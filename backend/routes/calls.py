"""
Calls and Voice routes for LeadGen Pro
Handles Twilio integration, call logs, analytics, and call coaching
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
import re
import logging
import os

from twilio.rest import Client as TwilioClient
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.twiml.voice_response import VoiceResponse

from core.database import db
from core.config import (
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_API_KEY,
    TWILIO_API_SECRET, TWILIO_PHONE_NUMBER, FRONTEND_URL
)
from core.security import User, get_current_user

router = APIRouter(tags=["Calls"])

# Initialize Twilio client
twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


# ==================== MODELS ====================

class CallOutcome(str):
    CONNECTED = "connected"
    VOICEMAIL = "voicemail"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    WRONG_NUMBER = "wrong_number"
    DECLINED = "declined"


class CallLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lead_id: Optional[str] = None
    phone_number: str
    outcome: str
    disposition: Optional[str] = None
    duration: int = 0
    notes: Optional[str] = None
    call_sid: Optional[str] = None
    agent_id: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    recording_url: Optional[str] = None
    transcript: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CallLogCreate(BaseModel):
    lead_id: Optional[str] = None
    phone_number: str
    outcome: str
    disposition: Optional[str] = None
    duration: int = 0
    notes: Optional[str] = None
    call_sid: Optional[str] = None


class VoiceTokenRequest(BaseModel):
    identity: str


class InitiateCallRequest(BaseModel):
    to_number: str
    lead_id: Optional[str] = None
    record: bool = False
    agent_phone: Optional[str] = None


class HangupRequest(BaseModel):
    call_sid: str


class CallListItem(BaseModel):
    id: str
    lead_id: Optional[str] = None
    lead_name: str
    company: str
    phone: str
    status: str = "pending"
    priority: int = 0
    notes: Optional[str] = None


# Call Disposition Options
CALL_DISPOSITIONS = [
    "No Answer",
    "Left Voicemail",
    "Gatekeeper",
    "Bad Number",
    "No Longer with Company",
    "Wrong POC",
    "Not Interested",
    "Referral",
    "Call Back",
    "Set Meeting",
    "Sent Info",
    "DNC - Do Not Call"
]


# ==================== HELPER FUNCTIONS ====================

def format_phone_e164(phone: str) -> str:
    """Format phone number to E.164 format"""
    if not phone:
        return phone
    if phone.startswith('+'):
        return phone
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 10:
        return '+1' + digits
    elif len(digits) == 11 and digits.startswith('1'):
        return '+' + digits
    return '+' + digits


# ==================== DISPOSITION ENDPOINTS ====================

@router.get("/calls/dispositions")
async def get_call_dispositions():
    """Get available call disposition options"""
    return CALL_DISPOSITIONS


@router.put("/calls/{call_id}/disposition")
async def update_call_disposition(
    call_id: str,
    disposition: str,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Update call disposition after a call ends"""
    call_log = await db.call_logs.find_one({"id": call_id}, {"_id": 0})
    
    if not call_log:
        pending_call = await db.pending_calls.find_one({"id": call_id})
        if pending_call:
            call_log = {
                "id": call_id,
                "call_sid": pending_call.get("agent_call_sid"),
                "lead_id": pending_call.get("lead_id"),
                "agent_id": pending_call.get("agent_id"),
                "phone_number": pending_call.get("lead_number"),
                "direction": "outbound",
                "outcome": "completed",
                "duration": 0,
                "started_at": pending_call.get("created_at"),
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "recording_url": None,
                "disposition": disposition,
                "notes": notes
            }
            await db.call_logs.insert_one(call_log)
            await db.pending_calls.delete_one({"id": call_id})
        else:
            raise HTTPException(status_code=404, detail="Call not found")
    else:
        update_data = {"disposition": disposition, "notes": notes}
        await db.call_logs.update_one({"id": call_id}, {"$set": update_data})
        call_log = await db.call_logs.find_one({"id": call_id}, {"_id": 0})
    
    # Create activity record
    activity_description = f"Call - {disposition}"
    if notes:
        activity_description += f" - {notes}"
    
    await db.activities.insert_one({
        "id": str(uuid.uuid4()),
        "type": "call_disposition",
        "description": activity_description,
        "user_id": current_user.id,
        "lead_id": call_log.get("lead_id"),
        "metadata": {
            "call_id": call_id,
            "disposition": disposition,
            "notes": notes,
            "phone_number": call_log.get("phone_number"),
            "duration": call_log.get("duration")
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Update lead's last_contacted
    if call_log.get("lead_id"):
        await db.leads.update_one(
            {"id": call_log["lead_id"]},
            {"$set": {"last_contacted": datetime.now(timezone.utc).isoformat()}}
        )
    
    return {"message": "Disposition updated", "disposition": disposition}


# ==================== CALL LOG ENDPOINTS ====================

@router.post("/calls/log", response_model=CallLog)
async def create_call_log(
    call_data: CallLogCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a manual call log entry"""
    call_log = CallLog(**call_data.model_dump(), agent_id=current_user.id)
    doc = call_log.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    if doc.get('started_at'):
        doc['started_at'] = doc['started_at'].isoformat()
    if doc.get('ended_at'):
        doc['ended_at'] = doc['ended_at'].isoformat()
    
    await db.call_logs.insert_one(doc)
    
    # Update lead's last_contacted
    if call_data.lead_id:
        await db.leads.update_one(
            {"id": call_data.lead_id},
            {"$set": {"last_contacted": datetime.now(timezone.utc).isoformat()}}
        )
    
    return call_log


@router.get("/calls/logs", response_model=List[CallLog])
async def get_call_logs(
    lead_id: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """Get call logs with optional lead filter"""
    query = {}
    if lead_id:
        query["lead_id"] = lead_id
    
    logs = await db.call_logs.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return [CallLog(**log) for log in logs]


@router.get("/calls/stats")
async def get_call_stats(current_user: User = Depends(get_current_user)):
    """Get call statistics for the current user"""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    pipeline = [
        {"$match": {"agent_id": current_user.id, "created_at": {"$gte": today.isoformat()}}},
        {"$group": {
            "_id": "$outcome",
            "count": {"$sum": 1},
            "total_duration": {"$sum": "$duration"}
        }}
    ]
    
    results = await db.call_logs.aggregate(pipeline).to_list(100)
    
    stats = {
        "total_calls": sum(r["count"] for r in results),
        "total_duration": sum(r.get("total_duration", 0) for r in results),
        "by_outcome": {r["_id"]: r["count"] for r in results}
    }
    
    return stats


# ==================== VOICE TOKEN ====================

@router.post("/voice/token")
async def generate_voice_token(request: VoiceTokenRequest, current_user: User = Depends(get_current_user)):
    """Generate Twilio access token for browser-based calling"""
    if not all([TWILIO_ACCOUNT_SID, TWILIO_API_KEY, TWILIO_API_SECRET]):
        raise HTTPException(status_code=500, detail="Twilio is not configured")
    
    try:
        token = AccessToken(
            TWILIO_ACCOUNT_SID,
            TWILIO_API_KEY,
            TWILIO_API_SECRET,
            identity=request.identity,
            ttl=3600
        )
        
        voice_grant = VoiceGrant(
            outgoing_application_sid=None,
            incoming_allow=True
        )
        token.add_grant(voice_grant)
        
        return {
            "success": True,
            "token": token.to_jwt(),
            "identity": request.identity,
            "expires_in": 3600
        }
    except Exception as e:
        logging.error(f"Error generating voice token: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CLICK-TO-CALL ====================

@router.post("/voice/call")
async def initiate_call(
    request: InitiateCallRequest,
    current_user: User = Depends(get_current_user)
):
    """Initiate a Click-to-Call - calls agent first, then bridges to lead"""
    if not twilio_client:
        raise HTTPException(status_code=500, detail="Twilio is not configured")
    
    agent_phone = request.agent_phone or current_user.phone
    if not agent_phone:
        raise HTTPException(
            status_code=400,
            detail="Please set your phone number in your profile settings to use Click-to-Call"
        )
    
    try:
        formatted_lead_number = format_phone_e164(request.to_number)
        formatted_agent_phone = format_phone_e164(agent_phone)
        
        callback_base = FRONTEND_URL.rstrip('/') if FRONTEND_URL else ''
        call_id = f"call_{uuid.uuid4().hex[:12]}"
        
        # Store pending call info
        pending_call = {
            "id": call_id,
            "lead_number": formatted_lead_number,
            "agent_id": current_user.id,
            "agent_name": current_user.full_name,
            "lead_id": request.lead_id,
            "record": request.record,
            "status": "calling_agent",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.pending_calls.insert_one(pending_call)
        
        # Build TwiML URL for agent connection
        twiml_url = f"{callback_base}/api/voice/connect/{call_id}"
        status_callback = f"{callback_base}/api/voice/agent-status/{call_id}"
        
        # Create call params
        call_params = {
            "to": formatted_agent_phone,
            "from_": TWILIO_PHONE_NUMBER,
            "url": twiml_url,
            "status_callback": status_callback,
            "status_callback_event": ["initiated", "ringing", "answered", "completed"],
            "status_callback_method": "POST",
            "method": "POST"
        }
        
        if request.record:
            call_params["record"] = True
            call_params["recording_status_callback"] = f"{callback_base}/api/voice/recording-callback"
        
        call = twilio_client.calls.create(**call_params)
        
        # Update pending call with agent call SID
        await db.pending_calls.update_one(
            {"id": call_id},
            {"$set": {"agent_call_sid": call.sid}}
        )
        
        return {
            "success": True,
            "call_id": call_id,
            "call_sid": call.sid,
            "status": "calling_agent",
            "message": f"Calling your phone at {formatted_agent_phone}. Answer to connect to lead."
        }
        
    except Exception as e:
        logging.error(f"Error initiating call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice/connect/{call_id}")
async def voice_connect_twiml(call_id: str, request: Request):
    """TwiML endpoint for when agent answers - prompts to connect to lead"""
    pending_call = await db.pending_calls.find_one({"id": call_id})
    if not pending_call:
        response = VoiceResponse()
        response.say("Sorry, this call session has expired.")
        response.hangup()
        return Response(content=str(response), media_type="application/xml")
    
    callback_base = FRONTEND_URL.rstrip('/') if FRONTEND_URL else ''
    
    response = VoiceResponse()
    gather = response.gather(
        num_digits=1,
        action=f"{callback_base}/api/voice/dial-status?call_id={call_id}",
        method="POST",
        timeout=10
    )
    gather.say(f"Press 1 to connect to your lead.")
    
    response.say("No input received. Goodbye.")
    response.hangup()
    
    return Response(content=str(response), media_type="application/xml")


@router.post("/voice/dial-status")
async def voice_dial_status(request: Request, call_id: str = None):
    """Handle agent's keypress and dial the lead"""
    form_data = await request.form()
    digits = form_data.get("Digits", "")
    
    if not call_id:
        call_id = form_data.get("call_id")
    
    pending_call = await db.pending_calls.find_one({"id": call_id})
    if not pending_call:
        response = VoiceResponse()
        response.say("Call session not found.")
        response.hangup()
        return Response(content=str(response), media_type="application/xml")
    
    if digits != "1":
        response = VoiceResponse()
        response.say("Call cancelled. Goodbye.")
        response.hangup()
        return Response(content=str(response), media_type="application/xml")
    
    callback_base = FRONTEND_URL.rstrip('/') if FRONTEND_URL else ''
    
    response = VoiceResponse()
    response.say("Connecting you now.")
    
    dial = response.dial(
        caller_id=TWILIO_PHONE_NUMBER,
        action=f"{callback_base}/api/voice/call-complete/{call_id}",
        method="POST",
        timeout=30
    )
    
    if pending_call.get("record"):
        dial.number(
            pending_call["lead_number"],
            status_callback=f"{callback_base}/api/voice/lead-status/{call_id}",
            status_callback_event="initiated ringing answered completed"
        )
    else:
        dial.number(pending_call["lead_number"])
    
    # Update status
    await db.pending_calls.update_one(
        {"id": call_id},
        {"$set": {"status": "connecting_lead", "connected_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return Response(content=str(response), media_type="application/xml")


@router.post("/voice/call-complete/{call_id}")
async def voice_call_complete(call_id: str, request: Request):
    """Handle call completion and create call log"""
    form_data = await request.form()
    dial_status = form_data.get("DialCallStatus", "unknown")
    dial_duration = int(form_data.get("DialCallDuration", 0))
    
    pending_call = await db.pending_calls.find_one({"id": call_id})
    
    if pending_call:
        outcome = "connected" if dial_status == "completed" else dial_status
        
        call_log = {
            "id": call_id,
            "call_sid": pending_call.get("agent_call_sid"),
            "lead_call_sid": pending_call.get("lead_call_sid"),
            "lead_id": pending_call.get("lead_id"),
            "agent_id": pending_call.get("agent_id"),
            "phone_number": pending_call.get("lead_number"),
            "direction": "outbound",
            "outcome": outcome,
            "duration": dial_duration,
            "started_at": pending_call.get("connected_at") or pending_call.get("created_at"),
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "recording_url": pending_call.get("recording_url")
        }
        
        await db.call_logs.insert_one(call_log)
        
        # Update lead's last_contacted
        if pending_call.get("lead_id"):
            await db.leads.update_one(
                {"id": pending_call["lead_id"]},
                {"$set": {"last_contacted": datetime.now(timezone.utc).isoformat()}}
            )
    
    response = VoiceResponse()
    response.say("Call ended. Goodbye.")
    response.hangup()
    
    return Response(content=str(response), media_type="application/xml")


@router.post("/voice/hangup")
async def hangup_call(request: HangupRequest, current_user: User = Depends(get_current_user)):
    """End an active call"""
    if not twilio_client:
        raise HTTPException(status_code=500, detail="Twilio is not configured")
    
    try:
        call = twilio_client.calls(request.call_sid).update(status="completed")
        return {"success": True, "message": "Call ended", "status": call.status}
    except Exception as e:
        logging.error(f"Error hanging up call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voice/call/{call_sid}/status")
async def get_call_status(call_sid: str, current_user: User = Depends(get_current_user)):
    """Get the status of a call"""
    if not twilio_client:
        raise HTTPException(status_code=500, detail="Twilio is not configured")
    
    try:
        call = twilio_client.calls(call_sid).fetch()
        return {
            "call_sid": call.sid,
            "status": call.status,
            "direction": call.direction,
            "duration": call.duration,
            "from": call.from_,
            "to": call.to
        }
    except Exception as e:
        logging.error(f"Error getting call status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/voice/call/{call_sid}/end")
async def end_call(call_sid: str, current_user: User = Depends(get_current_user)):
    """End a specific call by SID"""
    if not twilio_client:
        raise HTTPException(status_code=500, detail="Twilio is not configured")
    
    try:
        call = twilio_client.calls(call_sid).update(status="completed")
        return {"success": True, "message": "Call ended", "status": call.status}
    except Exception as e:
        logging.error(f"Error ending call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voice/pending/{call_id}")
async def get_pending_call(call_id: str, current_user: User = Depends(get_current_user)):
    """Get pending call status"""
    pending_call = await db.pending_calls.find_one({"id": call_id}, {"_id": 0})
    if not pending_call:
        call_log = await db.call_logs.find_one({"id": call_id}, {"_id": 0})
        if call_log:
            return {"status": "completed", "call_log": call_log}
        raise HTTPException(status_code=404, detail="Call not found")
    return pending_call


# ==================== WEBHOOKS ====================

@router.post("/voice/agent-status/{call_id}")
async def voice_agent_status(call_id: str, request: Request):
    """Handle agent call status updates"""
    form_data = await request.form()
    call_status = form_data.get("CallStatus")
    
    await db.pending_calls.update_one(
        {"id": call_id},
        {"$set": {"agent_status": call_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"status": "ok"}


@router.post("/voice/lead-status/{call_id}")
async def voice_lead_status(call_id: str, request: Request):
    """Handle lead call status updates"""
    form_data = await request.form()
    call_status = form_data.get("CallStatus")
    call_sid = form_data.get("CallSid")
    
    await db.pending_calls.update_one(
        {"id": call_id},
        {"$set": {
            "lead_status": call_status,
            "lead_call_sid": call_sid,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"status": "ok"}


@router.post("/voice/events")
async def voice_events(request: Request):
    """Handle Twilio voice events"""
    form_data = await request.form()
    logging.info(f"Voice event: {dict(form_data)}")
    return {"status": "ok"}


@router.post("/voice/recording-callback")
async def voice_recording_callback(request: Request):
    """Handle recording completion callback"""
    form_data = await request.form()
    recording_url = form_data.get("RecordingUrl")
    call_sid = form_data.get("CallSid")
    
    if recording_url and call_sid:
        # Update call log with recording URL
        await db.call_logs.update_one(
            {"call_sid": call_sid},
            {"$set": {"recording_url": recording_url}}
        )
        
        # Also update pending call
        await db.pending_calls.update_one(
            {"agent_call_sid": call_sid},
            {"$set": {"recording_url": recording_url}}
        )
    
    return {"status": "ok"}


# Export models and utilities
__all__ = [
    'router',
    'CallLog',
    'CallLogCreate',
    'CallOutcome',
    'CALL_DISPOSITIONS',
    'format_phone_e164'
]
