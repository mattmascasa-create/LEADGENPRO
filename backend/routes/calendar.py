"""
Calendar Routes - Events, Google Meet Integration, Export
"""

import random
import string
import urllib.parse
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from models.schemas import CalendarEvent, CalendarEventCreate, User, Activity
from services.database import db
from services.auth import get_current_user

router = APIRouter(prefix="/calendar", tags=["Calendar"])


def generate_google_meet_link():
    """Generate a unique Google Meet-style link"""
    chars = string.ascii_lowercase
    part1 = ''.join(random.choices(chars, k=3))
    part2 = ''.join(random.choices(chars, k=4))
    part3 = ''.join(random.choices(chars, k=3))
    return f"https://meet.google.com/{part1}-{part2}-{part3}"


@router.get("/events")
async def get_calendar_events(current_user: User = Depends(get_current_user)):
    """Get all calendar events"""
    events = await db.calendar_events.find({}, {"_id": 0}).to_list(1000)
    return events


@router.post("/events")
async def create_calendar_event(
    event_data: CalendarEventCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new calendar event"""
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
    return event


@router.post("/events/with-meet")
async def create_event_with_meet(
    event_data: CalendarEventCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a calendar event with automatic Google Meet link"""
    attendee_names = []
    for attendee_id in event_data.attendees:
        user = await db.users.find_one({"id": attendee_id}, {"_id": 0})
        if user:
            attendee_names.append(user["full_name"])
    
    meet_link = generate_google_meet_link()
    
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


@router.get("/events/{event_id}")
async def get_calendar_event(event_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific calendar event"""
    event = await db.calendar_events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.put("/events/{event_id}")
async def update_calendar_event(
    event_id: str,
    event_data: CalendarEventCreate,
    current_user: User = Depends(get_current_user)
):
    """Update a calendar event"""
    event = await db.calendar_events.find_one({"id": event_id})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    update_dict = event_data.model_dump()
    update_dict['start'] = update_dict['start'].isoformat()
    update_dict['end'] = update_dict['end'].isoformat()
    
    await db.calendar_events.update_one({"id": event_id}, {"$set": update_dict})
    
    updated_event = await db.calendar_events.find_one({"id": event_id}, {"_id": 0})
    return updated_event


@router.delete("/events/{event_id}")
async def delete_calendar_event(event_id: str, current_user: User = Depends(get_current_user)):
    """Delete a calendar event"""
    result = await db.calendar_events.delete_one({"id": event_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event deleted"}


@router.post("/events/{event_id}/add-meet")
async def add_meet_to_event(event_id: str, current_user: User = Depends(get_current_user)):
    """Add a Google Meet link to an existing event"""
    event = await db.calendar_events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event.get("meeting_link"):
        return {"event": event, "meeting_link": event["meeting_link"], "message": "Event already has a meeting link"}
    
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


@router.get("/export/ics/{event_id}")
async def export_event_to_ics(event_id: str, current_user: User = Depends(get_current_user)):
    """Export a calendar event as ICS file for Google Calendar import"""
    event = await db.calendar_events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    start = datetime.fromisoformat(event['start'].replace('Z', '+00:00')) if isinstance(event['start'], str) else event['start']
    end = datetime.fromisoformat(event['end'].replace('Z', '+00:00')) if isinstance(event['end'], str) else event['end']
    
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


@router.get("/export/google-url/{event_id}")
async def get_google_calendar_url(event_id: str, current_user: User = Depends(get_current_user)):
    """Get a URL to add event directly to Google Calendar"""
    event = await db.calendar_events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    start = datetime.fromisoformat(event['start'].replace('Z', '+00:00')) if isinstance(event['start'], str) else event['start']
    end = datetime.fromisoformat(event['end'].replace('Z', '+00:00')) if isinstance(event['end'], str) else event['end']
    
    title = urllib.parse.quote(event['title'])
    dates = f"{start.strftime('%Y%m%dT%H%M%SZ')}/{end.strftime('%Y%m%dT%H%M%SZ')}"
    details = urllib.parse.quote(event.get('description', '') + (f"\n\nMeeting Link: {event.get('meeting_link', '')}" if event.get('meeting_link') else ""))
    location = urllib.parse.quote(event.get('location', ''))
    
    google_url = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={title}&dates={dates}&details={details}&location={location}"
    
    return {
        "google_calendar_url": google_url,
        "event": event
    }


@router.get("/sync-status")
async def get_calendar_sync_status(current_user: User = Depends(get_current_user)):
    """Get Google Calendar sync status for the user"""
    user = await db.users.find_one({"id": current_user.id}, {"_id": 0})
    google_linked = user.get("google_linked", False)
    
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
