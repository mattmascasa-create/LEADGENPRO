"""
Booking routes for LeadGen Pro
Handles public booking page, availability slots, and meeting scheduling
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid
import os
import logging

from core.database import db
from core.security import User, get_current_user

router = APIRouter(prefix="/booking", tags=["Booking"])


# ==================== MODELS ====================

class BookingRequest(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    company: Optional[str] = None
    notes: Optional[str] = None
    datetime: datetime
    duration: int = 30


class AvailabilitySlot(BaseModel):
    time: str
    available: bool = True


class MeetingType(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    duration: int = 30  # minutes
    description: Optional[str] = None
    color: str = "#3B82F6"
    buffer_before: int = 0  # minutes before meeting
    buffer_after: int = 0  # minutes after meeting
    active: bool = True


# ==================== PUBLIC BOOKING ENDPOINTS ====================

@router.get("/{user_id}")
async def get_booking_info(user_id: str):
    """Get user info and booked slots for public booking page"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all booked events for this user
    booked_events = await db.calendar_events.find({
        "$or": [
            {"created_by": user_id},
            {"attendees": user_id}
        ]
    }, {"_id": 0}).to_list(1000)
    
    booked_slots = [event['start'] for event in booked_events]
    
    return {
        "user": user,
        "booked_slots": booked_slots
    }


@router.get("/{user_id}/slots")
async def get_available_slots(user_id: str, date: str):
    """Get available time slots for a specific date"""
    from datetime import datetime as dt
    
    try:
        target_date = dt.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    start_of_day = target_date.replace(hour=0, minute=0, second=0)
    end_of_day = target_date.replace(hour=23, minute=59, second=59)
    
    booked_events = await db.calendar_events.find({
        "$or": [
            {"created_by": user_id},
            {"attendees": user_id}
        ],
        "start": {
            "$gte": start_of_day.isoformat(),
            "$lte": end_of_day.isoformat()
        }
    }, {"_id": 0}).to_list(100)
    
    available_slots = []
    booked_times = set()
    
    for event in booked_events:
        event_start = dt.fromisoformat(event['start'].replace('Z', '+00:00') if 'Z' in event['start'] else event['start'])
        booked_times.add(event_start.strftime("%H:%M"))
    
    now = dt.now()
    for hour in range(9, 17):  # 9 AM to 5 PM
        for minute in [0, 30]:
            slot_time = f"{hour:02d}:{minute:02d}"
            
            # Skip past times for today
            if target_date.date() == now.date():
                slot_datetime = target_date.replace(hour=hour, minute=minute)
                if slot_datetime < now:
                    continue
            
            available_slots.append(AvailabilitySlot(
                time=slot_time,
                available=slot_time not in booked_times
            ))
    
    return available_slots


@router.post("/{user_id}/book")
async def book_meeting(
    user_id: str,
    booking: BookingRequest,
    background_tasks: BackgroundTasks
):
    """Book a meeting with a user (public endpoint)"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create calendar event
    event_id = str(uuid.uuid4())
    event = {
        "id": event_id,
        "title": f"Meeting with {booking.name}",
        "description": f"Booked by: {booking.name}\nEmail: {booking.email}\nPhone: {booking.phone or 'N/A'}\nCompany: {booking.company or 'N/A'}\nNotes: {booking.notes or 'None'}",
        "type": "meeting",
        "start": booking.datetime.isoformat(),
        "end": (booking.datetime + timedelta(minutes=booking.duration)).isoformat(),
        "attendees": [user_id],
        "attendee_names": [user.get("full_name", "Unknown")],
        "created_by": "booking_system",
        "booking_info": {
            "guest_name": booking.name,
            "guest_email": booking.email,
            "guest_phone": booking.phone,
            "guest_company": booking.company,
            "notes": booking.notes
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.calendar_events.insert_one(event)
    
    # Create lead from booking
    lead_id = str(uuid.uuid4())
    name_parts = booking.name.split(' ', 1)
    lead = {
        "id": lead_id,
        "first_name": name_parts[0],
        "last_name": name_parts[1] if len(name_parts) > 1 else "",
        "email": booking.email,
        "phone": booking.phone,
        "company": booking.company or "Unknown",
        "status": "new",
        "stage": "meeting_scheduled",
        "score": 60,
        "notes": f"Auto-created from booking. Notes: {booking.notes or 'None'}",
        "assigned_to": user_id,
        "created_by": user_id,
        "tags": ["booked_meeting"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.leads.insert_one(lead)
    
    # Create notification for the user
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": "new_booking",
        "title": "📅 New Meeting Booked!",
        "message": f"{booking.name} from {booking.company or 'Unknown'} booked a meeting for {booking.datetime.strftime('%B %d at %I:%M %p')}",
        "lead_id": lead_id,
        "read": False,
        "data": {
            "event_id": event_id,
            "guest_name": booking.name,
            "guest_email": booking.email
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "success": True,
        "message": "Meeting booked successfully",
        "event_id": event_id,
        "lead_id": lead_id,
        "booking": {
            "name": booking.name,
            "email": booking.email,
            "datetime": booking.datetime.isoformat(),
            "duration": booking.duration
        }
    }


@router.post("/{user_id}/book-simple")
async def book_simple_meeting(
    user_id: str,
    booking: BookingRequest,
    background_tasks: BackgroundTasks
):
    """Simple booking endpoint (same as /book but alternative path)"""
    return await book_meeting(user_id, booking, background_tasks)


@router.get("/link/{user_id}")
async def get_booking_link(user_id: str, current_user: User = Depends(get_current_user)):
    """Get the public booking link for a user"""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    base_url = os.environ.get('REACT_APP_BACKEND_URL', '').replace('/api', '')
    if not base_url:
        base_url = "https://your-domain.com"
    
    return {
        "booking_link": f"{base_url}/book/{user_id}",
        "user_id": user_id
    }


# ==================== MEETING TYPES ====================

@router.get("/{user_id}/meeting-types")
async def get_meeting_types(user_id: str):
    """Get available meeting types for a user"""
    meeting_types = await db.meeting_types.find(
        {"user_id": user_id, "active": True}, {"_id": 0}
    ).to_list(20)
    
    # Return defaults if none configured
    if not meeting_types:
        return [
            {
                "id": "default-30",
                "name": "30 Minute Meeting",
                "duration": 30,
                "description": "A quick 30-minute call",
                "color": "#3B82F6"
            },
            {
                "id": "default-60",
                "name": "60 Minute Meeting",
                "duration": 60,
                "description": "A detailed hour-long discussion",
                "color": "#10B981"
            }
        ]
    
    return meeting_types


@router.get("/{user_id}/slots/{meeting_type_id}")
async def get_slots_for_meeting_type(
    user_id: str,
    meeting_type_id: str,
    date: str
):
    """Get available slots for a specific meeting type"""
    from datetime import datetime as dt
    
    # Get meeting type details
    meeting_type = await db.meeting_types.find_one(
        {"id": meeting_type_id, "user_id": user_id}, {"_id": 0}
    )
    
    duration = 30  # default
    if meeting_type:
        duration = meeting_type.get("duration", 30)
    elif meeting_type_id == "default-60":
        duration = 60
    
    try:
        target_date = dt.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    start_of_day = target_date.replace(hour=0, minute=0, second=0)
    end_of_day = target_date.replace(hour=23, minute=59, second=59)
    
    booked_events = await db.calendar_events.find({
        "$or": [{"created_by": user_id}, {"attendees": user_id}],
        "start": {"$gte": start_of_day.isoformat(), "$lte": end_of_day.isoformat()}
    }, {"_id": 0}).to_list(100)
    
    # Build set of booked times
    booked_ranges = []
    for event in booked_events:
        event_start = dt.fromisoformat(event['start'].replace('Z', '+00:00') if 'Z' in event['start'] else event['start'])
        event_end = dt.fromisoformat(event['end'].replace('Z', '+00:00') if 'Z' in event['end'] else event['end'])
        booked_ranges.append((event_start, event_end))
    
    available_slots = []
    now = dt.now()
    
    # Generate slots based on duration
    slot_interval = 30 if duration <= 30 else 60
    
    for hour in range(9, 17):
        for minute in range(0, 60, slot_interval):
            slot_start = target_date.replace(hour=hour, minute=minute)
            slot_end = slot_start + timedelta(minutes=duration)
            
            # Skip if slot ends after 5 PM
            if slot_end.hour >= 17 and slot_end.minute > 0:
                continue
            
            # Skip past times
            if target_date.date() == now.date() and slot_start < now:
                continue
            
            # Check conflicts
            is_available = True
            for booked_start, booked_end in booked_ranges:
                if not (slot_end <= booked_start or slot_start >= booked_end):
                    is_available = False
                    break
            
            available_slots.append({
                "time": slot_start.strftime("%H:%M"),
                "available": is_available,
                "duration": duration
            })
    
    return available_slots


# Export models
__all__ = [
    'router',
    'BookingRequest',
    'AvailabilitySlot',
    'MeetingType'
]
