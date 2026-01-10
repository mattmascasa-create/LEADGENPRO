"""
Public API routes for LeadGen Pro
Handles external integrations via API keys
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import secrets
import logging

from core.database import db
from core.security import User, get_current_user

router = APIRouter(prefix="/public", tags=["Public API"])


# ==================== MODELS ====================

class APIKey(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    key: str
    user_id: str
    permissions: List[str] = ["read"]  # read, write, delete, admin
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used: Optional[datetime] = None
    is_active: bool = True


class CreateAPIKeyRequest(BaseModel):
    name: str
    permissions: List[str] = ["read"]


class PublicLeadCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    source: str = "api"
    notes: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None


class PublicAppointmentCreate(BaseModel):
    title: str
    lead_id: Optional[str] = None
    lead_email: Optional[str] = None
    lead_name: Optional[str] = None
    scheduled_at: datetime
    duration: int = 30  # minutes
    notes: Optional[str] = None
    meeting_type: str = "call"  # call, meeting, demo


class PublicCallLog(BaseModel):
    lead_id: str
    phone: str
    duration: int  # seconds
    outcome: str  # connected, voicemail, no_answer, busy
    notes: Optional[str] = None
    recorded: bool = False


class PublicTaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    lead_id: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: str = "medium"


class WebhookSubscription(BaseModel):
    url: str
    events: List[str]  # lead.created, lead.updated, call.completed, appointment.created, etc.
    secret: Optional[str] = None


# ==================== API KEY AUTHENTICATION ====================

async def get_api_key_user(request: Request):
    """Authenticate requests using API key in header"""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required. Add X-API-Key header.")
    
    key_doc = await db.api_keys.find_one({"key": api_key, "is_active": True})
    if not key_doc:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    
    # Update last used timestamp
    await db.api_keys.update_one(
        {"key": api_key},
        {"$set": {"last_used": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Get the user associated with this key
    user = await db.users.find_one({"id": key_doc["user_id"]}, {"_id": 0, "hashed_password": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=401, detail="API key user not found")
    
    return User(**user), key_doc.get("permissions", ["read"])


# ==================== API KEY MANAGEMENT (JWT Auth) ====================

@router.post("/api-keys", tags=["API Keys"])
async def create_api_key(request: CreateAPIKeyRequest, current_user: User = Depends(get_current_user)):
    """Create a new API key for external integrations"""
    api_key = APIKey(
        name=request.name,
        key=f"lgp_{secrets.token_urlsafe(32)}",
        user_id=current_user.id,
        permissions=request.permissions
    )
    
    key_doc = api_key.model_dump()
    key_doc['created_at'] = key_doc['created_at'].isoformat()
    await db.api_keys.insert_one(key_doc)
    
    return {
        "id": api_key.id,
        "name": api_key.name,
        "key": api_key.key,  # Only shown once!
        "permissions": api_key.permissions,
        "message": "Save this key securely - it won't be shown again!"
    }


@router.get("/api-keys", tags=["API Keys"])
async def list_api_keys(current_user: User = Depends(get_current_user)):
    """List all API keys for current user (keys are masked)"""
    keys = await db.api_keys.find(
        {"user_id": current_user.id},
        {"_id": 0, "key": 0}  # Don't return the actual key
    ).to_list(100)
    
    for key in keys:
        key["key_preview"] = "lgp_****" + key.get("id", "")[-8:]
    
    return keys


@router.delete("/api-keys/{key_id}", tags=["API Keys"])
async def delete_api_key(key_id: str, current_user: User = Depends(get_current_user)):
    """Deactivate an API key"""
    result = await db.api_keys.update_one(
        {"id": key_id, "user_id": current_user.id},
        {"$set": {"is_active": False}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"message": "API key deactivated"}


# ==================== PUBLIC API ENDPOINTS ====================

@router.get("/health")
async def public_health():
    """Health check endpoint - no auth required"""
    return {"status": "healthy", "service": "LeadGen Pro API", "version": "2.0"}


# ==================== LEADS API ====================

@router.get("/leads")
async def public_get_leads(
    limit: int = 50,
    offset: int = 0,
    stage: Optional[str] = None,
    auth: tuple = Depends(get_api_key_user)
):
    """Get leads via API key authentication"""
    user, permissions = auth
    if "read" not in permissions:
        raise HTTPException(status_code=403, detail="Read permission required")
    
    query = {}
    if stage:
        query["stage"] = stage
    
    leads = await db.leads.find(query, {"_id": 0}).skip(offset).limit(limit).to_list(limit)
    total = await db.leads.count_documents(query)
    
    return {"leads": leads, "total": total, "limit": limit, "offset": offset}


@router.get("/leads/{lead_id}")
async def public_get_lead(lead_id: str, auth: tuple = Depends(get_api_key_user)):
    """Get a specific lead by ID"""
    user, permissions = auth
    if "read" not in permissions:
        raise HTTPException(status_code=403, detail="Read permission required")
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("/leads")
async def public_create_lead(lead_data: PublicLeadCreate, auth: tuple = Depends(get_api_key_user)):
    """Create a new lead via API"""
    user, permissions = auth
    if "write" not in permissions:
        raise HTTPException(status_code=403, detail="Write permission required")
    
    lead_doc = {
        "id": str(uuid.uuid4()),
        "first_name": lead_data.first_name,
        "last_name": lead_data.last_name,
        "email": lead_data.email,
        "phone": lead_data.phone,
        "company": lead_data.company,
        "title": lead_data.title,
        "source": lead_data.source,
        "notes": lead_data.notes,
        "assigned_to": user.id,
        "stage": "new",
        "score": 50,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    if lead_data.custom_fields:
        lead_doc['custom_fields'] = lead_data.custom_fields
    
    await db.leads.insert_one(lead_doc)
    
    return {"id": lead_doc["id"], "message": "Lead created successfully"}


@router.put("/leads/{lead_id}")
async def public_update_lead(lead_id: str, updates: Dict[str, Any], auth: tuple = Depends(get_api_key_user)):
    """Update a lead via API"""
    user, permissions = auth
    if "write" not in permissions:
        raise HTTPException(status_code=403, detail="Write permission required")
    
    # Remove protected fields
    updates.pop("id", None)
    updates.pop("_id", None)
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.leads.update_one({"id": lead_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {"message": "Lead updated successfully"}


@router.delete("/leads/{lead_id}")
async def public_delete_lead(lead_id: str, auth: tuple = Depends(get_api_key_user)):
    """Delete a lead via API"""
    user, permissions = auth
    if "delete" not in permissions:
        raise HTTPException(status_code=403, detail="Delete permission required")
    
    result = await db.leads.delete_one({"id": lead_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {"message": "Lead deleted successfully"}


# ==================== APPOINTMENTS API ====================

@router.get("/appointments")
async def public_get_appointments(
    lead_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    auth: tuple = Depends(get_api_key_user)
):
    """Get appointments"""
    user, permissions = auth
    if "read" not in permissions:
        raise HTTPException(status_code=403, detail="Read permission required")
    
    query = {}
    if lead_id:
        query["lead_id"] = lead_id
    if from_date:
        query["scheduled_at"] = {"$gte": from_date}
    if to_date:
        if "scheduled_at" in query:
            query["scheduled_at"]["$lte"] = to_date
        else:
            query["scheduled_at"] = {"$lte": to_date}
    
    appointments = await db.appointments.find(query, {"_id": 0}).to_list(500)
    return {"appointments": appointments}


@router.post("/appointments")
async def public_create_appointment(appt: PublicAppointmentCreate, auth: tuple = Depends(get_api_key_user)):
    """Create an appointment from external system"""
    user, permissions = auth
    if "write" not in permissions:
        raise HTTPException(status_code=403, detail="Write permission required")
    
    appointment = {
        "id": f"appt_{uuid.uuid4().hex[:12]}",
        "title": appt.title,
        "lead_id": appt.lead_id,
        "lead_email": appt.lead_email,
        "lead_name": appt.lead_name,
        "scheduled_at": appt.scheduled_at.isoformat(),
        "duration": appt.duration,
        "notes": appt.notes,
        "meeting_type": appt.meeting_type,
        "status": "scheduled",
        "created_by": user.id,
        "source": "api",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.appointments.insert_one(appointment)
    
    return {"id": appointment["id"], "message": "Appointment created"}


@router.delete("/appointments/{appointment_id}")
async def public_cancel_appointment(appointment_id: str, auth: tuple = Depends(get_api_key_user)):
    """Cancel an appointment"""
    user, permissions = auth
    if "write" not in permissions:
        raise HTTPException(status_code=403, detail="Write permission required")
    
    result = await db.appointments.update_one(
        {"id": appointment_id},
        {"$set": {"status": "cancelled", "cancelled_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    return {"message": "Appointment cancelled"}


# ==================== CALLS API ====================

@router.get("/calls")
async def public_get_calls(
    lead_id: Optional[str] = None,
    limit: int = 50,
    auth: tuple = Depends(get_api_key_user)
):
    """Get call logs"""
    user, permissions = auth
    if "read" not in permissions:
        raise HTTPException(status_code=403, detail="Read permission required")
    
    query = {}
    if lead_id:
        query["lead_id"] = lead_id
    
    calls = await db.call_logs.find(query, {"_id": 0}).limit(limit).to_list(limit)
    return {"calls": calls}


@router.post("/calls")
async def public_log_call(call_data: PublicCallLog, auth: tuple = Depends(get_api_key_user)):
    """Log a call from external system (e.g., phone system integration)"""
    user, permissions = auth
    if "write" not in permissions:
        raise HTTPException(status_code=403, detail="Write permission required")
    
    call_log = {
        "id": f"call_{uuid.uuid4().hex[:12]}",
        "lead_id": call_data.lead_id,
        "phone": call_data.phone,
        "duration": call_data.duration,
        "outcome": call_data.outcome,
        "notes": call_data.notes,
        "recorded": call_data.recorded,
        "agent_id": user.id,
        "direction": "outbound",
        "source": "api",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.call_logs.insert_one(call_log)
    
    # Update lead's last_contacted
    if call_data.lead_id:
        await db.leads.update_one(
            {"id": call_data.lead_id},
            {"$set": {"last_contacted": datetime.now(timezone.utc).isoformat()}}
        )
    
    return {"id": call_log["id"], "message": "Call logged"}


# ==================== ACTIVITIES API ====================

@router.get("/activities/{lead_id}")
async def public_get_activities(lead_id: str, limit: int = 50, auth: tuple = Depends(get_api_key_user)):
    """Get activities for a lead"""
    user, permissions = auth
    if "read" not in permissions:
        raise HTTPException(status_code=403, detail="Read permission required")
    
    activities = await db.activities.find(
        {"lead_id": lead_id}, 
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {"activities": activities}


@router.post("/activities")
async def public_create_activity(
    lead_id: str,
    type: str,
    description: str,
    metadata: Optional[Dict[str, Any]] = None,
    auth: tuple = Depends(get_api_key_user)
):
    """Log an activity from an external system"""
    user, permissions = auth
    if "write" not in permissions:
        raise HTTPException(status_code=403, detail="Write permission required")
    
    activity = {
        "id": f"act_{uuid.uuid4().hex[:12]}",
        "type": type,
        "description": description,
        "lead_id": lead_id,
        "user_id": user.id,
        "metadata": metadata or {},
        "source": "api",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.activities.insert_one(activity)
    return {"id": activity["id"], "message": "Activity logged"}


# ==================== TASKS API ====================

@router.get("/tasks")
async def public_get_tasks(
    status: Optional[str] = None,
    lead_id: Optional[str] = None,
    auth: tuple = Depends(get_api_key_user)
):
    """Get tasks"""
    user, permissions = auth
    if "read" not in permissions:
        raise HTTPException(status_code=403, detail="Read permission required")
    
    query = {}
    if status:
        query["completed"] = status == "completed"
    if lead_id:
        query["lead_id"] = lead_id
    
    tasks = await db.tasks.find(query, {"_id": 0}).to_list(500)
    return {"tasks": tasks}


@router.post("/tasks")
async def public_create_task(task_data: PublicTaskCreate, auth: tuple = Depends(get_api_key_user)):
    """Create a task from external system"""
    user, permissions = auth
    if "write" not in permissions:
        raise HTTPException(status_code=403, detail="Write permission required")
    
    task = {
        "id": f"task_{uuid.uuid4().hex[:12]}",
        "title": task_data.title,
        "description": task_data.description,
        "lead_id": task_data.lead_id,
        "assigned_to": user.id,
        "due_date": task_data.due_date.isoformat() if task_data.due_date else None,
        "priority": task_data.priority,
        "completed": False,
        "source": "api",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.tasks.insert_one(task)
    return {"id": task["id"], "message": "Task created"}


# ==================== WEBHOOKS ====================

@router.post("/webhooks")
async def create_webhook(webhook: WebhookSubscription, auth: tuple = Depends(get_api_key_user)):
    """Subscribe to webhook events"""
    user, permissions = auth
    if "admin" not in permissions:
        raise HTTPException(status_code=403, detail="Admin permission required for webhooks")
    
    webhook_doc = {
        "id": f"wh_{uuid.uuid4().hex[:12]}",
        "url": webhook.url,
        "events": webhook.events,
        "secret": webhook.secret or secrets.token_urlsafe(32),
        "user_id": user.id,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.webhooks.insert_one(webhook_doc)
    return {
        "id": webhook_doc["id"],
        "secret": webhook_doc["secret"],
        "message": "Webhook created. Use the secret to verify payloads."
    }


@router.get("/webhooks")
async def list_webhooks(auth: tuple = Depends(get_api_key_user)):
    """List webhook subscriptions"""
    user, permissions = auth
    webhooks = await db.webhooks.find(
        {"user_id": user.id, "is_active": True},
        {"_id": 0, "secret": 0}
    ).to_list(100)
    return {"webhooks": webhooks}


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, auth: tuple = Depends(get_api_key_user)):
    """Delete a webhook subscription"""
    user, permissions = auth
    result = await db.webhooks.update_one(
        {"id": webhook_id, "user_id": user.id},
        {"$set": {"is_active": False}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"message": "Webhook deleted"}


# ==================== API DOCUMENTATION ====================

@router.get("/docs")
async def api_documentation():
    """Get API documentation"""
    return {
        "name": "LeadGen Pro Public API",
        "version": "2.0",
        "base_url": "/api/public",
        "authentication": {
            "type": "API Key",
            "header": "X-API-Key",
            "description": "Create API keys in your LeadGen Pro dashboard under Settings"
        },
        "endpoints": {
            "leads": {
                "GET /leads": "List leads with pagination",
                "GET /leads/{id}": "Get a specific lead",
                "POST /leads": "Create a new lead",
                "PUT /leads/{id}": "Update a lead",
                "DELETE /leads/{id}": "Delete a lead"
            },
            "appointments": {
                "GET /appointments": "List appointments",
                "POST /appointments": "Create appointment/meeting",
                "DELETE /appointments/{id}": "Cancel appointment"
            },
            "calls": {
                "GET /calls": "Get call logs",
                "POST /calls": "Log a call from external system"
            },
            "tasks": {
                "GET /tasks": "Get tasks",
                "POST /tasks": "Create a task"
            },
            "activities": {
                "GET /activities/{lead_id}": "Get activities for a lead",
                "POST /activities": "Log an activity"
            },
            "webhooks": {
                "GET /webhooks": "List webhook subscriptions",
                "POST /webhooks": "Subscribe to events",
                "DELETE /webhooks/{id}": "Unsubscribe from events"
            }
        },
        "webhook_events": [
            "lead.created",
            "lead.updated",
            "lead.deleted",
            "call.completed",
            "appointment.created",
            "appointment.cancelled",
            "task.created",
            "task.completed"
        ],
        "permissions": {
            "read": "View leads, appointments, calls, tasks",
            "write": "Create/update leads, appointments, calls, tasks",
            "delete": "Delete leads",
            "admin": "Manage webhooks, full access"
        }
    }


# Export models and router
__all__ = [
    'router',
    'APIKey',
    'CreateAPIKeyRequest',
    'PublicLeadCreate',
    'PublicAppointmentCreate',
    'PublicCallLog',
    'PublicTaskCreate',
    'WebhookSubscription',
    'get_api_key_user'
]
