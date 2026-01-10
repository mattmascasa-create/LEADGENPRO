"""
Email routes for LeadGen Pro
Handles email templates, campaigns, tracking, sequences, and AI generation
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, RedirectResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
import json
import logging
import asyncio
import os
import resend

from core.database import db
from core.security import User, get_current_user

# Initialize Resend
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

router = APIRouter(tags=["Email"])


# ==================== MODELS ====================

class EmailTemplate(BaseModel):
    id: str = None
    name: str
    subject: str
    body: str
    category: str = "general"
    created_by: str = None
    created_at: datetime = None

    def __init__(self, **data):
        if 'id' not in data or data['id'] is None:
            data['id'] = str(uuid.uuid4())
        if 'created_at' not in data or data['created_at'] is None:
            data['created_at'] = datetime.now(timezone.utc)
        super().__init__(**data)


class EmailCampaign(BaseModel):
    id: str = None
    name: str = ""
    subject: str
    body: str
    sent_count: int = 0
    opened_count: int = 0
    clicked_count: int = 0
    created_by: str = None
    created_at: datetime = None

    def __init__(self, **data):
        if 'id' not in data or data['id'] is None:
            data['id'] = str(uuid.uuid4())
        if 'created_at' not in data or data['created_at'] is None:
            data['created_at'] = datetime.now(timezone.utc)
        super().__init__(**data)


class ScheduledEmail(BaseModel):
    id: str = None
    subject: str
    body: str
    recipient_ids: List[str]
    recipient_count: int
    scheduled_time: datetime
    campaign_id: Optional[str] = None
    status: str = "pending"
    created_by: str = None
    created_at: datetime = None

    def __init__(self, **data):
        if 'id' not in data or data['id'] is None:
            data['id'] = str(uuid.uuid4())
        if 'created_at' not in data or data['created_at'] is None:
            data['created_at'] = datetime.now(timezone.utc)
        super().__init__(**data)


class EmailTrackingEvent(BaseModel):
    id: str = None
    email_id: str
    event_type: str  # opened, clicked, bounced, replied
    lead_id: Optional[str] = None
    campaign_id: Optional[str] = None
    sequence_id: Optional[str] = None
    link_url: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    timestamp: datetime = None

    def __init__(self, **data):
        if 'id' not in data or data['id'] is None:
            data['id'] = str(uuid.uuid4())
        if 'timestamp' not in data or data['timestamp'] is None:
            data['timestamp'] = datetime.now(timezone.utc)
        super().__init__(**data)


class TrackedEmail(BaseModel):
    id: str = None
    lead_id: str
    campaign_id: Optional[str] = None
    sequence_id: Optional[str] = None
    subject: str
    body: str
    sent_by: str
    sent_at: datetime = None
    status: str = "sent"
    open_count: int = 0
    click_count: int = 0
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None

    def __init__(self, **data):
        if 'id' not in data or data['id'] is None:
            data['id'] = str(uuid.uuid4())
        if 'sent_at' not in data or data['sent_at'] is None:
            data['sent_at'] = datetime.now(timezone.utc)
        super().__init__(**data)


class SequenceStep(BaseModel):
    step_number: int
    subject: str
    body: str
    delay_days: int = 0
    delay_hours: int = 0


class EmailSequence(BaseModel):
    id: str = None
    name: str
    description: Optional[str] = None
    steps: List[SequenceStep] = []
    status: str = "active"
    exit_on_reply: bool = True
    exit_on_meeting: bool = True
    total_enrolled: int = 0
    created_by: str = None
    created_at: datetime = None
    updated_at: datetime = None

    def __init__(self, **data):
        if 'id' not in data or data['id'] is None:
            data['id'] = str(uuid.uuid4())
        if 'created_at' not in data or data['created_at'] is None:
            data['created_at'] = datetime.now(timezone.utc)
        if 'updated_at' not in data or data['updated_at'] is None:
            data['updated_at'] = datetime.now(timezone.utc)
        super().__init__(**data)


class SequenceEnrollment(BaseModel):
    id: str = None
    sequence_id: str
    lead_id: str
    current_step: int = 1
    status: str = "active"  # active, completed, unenrolled, paused
    enrolled_by: str = None
    enrolled_at: datetime = None
    next_email_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def __init__(self, **data):
        if 'id' not in data or data['id'] is None:
            data['id'] = str(uuid.uuid4())
        if 'enrolled_at' not in data or data['enrolled_at'] is None:
            data['enrolled_at'] = datetime.now(timezone.utc)
        super().__init__(**data)


class EmailGenerateRequest(BaseModel):
    prompt: str
    context: str = "single_email"
    lead_count: int = 0


class BulkEmailRequest(BaseModel):
    lead_ids: List[str]
    subject: str
    body: str
    ai_personalize: bool = False
    schedule_time: Optional[str] = None
    follow_up: Optional[dict] = None


# ==================== EMAIL TEMPLATES ====================

@router.get("/email/templates")
async def get_email_templates(current_user: User = Depends(get_current_user)):
    """Get all email templates"""
    templates = await db.email_templates.find({}, {"_id": 0}).to_list(100)
    return templates


@router.post("/email/templates")
async def create_email_template(template: EmailTemplate, current_user: User = Depends(get_current_user)):
    """Create a new email template"""
    template.created_by = current_user.id
    doc = template.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.email_templates.insert_one(doc)
    return {"success": True, "template": template}


@router.delete("/email/templates/{template_id}")
async def delete_email_template(template_id: str, current_user: User = Depends(get_current_user)):
    """Delete an email template"""
    await db.email_templates.delete_one({"id": template_id})
    return {"success": True}


# ==================== EMAIL CAMPAIGNS ====================

@router.get("/email/campaigns")
async def get_email_campaigns(current_user: User = Depends(get_current_user)):
    """Get all email campaigns"""
    campaigns = await db.email_campaigns.find({}, {"_id": 0}).to_list(100)
    return campaigns


@router.get("/email/scheduled")
async def get_scheduled_emails(current_user: User = Depends(get_current_user)):
    """Get all scheduled emails"""
    emails = await db.scheduled_emails.find({"status": "pending"}, {"_id": 0}).to_list(100)
    return emails


@router.delete("/email/scheduled/{email_id}")
async def cancel_scheduled_email(email_id: str, current_user: User = Depends(get_current_user)):
    """Cancel a scheduled email"""
    await db.scheduled_emails.update_one(
        {"id": email_id},
        {"$set": {"status": "cancelled"}}
    )
    return {"success": True}


# ==================== AI EMAIL GENERATION ====================

@router.post("/email/generate")
async def generate_email_with_ai(request: EmailGenerateRequest, current_user: User = Depends(get_current_user)):
    """Generate email content using AI"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"email-gen-{uuid.uuid4().hex[:8]}",
            system_message="""You are an expert email copywriter specializing in B2B sales and marketing emails.
            Write compelling, personalized emails that:
            - Have attention-grabbing subject lines
            - Are concise and value-focused
            - Include clear calls to action
            - Sound natural and not salesy
            - Use personalization variables like {{first_name}}, {{company}}, {{title}} where appropriate"""
        ).with_model("openai", "gpt-4o")
        
        prompt = f"""Write a professional sales email based on this request: {request.prompt}
        
        {"This will be sent to " + str(request.lead_count) + " recipients, so include personalization variables." if request.lead_count > 1 else ""}
        
        Return your response in this exact JSON format:
        {{
            "subject": "Your subject line here",
            "body": "Your email body here"
        }}
        
        Return ONLY the JSON, no other text."""
        
        message = UserMessage(text=prompt)
        response = await chat.send_message(message)
        
        # Parse response
        clean_response = response.strip()
        if clean_response.startswith("```json"):
            clean_response = clean_response[7:]
        if clean_response.startswith("```"):
            clean_response = clean_response[3:]
        if clean_response.endswith("```"):
            clean_response = clean_response[:-3]
        
        email_content = json.loads(clean_response.strip())
        return email_content
        
    except Exception as e:
        logging.error(f"Email generation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate email")


# ==================== BULK EMAIL ====================

@router.post("/email/send-bulk")
async def send_bulk_email(request: BulkEmailRequest, current_user: User = Depends(get_current_user)):
    """Send bulk emails to selected leads"""
    if not RESEND_API_KEY:
        raise HTTPException(status_code=400, detail="Email service not configured")
    
    # Import Activity model
    from routes.leads import Activity
    
    # Get lead details
    leads = await db.leads.find({"id": {"$in": request.lead_ids}}, {"_id": 0}).to_list(100)
    
    if not leads:
        raise HTTPException(status_code=400, detail="No valid leads found")
    
    # Create campaign record
    campaign = EmailCampaign(
        subject=request.subject,
        body=request.body,
        sent_count=len(leads),
        created_by=current_user.id
    )
    
    campaign_doc = campaign.model_dump()
    campaign_doc['created_at'] = campaign_doc['created_at'].isoformat()
    await db.email_campaigns.insert_one(campaign_doc)
    
    # If scheduled, save for later
    if request.schedule_time:
        scheduled = ScheduledEmail(
            subject=request.subject,
            body=request.body,
            recipient_ids=request.lead_ids,
            recipient_count=len(leads),
            scheduled_time=datetime.fromisoformat(request.schedule_time),
            campaign_id=campaign.id,
            created_by=current_user.id
        )
        scheduled_doc = scheduled.model_dump()
        scheduled_doc['created_at'] = scheduled_doc['created_at'].isoformat()
        scheduled_doc['scheduled_time'] = scheduled_doc['scheduled_time'].isoformat()
        await db.scheduled_emails.insert_one(scheduled_doc)
        
        return {
            "success": True,
            "sent_count": 0,
            "scheduled_count": len(leads),
            "scheduled_time": request.schedule_time
        }
    
    # Send emails immediately
    sent_count = 0
    failed_count = 0
    
    for lead in leads:
        try:
            # Personalize email
            personalized_subject = request.subject
            personalized_body = request.body
            
            # Replace variables
            replacements = {
                "{{first_name}}": lead.get("first_name", ""),
                "{{last_name}}": lead.get("last_name", ""),
                "{{company}}": lead.get("company", ""),
                "{{title}}": lead.get("title", ""),
                "{{email}}": lead.get("email", "")
            }
            
            for var, value in replacements.items():
                personalized_subject = personalized_subject.replace(var, value)
                personalized_body = personalized_body.replace(var, value)
            
            # Send email via Resend
            email_params = {
                "from": SENDER_EMAIL,
                "to": [lead.get("email")],
                "subject": personalized_subject,
                "html": f"<div style='font-family: Arial, sans-serif; line-height: 1.6;'>{personalized_body.replace(chr(10), '<br>')}</div>"
            }
            
            await asyncio.to_thread(resend.Emails.send, email_params)
            sent_count += 1
            
            # Log activity
            activity = Activity(
                type="email_sent",
                description=f"Sent bulk email: {personalized_subject}",
                lead_id=lead.get("id"),
                user_id=current_user.id,
                metadata={"campaign_id": campaign.id, "subject": personalized_subject}
            )
            activity_doc = activity.model_dump()
            activity_doc['created_at'] = activity_doc['created_at'].isoformat()
            await db.activities.insert_one(activity_doc)
            
        except Exception as e:
            logging.error(f"Failed to send email to {lead.get('email')}: {e}")
            failed_count += 1
    
    # Schedule follow-ups if enabled
    if request.follow_up and sent_count > 0:
        follow_up_days = request.follow_up.get("days", 3)
        follow_up_count = request.follow_up.get("count", 2)
        
        for i in range(1, follow_up_count + 1):
            follow_up_time = datetime.now(timezone.utc) + timedelta(days=follow_up_days * i)
            
            scheduled = ScheduledEmail(
                subject=f"Re: {request.subject}",
                body=f"Following up on my previous email...\n\n{request.body}",
                recipient_ids=request.lead_ids,
                recipient_count=len(leads),
                scheduled_time=follow_up_time,
                campaign_id=campaign.id,
                created_by=current_user.id
            )
            scheduled_doc = scheduled.model_dump()
            scheduled_doc['created_at'] = scheduled_doc['created_at'].isoformat()
            scheduled_doc['scheduled_time'] = scheduled_doc['scheduled_time'].isoformat()
            await db.scheduled_emails.insert_one(scheduled_doc)
    
    return {
        "success": True,
        "sent_count": sent_count,
        "failed_count": failed_count,
        "campaign_id": campaign.id
    }


# ==================== EMAIL TRACKING ====================

@router.get("/email/tracking/pixel/{email_id}.gif")
async def track_email_open(email_id: str, request: Request):
    """Tracking pixel endpoint - returns 1x1 transparent GIF"""
    # Log the open event
    try:
        # Update tracked email
        result = await db.tracked_emails.update_one(
            {"id": email_id},
            {
                "$set": {"opened_at": datetime.now(timezone.utc).isoformat(), "status": "opened"},
                "$inc": {"open_count": 1}
            }
        )
        
        if result.modified_count > 0:
            # Get email details
            email = await db.tracked_emails.find_one({"id": email_id}, {"_id": 0})
            
            # Create tracking event
            event = EmailTrackingEvent(
                email_id=email_id,
                event_type="opened",
                lead_id=email.get("lead_id") if email else None,
                campaign_id=email.get("campaign_id") if email else None,
                sequence_id=email.get("sequence_id") if email else None,
                user_agent=request.headers.get("user-agent"),
                ip_address=request.client.host if request.client else None
            )
            event_doc = event.model_dump()
            event_doc['timestamp'] = event_doc['timestamp'].isoformat()
            await db.email_tracking_events.insert_one(event_doc)
            
            # Update campaign stats
            if email and email.get("campaign_id"):
                await db.email_campaigns.update_one(
                    {"id": email["campaign_id"]},
                    {"$inc": {"opened_count": 1}}
                )
    except Exception as e:
        logging.error(f"Error tracking email open: {e}")
    
    # Return 1x1 transparent GIF
    gif_bytes = b'GIF89a\x01\x01\x80\xff\xff\xff!\xf9\x04\x01,\x01\x01\x02\x02D\x01;'
    return Response(content=gif_bytes, media_type="image/gif")


@router.get("/email/tracking/click/{email_id}/{link_id}")
async def track_email_click(email_id: str, link_id: str, url: str, request: Request):
    """Track link clicks and redirect to actual URL"""
    try:
        # Update tracked email
        await db.tracked_emails.update_one(
            {"id": email_id},
            {
                "$set": {"clicked_at": datetime.now(timezone.utc).isoformat(), "status": "clicked"},
                "$inc": {"click_count": 1}
            }
        )
        
        # Get email details
        email = await db.tracked_emails.find_one({"id": email_id}, {"_id": 0})
        
        # Create tracking event
        event = EmailTrackingEvent(
            email_id=email_id,
            event_type="clicked",
            lead_id=email.get("lead_id") if email else None,
            campaign_id=email.get("campaign_id") if email else None,
            sequence_id=email.get("sequence_id") if email else None,
            link_url=url,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None
        )
        event_doc = event.model_dump()
        event_doc['timestamp'] = event_doc['timestamp'].isoformat()
        await db.email_tracking_events.insert_one(event_doc)
        
        # Update campaign stats
        if email and email.get("campaign_id"):
            await db.email_campaigns.update_one(
                {"id": email["campaign_id"]},
                {"$inc": {"clicked_count": 1}}
            )
    except Exception as e:
        logging.error(f"Error tracking email click: {e}")
    
    # Redirect to actual URL
    return RedirectResponse(url=url)


@router.get("/email/tracking/stats")
async def get_email_tracking_stats(
    days: int = 30,
    current_user: User = Depends(get_current_user)
):
    """Get email tracking statistics"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get tracked emails
    emails = await db.tracked_emails.find(
        {"sent_at": {"$gte": cutoff.isoformat()}, "sent_by": current_user.id},
        {"_id": 0}
    ).to_list(1000)
    
    total_sent = len(emails)
    total_opened = sum(1 for e in emails if e.get("opened_at"))
    total_clicked = sum(1 for e in emails if e.get("clicked_at"))
    total_replied = sum(1 for e in emails if e.get("replied_at"))
    
    open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
    click_rate = (total_clicked / total_sent * 100) if total_sent > 0 else 0
    reply_rate = (total_replied / total_sent * 100) if total_sent > 0 else 0
    
    # Get daily breakdown
    daily_stats = {}
    for email in emails:
        date = email.get("sent_at", "")[:10]
        if date not in daily_stats:
            daily_stats[date] = {"sent": 0, "opened": 0, "clicked": 0, "replied": 0}
        daily_stats[date]["sent"] += 1
        if email.get("opened_at"):
            daily_stats[date]["opened"] += 1
        if email.get("clicked_at"):
            daily_stats[date]["clicked"] += 1
        if email.get("replied_at"):
            daily_stats[date]["replied"] += 1
    
    return {
        "summary": {
            "total_sent": total_sent,
            "total_opened": total_opened,
            "total_clicked": total_clicked,
            "total_replied": total_replied,
            "open_rate": round(open_rate, 1),
            "click_rate": round(click_rate, 1),
            "reply_rate": round(reply_rate, 1)
        },
        "daily_breakdown": [
            {"date": date, **stats}
            for date, stats in sorted(daily_stats.items())
        ],
        "recent_emails": emails[:20]
    }


@router.get("/email/tracking/{email_id}")
async def get_email_tracking_details(email_id: str, current_user: User = Depends(get_current_user)):
    """Get detailed tracking for a specific email"""
    email = await db.tracked_emails.find_one({"id": email_id}, {"_id": 0})
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Get all events for this email
    events = await db.email_tracking_events.find(
        {"email_id": email_id},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(100)
    
    return {
        "email": email,
        "events": events
    }


# ==================== EMAIL SEQUENCES (DRIP CAMPAIGNS) ====================

@router.get("/sequences")
async def get_sequences(current_user: User = Depends(get_current_user)):
    """Get all email sequences"""
    sequences = await db.email_sequences.find(
        {"created_by": current_user.id},
        {"_id": 0}
    ).to_list(100)
    return sequences


@router.post("/sequences")
async def create_sequence(
    name: str,
    description: Optional[str] = None,
    steps: List[dict] = [],
    exit_on_reply: bool = True,
    exit_on_meeting: bool = True,
    current_user: User = Depends(get_current_user)
):
    """Create a new email sequence"""
    sequence = EmailSequence(
        name=name,
        description=description,
        steps=[SequenceStep(**step) for step in steps],
        exit_on_reply=exit_on_reply,
        exit_on_meeting=exit_on_meeting,
        created_by=current_user.id
    )
    
    seq_doc = sequence.model_dump()
    seq_doc['created_at'] = seq_doc['created_at'].isoformat()
    seq_doc['updated_at'] = seq_doc['updated_at'].isoformat()
    seq_doc['steps'] = [s.model_dump() if hasattr(s, 'model_dump') else s for s in seq_doc['steps']]
    await db.email_sequences.insert_one(seq_doc)
    
    return {"success": True, "sequence": seq_doc}


@router.get("/sequences/{sequence_id}")
async def get_sequence(sequence_id: str, current_user: User = Depends(get_current_user)):
    """Get sequence details with enrollments"""
    sequence = await db.email_sequences.find_one({"id": sequence_id}, {"_id": 0})
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    # Get enrollments
    enrollments = await db.sequence_enrollments.find(
        {"sequence_id": sequence_id},
        {"_id": 0}
    ).to_list(500)
    
    # Get lead details for enrollments
    lead_ids = [e["lead_id"] for e in enrollments]
    leads = await db.leads.find({"id": {"$in": lead_ids}}, {"_id": 0}).to_list(500)
    lead_map = {l["id"]: l for l in leads}
    
    for enrollment in enrollments:
        enrollment["lead"] = lead_map.get(enrollment["lead_id"])
    
    return {
        "sequence": sequence,
        "enrollments": enrollments
    }


@router.put("/sequences/{sequence_id}")
async def update_sequence(
    sequence_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    steps: Optional[List[dict]] = None,
    status: Optional[str] = None,
    exit_on_reply: Optional[bool] = None,
    exit_on_meeting: Optional[bool] = None,
    current_user: User = Depends(get_current_user)
):
    """Update a sequence"""
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if name is not None:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description
    if steps is not None:
        update_data["steps"] = steps
    if status is not None:
        update_data["status"] = status
    if exit_on_reply is not None:
        update_data["exit_on_reply"] = exit_on_reply
    if exit_on_meeting is not None:
        update_data["exit_on_meeting"] = exit_on_meeting
    
    result = await db.email_sequences.update_one(
        {"id": sequence_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    return {"success": True, "message": "Sequence updated"}


@router.delete("/sequences/{sequence_id}")
async def delete_sequence(sequence_id: str, current_user: User = Depends(get_current_user)):
    """Delete a sequence"""
    # Remove all enrollments first
    await db.sequence_enrollments.delete_many({"sequence_id": sequence_id})
    
    result = await db.email_sequences.delete_one({"id": sequence_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    return {"success": True, "message": "Sequence deleted"}


@router.post("/sequences/{sequence_id}/enroll")
async def enroll_leads_in_sequence(
    sequence_id: str,
    lead_ids: List[str],
    current_user: User = Depends(get_current_user)
):
    """Enroll leads in a sequence"""
    sequence = await db.email_sequences.find_one({"id": sequence_id}, {"_id": 0})
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    
    enrolled_count = 0
    already_enrolled = 0
    
    for lead_id in lead_ids:
        # Check if already enrolled
        existing = await db.sequence_enrollments.find_one({
            "sequence_id": sequence_id,
            "lead_id": lead_id,
            "status": "active"
        })
        
        if existing:
            already_enrolled += 1
            continue
        
        # Calculate first email time
        steps = sequence.get("steps", [])
        first_step = steps[0] if steps else None
        
        if first_step:
            delay_days = first_step.get("delay_days", 0)
            delay_hours = first_step.get("delay_hours", 0)
            next_email_at = datetime.now(timezone.utc) + timedelta(days=delay_days, hours=delay_hours)
        else:
            next_email_at = datetime.now(timezone.utc)
        
        enrollment = SequenceEnrollment(
            sequence_id=sequence_id,
            lead_id=lead_id,
            current_step=1,
            status="active",
            next_email_at=next_email_at,
            enrolled_by=current_user.id
        )
        
        enroll_doc = enrollment.model_dump()
        enroll_doc['enrolled_at'] = enroll_doc['enrolled_at'].isoformat()
        enroll_doc['next_email_at'] = enroll_doc['next_email_at'].isoformat() if enroll_doc['next_email_at'] else None
        await db.sequence_enrollments.insert_one(enroll_doc)
        
        enrolled_count += 1
    
    # Update sequence stats
    await db.email_sequences.update_one(
        {"id": sequence_id},
        {"$inc": {"total_enrolled": enrolled_count}}
    )
    
    return {
        "success": True,
        "enrolled_count": enrolled_count,
        "already_enrolled": already_enrolled
    }


@router.post("/sequences/{sequence_id}/unenroll/{lead_id}")
async def unenroll_lead_from_sequence(
    sequence_id: str,
    lead_id: str,
    current_user: User = Depends(get_current_user)
):
    """Unenroll a lead from a sequence"""
    result = await db.sequence_enrollments.update_one(
        {"sequence_id": sequence_id, "lead_id": lead_id, "status": "active"},
        {"$set": {"status": "unenrolled", "completed_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    return {"success": True, "message": "Lead unenrolled from sequence"}


# Export models and router
__all__ = [
    'router',
    'EmailTemplate',
    'EmailCampaign',
    'ScheduledEmail',
    'EmailTrackingEvent',
    'TrackedEmail',
    'EmailSequence',
    'SequenceStep',
    'SequenceEnrollment',
    'EmailGenerateRequest',
    'BulkEmailRequest'
]
