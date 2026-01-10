"""
Calendar and Appointment routes for LeadGen Pro
Handles internal calendar events, appointments, and Google Calendar sync
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
import logging
import random
import string
import urllib.parse

from core.database import db
from core.security import User, get_current_user

router = APIRouter(tags=["Calendar"])


# ==================== MODELS ====================

class Appointment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    lead_id: Optional[str] = None
    employee_id: str
    scheduled_at: datetime
    duration: int = 30
    status: str = "scheduled"
    meeting_link: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AppointmentCreate(BaseModel):
    title: str
    lead_id: Optional[str] = None
    employee_id: str
    scheduled_at: datetime
    duration: int = 30
    meeting_link: Optional[str] = None
    notes: Optional[str] = None


class CalendarEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    type: str = "meeting"  # meeting, call, task, reminder
    start: datetime
    end: datetime
    attendees: List[str] = []
    attendee_names: List[str] = []
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CalendarEventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    type: str = "meeting"
    start: datetime
    end: datetime
    attendees: List[str] = []
    location: Optional[str] = None
    meeting_link: Optional[str] = None


class Activity(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    description: str
    lead_id: Optional[str] = None
    user_id: str
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==================== HELPER FUNCTIONS ====================

def generate_google_meet_link() -> str:
    """Generate a unique Google Meet-style link"""
    chars = string.ascii_lowercase
    part1 = ''.join(random.choices(chars, k=3))
    part2 = ''.join(random.choices(chars, k=4))
    part3 = ''.join(random.choices(chars, k=3))
    return f"https://meet.google.com/{part1}-{part2}-{part3}"


# ==================== APPOINTMENT ENDPOINTS ====================

@router.get("/appointments", response_model=List[Appointment])
async def get_appointments(current_user: User = Depends(get_current_user)):
    """Get all appointments for the user"""
    query = {}
    if current_user.role == "employee":
        query["employee_id"] = current_user.id
    
    appointments = await db.appointments.find(query, {"_id": 0}).to_list(1000)
    return [Appointment(**apt) for apt in appointments]


@router.post("/appointments", response_model=Appointment)
async def create_appointment(apt_data: AppointmentCreate, current_user: User = Depends(get_current_user)):
    """Create a new appointment"""
    appointment = Appointment(**apt_data.model_dump())
    doc = appointment.model_dump()
    doc['scheduled_at'] = doc['scheduled_at'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.appointments.insert_one(doc)
    
    # Log activity
    activity = Activity(
        type="appointment_created",
        description=f"Scheduled: {appointment.title}",
        lead_id=appointment.lead_id,
        user_id=current_user.id
    )
    activity_doc = activity.model_dump()
    activity_doc['created_at'] = activity_doc['created_at'].isoformat()
    await db.activities.insert_one(activity_doc)
    
    return appointment


# ==================== CALENDAR EVENT ENDPOINTS ====================

@router.get("/calendar/events", response_model=List[CalendarEvent])
async def get_calendar_events(current_user: User = Depends(get_current_user)):
    """Get all calendar events visible to the user"""
    events = await db.calendar_events.find({}, {"_id": 0}).sort("start", 1).to_list(1000)
    return [CalendarEvent(**event) for event in events]


@router.post("/calendar/events", response_model=CalendarEvent)
async def create_calendar_event(event_data: CalendarEventCreate, current_user: User = Depends(get_current_user)):
    """Create a new calendar event"""
    # Get attendee names
    attendee_names = []
    for attendee_id in event_data.attendees:
        user = await db.users.find_one({"id": attendee_id}, {"_id": 0})
        if user:
            attendee_names.append(user["full_name"])
    
    event = CalendarEvent(
        **event_data.model_dump(),
        attendee_names=attendee_names,
        created_by=current_user.id
    )
    
    doc = event.model_dump()
    doc['start'] = doc['start'].isoformat()
    doc['end'] = doc['end'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.calendar_events.insert_one(doc)
    
    # Log activity
    activity = Activity(
        type="event_created",
        description=f"Created {event.type}: {event.title}",
        user_id=current_user.id,
        metadata={"event_id": event.id, "event_type": event.type}
    )
    activity_doc = activity.model_dump()
    activity_doc['created_at'] = activity_doc['created_at'].isoformat()
    await db.activities.insert_one(activity_doc)
    
    return event


@router.delete("/calendar/events/{event_id}")
async def delete_calendar_event(event_id: str, current_user: User = Depends(get_current_user)):
    """Delete a calendar event"""
    result = await db.calendar_events.delete_one({"id": event_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event deleted"}


# ==================== GOOGLE MEET INTEGRATION ====================

@router.post("/calendar/events/with-meet")
async def create_event_with_meet(event_data: CalendarEventCreate, current_user: User = Depends(get_current_user)):
    """Create a calendar event with automatic Google Meet link"""
    # Get attendee names
    attendee_names = []
    for attendee_id in event_data.attendees:
        user = await db.users.find_one({"id": attendee_id}, {"_id": 0})
        if user:
            attendee_names.append(user["full_name"])
    
    # Generate Meet link
    meet_link = generate_google_meet_link()
    
    # Get event data without the meeting_link field to avoid duplication
    event_dict = event_data.model_dump()
    event_dict.pop('meeting_link', None)
    
    event = CalendarEvent(
        **event_dict,
        attendee_names=attendee_names,
        created_by=current_user.id,
        meeting_link=meet_link
    )
    
    doc = event.model_dump()
    doc['start'] = doc['start'].isoformat()
    doc['end'] = doc['end'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.calendar_events.insert_one(doc)
    
    # Log activity
    activity = Activity(
        type="meeting_created",
        description=f"Created meeting with Google Meet: {event.title}",
        user_id=current_user.id,
        metadata={"event_id": event.id, "meeting_link": meet_link}
    )
    activity_doc = activity.model_dump()
    activity_doc['created_at'] = activity_doc['created_at'].isoformat()
    await db.activities.insert_one(activity_doc)
    
    return {
        "event": event,
        "meeting_link": meet_link,
        "message": "Event created with Google Meet link"
    }


@router.post("/calendar/events/{event_id}/add-meet")
async def add_meet_to_event(event_id: str, current_user: User = Depends(get_current_user)):
    """Add a Google Meet link to an existing event"""
    event = await db.calendar_events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event.get("meeting_link"):
        return {"event": event, "meeting_link": event["meeting_link"], "message": "Event already has a meeting link"}
    
    # Generate Meet link
    meet_link = generate_google_meet_link()
    
    await db.calendar_events.update_one(
        {"id": event_id},
        {"$set": {"meeting_link": meet_link}}
    )
    
    event["meeting_link"] = meet_link
    
    return {
        "event": event,
        "meeting_link": meet_link,
        "message": "Google Meet link added to event"
    }


# ==================== CALENDAR EXPORT ====================

@router.get("/calendar/export/ics/{event_id}")
async def export_event_to_ics(event_id: str, current_user: User = Depends(get_current_user)):
    """Export a calendar event as ICS file for Google Calendar import"""
    event = await db.calendar_events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Parse dates
    start = datetime.fromisoformat(event['start'].replace('Z', '+00:00')) if isinstance(event['start'], str) else event['start']
    end = datetime.fromisoformat(event['end'].replace('Z', '+00:00')) if isinstance(event['end'], str) else event['end']
    
    # Build ICS content
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//LeadGen Pro//Calendar//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}
DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}
DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}
UID:{event['id']}@leadgenpro
SUMMARY:{event['title']}
DESCRIPTION:{event.get('description', '')}
LOCATION:{event.get('location', '')}
"""
    
    if event.get('meeting_link'):
        ics_content += f"URL:{event['meeting_link']}\n"
        ics_content += f"X-GOOGLE-CONFERENCE:{event['meeting_link']}\n"
    
    ics_content += """STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""
    
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f"attachment; filename=event_{event_id}.ics"
        }
    )


@router.get("/calendar/export/google-url/{event_id}")
async def get_google_calendar_url(event_id: str, current_user: User = Depends(get_current_user)):
    """Get a URL to add event directly to Google Calendar"""
    event = await db.calendar_events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Parse dates
    start = datetime.fromisoformat(event['start'].replace('Z', '+00:00')) if isinstance(event['start'], str) else event['start']
    end = datetime.fromisoformat(event['end'].replace('Z', '+00:00')) if isinstance(event['end'], str) else event['end']
    
    # Build Google Calendar URL
    title = urllib.parse.quote(event['title'])
    dates = f"{start.strftime('%Y%m%dT%H%M%SZ')}/{end.strftime('%Y%m%dT%H%M%SZ')}"
    details = urllib.parse.quote(event.get('description', '') + (f"\n\nMeeting Link: {event.get('meeting_link', '')}" if event.get('meeting_link') else ""))
    location = urllib.parse.quote(event.get('location', ''))
    
    google_url = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={title}&dates={dates}&details={details}&location={location}"
    
    return {
        "google_calendar_url": google_url,
        "event": event
    }


@router.get("/calendar/sync-status")
async def get_calendar_sync_status(current_user: User = Depends(get_current_user)):
    """Get Google Calendar sync status for the user"""
    user = await db.users.find_one({"id": current_user.id}, {"_id": 0})
    google_linked = user.get("google_linked", False)
    
    # Check if user has Google credentials for full sync
    google_creds = await db.google_credentials.find_one({"user_id": current_user.id})
    has_full_sync = google_creds is not None and "calendar" in str(google_creds.get("scopes", []))
    
    return {
        "google_linked": google_linked,
        "has_full_sync": has_full_sync,
        "sync_method": "full" if has_full_sync else ("manual" if google_linked else "none"),
        "message": "Full two-way sync available" if has_full_sync else 
                   ("Manual export to Google Calendar available" if google_linked else 
                    "Sign in with Google to enable calendar sync")
    }


# Export models for use in other modules
__all__ = [
    'router',
    'Appointment',
    'AppointmentCreate',
    'CalendarEvent',
    'CalendarEventCreate',
    'generate_google_meet_link'
]
