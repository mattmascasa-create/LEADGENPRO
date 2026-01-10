"""
Meetings routes for LeadGen Pro
Handles meeting types, availability rules, and user status/presence
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from core.database import db
from core.security import User, get_current_user

router = APIRouter(tags=["Meetings"])


# ==================== MODELS ====================

class MeetingType(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str  # "Quick Call", "Discovery Call", "Demo", etc.
    duration: int  # minutes
    description: Optional[str] = None
    color: str = "#3B82F6"
    location: str = "google_meet"  # google_meet, zoom, phone, in_person
    buffer_before: int = 0  # minutes
    buffer_after: int = 0  # minutes
    max_bookings_per_day: Optional[int] = None
    questions: List[Dict[str, Any]] = []  # Custom intake questions
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MeetingTypeCreate(BaseModel):
    name: str
    duration: int
    description: Optional[str] = None
    color: str = "#3B82F6"
    location: str = "google_meet"
    buffer_before: int = 0
    buffer_after: int = 0
    max_bookings_per_day: Optional[int] = None
    questions: List[Dict[str, Any]] = []


class AvailabilityRule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    day_of_week: int  # 0=Monday, 6=Sunday
    start_time: str  # "09:00"
    end_time: str  # "17:00"
    is_available: bool = True


class UserStatusUpdate(BaseModel):
    status: str  # online, away, busy, do_not_disturb, offline
    status_text: Optional[str] = None
    clear_at: Optional[datetime] = None


# Status presets
STATUS_PRESETS = [
    {"emoji": "🟢", "text": "Available", "status": "online"},
    {"emoji": "🔴", "text": "In a meeting", "status": "busy"},
    {"emoji": "📞", "text": "On a call", "status": "busy"},
    {"emoji": "🍽️", "text": "At lunch", "status": "away"},
    {"emoji": "🏠", "text": "Working remotely", "status": "online"},
    {"emoji": "🤒", "text": "Out sick", "status": "offline"},
    {"emoji": "🌴", "text": "On vacation", "status": "offline"},
    {"emoji": "🎯", "text": "Focusing", "status": "do_not_disturb"},
]


# ==================== MEETING TYPE ENDPOINTS ====================

@router.get("/meeting-types")
async def get_meeting_types(current_user: User = Depends(get_current_user)):
    """Get user's meeting types (like Calendly event types)"""
    meeting_types = await db.meeting_types.find(
        {"user_id": current_user.id, "is_active": True}, 
        {"_id": 0}
    ).to_list(100)
    
    # Return default types if none exist
    if not meeting_types:
        default_types = [
            {"id": str(uuid.uuid4()), "user_id": current_user.id, "name": "Quick Call", "duration": 15, "color": "#10B981", "location": "google_meet", "description": "A brief 15-minute call"},
            {"id": str(uuid.uuid4()), "user_id": current_user.id, "name": "Discovery Call", "duration": 30, "color": "#3B82F6", "location": "google_meet", "description": "Learn about your needs"},
            {"id": str(uuid.uuid4()), "user_id": current_user.id, "name": "Product Demo", "duration": 45, "color": "#8B5CF6", "location": "google_meet", "description": "Full product demonstration"},
            {"id": str(uuid.uuid4()), "user_id": current_user.id, "name": "Strategy Session", "duration": 60, "color": "#F59E0B", "location": "google_meet", "description": "In-depth strategy discussion"},
        ]
        for mt in default_types:
            mt["is_active"] = True
            mt["created_at"] = datetime.now(timezone.utc).isoformat()
            await db.meeting_types.insert_one(mt)
        # Re-fetch without _id to ensure clean data
        meeting_types = await db.meeting_types.find(
            {"user_id": current_user.id, "is_active": True}, 
            {"_id": 0}
        ).to_list(100)
    
    return meeting_types


@router.post("/meeting-types")
async def create_meeting_type(
    data: MeetingTypeCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new meeting type"""
    meeting_type = MeetingType(
        user_id=current_user.id,
        **data.model_dump()
    )
    doc = meeting_type.model_dump()
    await db.meeting_types.insert_one(doc)
    return meeting_type


@router.put("/meeting-types/{meeting_type_id}")
async def update_meeting_type(
    meeting_type_id: str,
    data: MeetingTypeCreate,
    current_user: User = Depends(get_current_user)
):
    """Update a meeting type"""
    result = await db.meeting_types.update_one(
        {"id": meeting_type_id, "user_id": current_user.id},
        {"$set": data.model_dump()}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Meeting type not found")
    return {"message": "Meeting type updated"}


@router.delete("/meeting-types/{meeting_type_id}")
async def delete_meeting_type(
    meeting_type_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete (deactivate) a meeting type"""
    await db.meeting_types.update_one(
        {"id": meeting_type_id, "user_id": current_user.id},
        {"$set": {"is_active": False}}
    )
    return {"message": "Meeting type deleted"}


# ==================== AVAILABILITY ENDPOINTS ====================

@router.get("/availability")
async def get_availability(current_user: User = Depends(get_current_user)):
    """Get user's availability rules"""
    rules = await db.availability_rules.find(
        {"user_id": current_user.id}, 
        {"_id": 0}
    ).to_list(100)
    
    # Return default availability if none set
    if not rules:
        default_rules = []
        for day in range(5):  # Mon-Fri
            default_rules.append({
                "id": str(uuid.uuid4()),
                "user_id": current_user.id,
                "day_of_week": day,
                "start_time": "09:00",
                "end_time": "17:00",
                "is_available": True
            })
        for rule in default_rules:
            await db.availability_rules.insert_one(rule)
        # Re-fetch without _id
        rules = await db.availability_rules.find(
            {"user_id": current_user.id}, 
            {"_id": 0}
        ).to_list(100)
    
    return rules


@router.put("/availability")
async def update_availability(
    rules: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user)
):
    """Update availability rules"""
    # Delete existing rules
    await db.availability_rules.delete_many({"user_id": current_user.id})
    
    # Insert new rules
    for rule in rules:
        rule["user_id"] = current_user.id
        rule["id"] = str(uuid.uuid4())
        await db.availability_rules.insert_one(rule)
    
    return {"message": "Availability updated"}


# ==================== USER STATUS/PRESENCE ENDPOINTS ====================

@router.get("/users/status")
async def get_all_user_statuses(current_user: User = Depends(get_current_user)):
    """Get status of all users for presence indicators"""
    statuses = await db.user_statuses.find({}, {"_id": 0}).to_list(1000)
    
    # Get all users to show default status for those without explicit status
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    
    status_map = {s["user_id"]: s for s in statuses}
    
    result = []
    for user in users:
        user_status = status_map.get(user["id"], {
            "user_id": user["id"],
            "status": "offline",
            "status_text": None,
            "last_seen": None
        })
        user_status["user"] = user
        result.append(user_status)
        
        # Auto-update last seen for current user
        if user["id"] == current_user.id:
            await db.user_statuses.update_one(
                {"user_id": current_user.id},
                {"$set": {"last_seen": datetime.now(timezone.utc).isoformat()}},
                upsert=True
            )
    
    return result


@router.get("/users/{user_id}/status")
async def get_user_status(user_id: str, current_user: User = Depends(get_current_user)):
    """Get status of a specific user"""
    status = await db.user_statuses.find_one({"user_id": user_id}, {"_id": 0})
    if not status:
        return {
            "user_id": user_id,
            "status": "offline",
            "status_text": None,
            "last_seen": None
        }
    return status


@router.put("/users/status")
async def update_user_status(
    status_update: UserStatusUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update current user's status"""
    update_data = {
        "user_id": current_user.id,
        "status": status_update.status,
        "status_text": status_update.status_text,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "last_seen": datetime.now(timezone.utc).isoformat()
    }
    
    if status_update.clear_at:
        update_data["clear_at"] = status_update.clear_at.isoformat()
    
    await db.user_statuses.update_one(
        {"user_id": current_user.id},
        {"$set": update_data},
        upsert=True
    )
    
    return {"message": "Status updated", "status": update_data}


@router.get("/users/status/presets")
async def get_status_presets(current_user: User = Depends(get_current_user)):
    """Get available status presets"""
    return STATUS_PRESETS


# Export models and router
__all__ = [
    'router',
    'MeetingType',
    'MeetingTypeCreate',
    'AvailabilityRule',
    'UserStatusUpdate',
    'STATUS_PRESETS'
]
