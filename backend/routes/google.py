"""
Google Integration routes for LeadGen Pro
Handles Google Drive and Calendar OAuth, sync, and file operations
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid
import os
import logging
import tempfile
import aiohttp

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from core.database import db
from core.security import User, get_current_user

# Google OAuth config
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', os.environ.get('GOOGLE_DRIVE_REDIRECT_URI'))
FRONTEND_URL = os.environ.get('FRONTEND_URL')

# Google OAuth Scopes for different services
GOOGLE_SCOPES = {
    'drive': 'https://www.googleapis.com/auth/drive',
    'calendar': 'https://www.googleapis.com/auth/calendar',
    'meet': 'https://www.googleapis.com/auth/calendar.events',
    'gmail_readonly': 'https://www.googleapis.com/auth/gmail.readonly',
    'profile': 'https://www.googleapis.com/auth/userinfo.profile',
    'email': 'https://www.googleapis.com/auth/userinfo.email'
}

router = APIRouter(tags=["Google Integration"])


# ==================== MODELS ====================

class CalendarSyncRequest(BaseModel):
    sync_direction: str = "both"  # "to_google", "from_google", "both"
    days_ahead: int = 30
    days_back: int = 7


# ==================== HELPER FUNCTIONS ====================

async def get_google_credentials(user_id: str):
    """Get Google credentials for a user"""
    creds_doc = await db.google_credentials.find_one({"user_id": user_id})
    if not creds_doc:
        return None
    
    creds = Credentials(
        token=creds_doc["access_token"],
        refresh_token=creds_doc.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=creds_doc.get("scopes", [])
    )
    
    # Auto-refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(GoogleRequest())
            await db.google_credentials.update_one(
                {"user_id": user_id},
                {"$set": {
                    "access_token": creds.token,
                    "expiry": creds.expiry.isoformat() if creds.expiry else None,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
        except Exception as e:
            logging.error(f"Failed to refresh Google token: {e}")
            return None
    
    return creds


async def get_drive_service(user: User):
    """Get Google Drive service with auto-refresh credentials"""
    creds = await get_google_credentials(user.id)
    if not creds:
        return None
    return build('drive', 'v3', credentials=creds)


async def get_calendar_service(user: User):
    """Get Google Calendar service"""
    creds = await get_google_credentials(user.id)
    if not creds:
        return None
    return build('calendar', 'v3', credentials=creds)


# ==================== GOOGLE STATUS & CONNECT ====================

@router.get("/google/status")
async def get_google_status(current_user: User = Depends(get_current_user)):
    """Check which Google services are connected"""
    creds_doc = await db.google_credentials.find_one({"user_id": current_user.id})
    
    if not creds_doc:
        return {
            "connected": False,
            "services": {
                "drive": False,
                "calendar": False,
                "meet": False
            },
            "message": "No Google account connected"
        }
    
    scopes = creds_doc.get("scopes", [])
    
    return {
        "connected": True,
        "email": creds_doc.get("email"),
        "name": creds_doc.get("name"),
        "picture": creds_doc.get("picture"),
        "connected_at": creds_doc.get("created_at"),
        "services": {
            "drive": GOOGLE_SCOPES['drive'] in scopes,
            "calendar": GOOGLE_SCOPES['calendar'] in scopes,
            "meet": GOOGLE_SCOPES['meet'] in scopes
        }
    }


@router.get("/google/connect")
async def connect_google(
    services: str = "drive,calendar",
    current_user: User = Depends(get_current_user)
):
    """Initiate Google OAuth flow for selected services"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=400, 
            detail="Google integration not configured. Please add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to environment."
        )
    
    # Build scopes based on requested services
    requested_services = [s.strip() for s in services.split(',')]
    scopes = [GOOGLE_SCOPES['profile'], GOOGLE_SCOPES['email']]
    
    for service in requested_services:
        if service in GOOGLE_SCOPES:
            scopes.append(GOOGLE_SCOPES[service])
    
    # Store state for CSRF protection
    state = f"{current_user.id}:{uuid.uuid4().hex[:16]}"
    await db.oauth_states.insert_one({
        "state": state,
        "user_id": current_user.id,
        "services": requested_services,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    # Build OAuth URL
    oauth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        "response_type=code&"
        f"scope={' '.join(scopes)}&"
        "access_type=offline&"
        "prompt=consent&"
        f"state={state}"
    )
    
    return {"auth_url": oauth_url}


@router.get("/google/callback")
async def google_callback(code: str = None, state: str = None, error: str = None):
    """Handle Google OAuth callback"""
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/settings?error={error}")
    
    if not code or not state:
        return RedirectResponse(f"{FRONTEND_URL}/settings?error=missing_params")
    
    # Verify state
    state_doc = await db.oauth_states.find_one({"state": state})
    if not state_doc:
        return RedirectResponse(f"{FRONTEND_URL}/settings?error=invalid_state")
    
    user_id = state_doc["user_id"]
    
    # Clean up state
    await db.oauth_states.delete_one({"state": state})
    
    try:
        # Exchange code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=token_data) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logging.error(f"Token exchange failed: {error_text}")
                    return RedirectResponse(f"{FRONTEND_URL}/settings?error=token_exchange_failed")
                
                tokens = await resp.json()
        
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 3600)
        
        # Get user info from Google
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            ) as resp:
                if resp.status == 200:
                    user_info = await resp.json()
                else:
                    user_info = {}
        
        # Decode the scopes from the token
        scopes = tokens.get("scope", "").split(" ")
        
        # Store credentials
        creds_doc = {
            "user_id": user_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "scopes": scopes,
            "email": user_info.get("email"),
            "name": user_info.get("name"),
            "picture": user_info.get("picture"),
            "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Upsert credentials
        await db.google_credentials.update_one(
            {"user_id": user_id},
            {"$set": creds_doc},
            upsert=True
        )
        
        # Also update legacy drive_credentials for backward compatibility
        await db.drive_credentials.update_one(
            {"user_id": user_id},
            {"$set": {
                "user_id": user_id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "scopes": scopes,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True
        )
        
        return RedirectResponse(f"{FRONTEND_URL}/settings?google=connected")
        
    except Exception as e:
        logging.error(f"Google OAuth error: {e}")
        return RedirectResponse(f"{FRONTEND_URL}/settings?error=oauth_failed")


@router.post("/google/disconnect")
async def disconnect_google(current_user: User = Depends(get_current_user)):
    """Disconnect Google account"""
    await db.google_credentials.delete_one({"user_id": current_user.id})
    await db.drive_credentials.delete_one({"user_id": current_user.id})
    return {"message": "Google account disconnected"}


# ==================== GOOGLE CALENDAR ====================

@router.get("/google/calendar/events")
async def get_google_calendar_events(
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get events from user's Google Calendar"""
    service = await get_calendar_service(current_user)
    if not service:
        raise HTTPException(status_code=400, detail="Google Calendar not connected")
    
    try:
        now = datetime.now(timezone.utc)
        time_min = time_min or now.isoformat()
        time_max = time_max or (now + timedelta(days=30)).isoformat()
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=100,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        return {"events": events}
    except Exception as e:
        logging.error(f"Failed to get calendar events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/google/calendar/events")
async def create_google_calendar_event(
    title: str,
    start_time: datetime,
    end_time: datetime,
    description: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    add_meet_link: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Create an event in user's Google Calendar with optional Meet link"""
    service = await get_calendar_service(current_user)
    if not service:
        raise HTTPException(status_code=400, detail="Google Calendar not connected")
    
    try:
        event = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            }
        }
        
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]
        
        if add_meet_link:
            event['conferenceData'] = {
                'createRequest': {
                    'requestId': uuid.uuid4().hex,
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }
        
        created_event = service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1 if add_meet_link else 0,
            sendUpdates='all' if attendees else 'none'
        ).execute()
        
        return {
            "id": created_event.get('id'),
            "html_link": created_event.get('htmlLink'),
            "meet_link": created_event.get('hangoutLink'),
            "message": "Event created successfully"
        }
    except Exception as e:
        logging.error(f"Failed to create calendar event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== TWO-WAY GOOGLE CALENDAR SYNC ====================

@router.post("/google/calendar/sync")
async def sync_google_calendar(
    sync_request: CalendarSyncRequest,
    current_user: User = Depends(get_current_user)
):
    """Full two-way sync between LeadGen Pro and Google Calendar"""
    service = await get_calendar_service(current_user)
    if not service:
        raise HTTPException(status_code=400, detail="Google Calendar not connected. Please connect your Google account first.")
    
    sync_results = {
        "pushed_to_google": 0,
        "pulled_from_google": 0,
        "errors": [],
        "synced_at": datetime.now(timezone.utc).isoformat()
    }
    
    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(days=sync_request.days_back)).isoformat()
    time_max = (now + timedelta(days=sync_request.days_ahead)).isoformat()
    
    try:
        # PUSH: LeadGen Pro events -> Google Calendar
        if sync_request.sync_direction in ["to_google", "both"]:
            leadgen_events = await db.calendar_events.find({
                "created_by": current_user.id,
                "start": {"$gte": time_min, "$lte": time_max}
            }, {"_id": 0}).to_list(500)
            
            for event in leadgen_events:
                # Check if already synced
                if event.get("google_event_id"):
                    continue
                
                try:
                    google_event = {
                        'summary': event['title'],
                        'description': event.get('description', '') + f"\n\n[Synced from LeadGen Pro - ID: {event['id']}]",
                        'start': {
                            'dateTime': event['start'] if 'T' in event['start'] else event['start'] + 'T00:00:00Z',
                            'timeZone': 'UTC',
                        },
                        'end': {
                            'dateTime': event['end'] if 'T' in event['end'] else event['end'] + 'T23:59:59Z',
                            'timeZone': 'UTC',
                        }
                    }
                    
                    if event.get('meeting_link'):
                        google_event['description'] += f"\n\nMeeting Link: {event['meeting_link']}"
                        google_event['location'] = event['meeting_link']
                    
                    created = service.events().insert(
                        calendarId='primary',
                        body=google_event
                    ).execute()
                    
                    # Store Google event ID for future syncs
                    await db.calendar_events.update_one(
                        {"id": event['id']},
                        {"$set": {
                            "google_event_id": created['id'],
                            "google_synced_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                    sync_results["pushed_to_google"] += 1
                    
                except Exception as e:
                    sync_results["errors"].append(f"Push error for {event['title']}: {str(e)}")
        
        # PULL: Google Calendar events -> LeadGen Pro
        if sync_request.sync_direction in ["from_google", "both"]:
            google_events = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=500,
                singleEvents=True,
                orderBy='startTime'
            ).execute().get('items', [])
            
            for g_event in google_events:
                google_id = g_event['id']
                
                # Check if already exists in LeadGen Pro
                existing = await db.calendar_events.find_one({"google_event_id": google_id})
                if existing:
                    continue
                
                start_time = g_event.get('start', {}).get('dateTime') or g_event.get('start', {}).get('date')
                if not start_time:
                    continue
                
                try:
                    end_time = g_event.get('end', {}).get('dateTime') or g_event.get('end', {}).get('date')
                    
                    new_event = {
                        "id": str(uuid.uuid4()),
                        "title": g_event.get('summary', 'Untitled Event'),
                        "description": g_event.get('description', ''),
                        "start": start_time,
                        "end": end_time or start_time,
                        "location": g_event.get('location', ''),
                        "meeting_link": g_event.get('hangoutLink', ''),
                        "created_by": current_user.id,
                        "attendees": [att.get('email') for att in g_event.get('attendees', []) if att.get('email')],
                        "google_event_id": google_id,
                        "google_synced_at": datetime.now(timezone.utc).isoformat(),
                        "source": "google_calendar",
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await db.calendar_events.insert_one(new_event)
                    sync_results["pulled_from_google"] += 1
                    
                except Exception as e:
                    sync_results["errors"].append(f"Pull error for {g_event.get('summary', 'Unknown')}: {str(e)}")
        
        # Update sync status
        await db.google_credentials.update_one(
            {"user_id": current_user.id},
            {"$set": {
                "last_calendar_sync": datetime.now(timezone.utc).isoformat(),
                "sync_stats": sync_results
            }}
        )
        
        return {
            "success": True,
            "message": f"Sync complete! Pushed {sync_results['pushed_to_google']} events to Google, pulled {sync_results['pulled_from_google']} events from Google.",
            "results": sync_results
        }
        
    except Exception as e:
        logging.error(f"Calendar sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.put("/google/calendar/events/{event_id}")
async def update_google_calendar_event(
    event_id: str,
    title: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    description: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Update an event in Google Calendar (two-way sync)"""
    service = await get_calendar_service(current_user)
    if not service:
        raise HTTPException(status_code=400, detail="Google Calendar not connected")
    
    # Find the local event
    local_event = await db.calendar_events.find_one({"id": event_id})
    if not local_event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    google_event_id = local_event.get("google_event_id")
    
    # Update local event
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if title:
        update_data["title"] = title
    if start_time:
        update_data["start"] = start_time.isoformat()
    if end_time:
        update_data["end"] = end_time.isoformat()
    if description:
        update_data["description"] = description
    
    await db.calendar_events.update_one({"id": event_id}, {"$set": update_data})
    
    # If synced to Google, update there too
    if google_event_id:
        try:
            existing = service.events().get(calendarId='primary', eventId=google_event_id).execute()
            
            if title:
                existing['summary'] = title
            if start_time:
                existing['start'] = {'dateTime': start_time.isoformat(), 'timeZone': 'UTC'}
            if end_time:
                existing['end'] = {'dateTime': end_time.isoformat(), 'timeZone': 'UTC'}
            if description:
                existing['description'] = description
            
            service.events().update(
                calendarId='primary',
                eventId=google_event_id,
                body=existing
            ).execute()
            
            return {"success": True, "message": "Event updated in both LeadGen Pro and Google Calendar"}
        except Exception as e:
            logging.error(f"Failed to update Google event: {e}")
            return {"success": True, "message": "Event updated locally but Google sync failed", "error": str(e)}
    
    return {"success": True, "message": "Event updated locally"}


@router.delete("/google/calendar/events/{event_id}")
async def delete_google_calendar_event(
    event_id: str,
    delete_from_google: bool = True,
    current_user: User = Depends(get_current_user)
):
    """Delete an event from LeadGen Pro and optionally from Google Calendar"""
    local_event = await db.calendar_events.find_one({"id": event_id})
    if not local_event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    google_event_id = local_event.get("google_event_id")
    
    # Delete from Google if connected and requested
    if google_event_id and delete_from_google:
        service = await get_calendar_service(current_user)
        if service:
            try:
                service.events().delete(calendarId='primary', eventId=google_event_id).execute()
            except Exception as e:
                logging.error(f"Failed to delete from Google Calendar: {e}")
    
    # Delete locally
    await db.calendar_events.delete_one({"id": event_id})
    
    return {"success": True, "message": "Event deleted"}


@router.get("/google/calendar/sync-status")
async def get_google_calendar_sync_status(current_user: User = Depends(get_current_user)):
    """Get detailed Google Calendar sync status"""
    creds_doc = await db.google_credentials.find_one({"user_id": current_user.id})
    
    if not creds_doc:
        return {
            "connected": False,
            "can_sync": False,
            "message": "Google Calendar not connected. Connect your Google account to enable two-way sync."
        }
    
    has_calendar_scope = GOOGLE_SCOPES['calendar'] in creds_doc.get("scopes", [])
    
    # Count synced events
    synced_count = await db.calendar_events.count_documents({
        "created_by": current_user.id,
        "google_event_id": {"$exists": True, "$ne": None}
    })
    
    pending_count = await db.calendar_events.count_documents({
        "created_by": current_user.id,
        "google_event_id": {"$exists": False}
    })
    
    return {
        "connected": True,
        "can_sync": has_calendar_scope,
        "email": creds_doc.get("email"),
        "last_sync": creds_doc.get("last_calendar_sync"),
        "sync_stats": creds_doc.get("sync_stats"),
        "events_synced": synced_count,
        "events_pending": pending_count,
        "message": "Two-way sync enabled" if has_calendar_scope else "Calendar permissions not granted"
    }


@router.post("/google/calendar/push-event/{event_id}")
async def push_single_event_to_google(
    event_id: str,
    current_user: User = Depends(get_current_user)
):
    """Push a single LeadGen Pro event to Google Calendar"""
    service = await get_calendar_service(current_user)
    if not service:
        raise HTTPException(status_code=400, detail="Google Calendar not connected")
    
    event = await db.calendar_events.find_one({"id": event_id})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event.get("google_event_id"):
        return {"success": False, "message": "Event already synced to Google Calendar"}
    
    try:
        google_event = {
            'summary': event['title'],
            'description': event.get('description', ''),
            'start': {
                'dateTime': event['start'] if 'T' in event['start'] else event['start'] + 'T00:00:00Z',
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': event['end'] if 'T' in event['end'] else event['end'] + 'T23:59:59Z',
                'timeZone': 'UTC',
            }
        }
        
        if event.get('meeting_link'):
            google_event['location'] = event['meeting_link']
        
        created = service.events().insert(calendarId='primary', body=google_event).execute()
        
        await db.calendar_events.update_one(
            {"id": event_id},
            {"$set": {
                "google_event_id": created['id'],
                "google_synced_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {
            "success": True,
            "google_event_id": created['id'],
            "google_link": created.get('htmlLink'),
            "message": "Event pushed to Google Calendar"
        }
    except Exception as e:
        logging.error(f"Failed to push event to Google: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== GOOGLE DRIVE ====================

@router.get("/drive/status")
async def get_drive_status(current_user: User = Depends(get_current_user)):
    """Check if Google Drive is connected for current user"""
    creds_doc = await db.google_credentials.find_one({"user_id": current_user.id})
    
    if not creds_doc:
        return {"connected": False, "message": "Google Drive not connected"}
    
    has_drive_scope = GOOGLE_SCOPES['drive'] in creds_doc.get("scopes", [])
    
    return {
        "connected": has_drive_scope,
        "email": creds_doc.get("email") if has_drive_scope else None,
        "connected_at": creds_doc.get("updated_at") if has_drive_scope else None
    }


@router.get("/drive/connect")
async def connect_drive(current_user: User = Depends(get_current_user)):
    """Redirect to unified Google connect with Drive scope"""
    return await connect_google(services="drive", current_user=current_user)


@router.get("/drive/callback")
async def drive_callback(code: str = None, state: str = None, error: str = None):
    """Legacy callback - redirect to unified Google callback"""
    return await google_callback(code=code, state=state, error=error)


@router.get("/drive/disconnect")
async def disconnect_drive(current_user: User = Depends(get_current_user)):
    """Disconnect Google Drive"""
    await db.drive_credentials.delete_one({"user_id": current_user.id})
    return {"success": True, "message": "Google Drive disconnected"}


@router.get("/drive/files")
async def list_drive_files(
    folder_id: str = None,
    page_token: str = None,
    current_user: User = Depends(get_current_user)
):
    """List files from Google Drive"""
    service = await get_drive_service(current_user)
    if not service:
        raise HTTPException(status_code=400, detail="Google Drive not connected")
    
    try:
        # Build query
        query_parts = ["trashed = false"]
        if folder_id:
            query_parts.append(f"'{folder_id}' in parents")
        else:
            query_parts.append("'root' in parents")
        
        query = " and ".join(query_parts)
        
        # Execute query
        results = service.files().list(
            q=query,
            pageSize=50,
            pageToken=page_token,
            fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, webViewLink, iconLink, thumbnailLink, parents)",
            orderBy="folder,name"
        ).execute()
        
        files = results.get('files', [])
        next_page_token = results.get('nextPageToken')
        
        # Format response
        formatted_files = []
        for file in files:
            formatted_files.append({
                "id": file.get('id'),
                "name": file.get('name'),
                "mimeType": file.get('mimeType'),
                "isFolder": file.get('mimeType') == 'application/vnd.google-apps.folder',
                "size": int(file.get('size', 0)) if file.get('size') else None,
                "modifiedTime": file.get('modifiedTime'),
                "webViewLink": file.get('webViewLink'),
                "iconLink": file.get('iconLink'),
                "thumbnailLink": file.get('thumbnailLink')
            })
        
        return {
            "files": formatted_files,
            "nextPageToken": next_page_token
        }
    
    except Exception as e:
        logging.error(f"Failed to list Drive files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.post("/drive/folder")
async def create_drive_folder(
    name: str,
    parent_id: str = None,
    current_user: User = Depends(get_current_user)
):
    """Create a folder in Google Drive"""
    service = await get_drive_service(current_user)
    if not service:
        raise HTTPException(status_code=400, detail="Google Drive not connected")
    
    try:
        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
        
        folder = service.files().create(
            body=file_metadata,
            fields='id, name, webViewLink'
        ).execute()
        
        return {
            "success": True,
            "folder": {
                "id": folder.get('id'),
                "name": folder.get('name'),
                "webViewLink": folder.get('webViewLink')
            }
        }
    
    except Exception as e:
        logging.error(f"Failed to create folder: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create folder: {str(e)}")


@router.post("/drive/upload")
async def upload_to_drive(
    file: UploadFile = File(...),
    folder_id: str = Form(None),
    current_user: User = Depends(get_current_user)
):
    """Upload a file to Google Drive"""
    service = await get_drive_service(current_user)
    if not service:
        raise HTTPException(status_code=400, detail="Google Drive not connected")
    
    try:
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        file_metadata = {'name': file.filename}
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        media = MediaFileUpload(tmp_path, mimetype=file.content_type, resumable=True)
        
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink, size'
        ).execute()
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        return {
            "success": True,
            "file": {
                "id": uploaded_file.get('id'),
                "name": uploaded_file.get('name'),
                "webViewLink": uploaded_file.get('webViewLink'),
                "size": uploaded_file.get('size')
            }
        }
    
    except Exception as e:
        logging.error(f"Failed to upload file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.delete("/drive/files/{file_id}")
async def delete_drive_file(file_id: str, current_user: User = Depends(get_current_user)):
    """Delete a file from Google Drive"""
    service = await get_drive_service(current_user)
    if not service:
        raise HTTPException(status_code=400, detail="Google Drive not connected")
    
    try:
        service.files().delete(fileId=file_id).execute()
        return {"success": True, "message": "File deleted"}
    
    except Exception as e:
        logging.error(f"Failed to delete file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.get("/drive/search")
async def search_drive_files(
    query: str,
    current_user: User = Depends(get_current_user)
):
    """Search files in Google Drive"""
    service = await get_drive_service(current_user)
    if not service:
        raise HTTPException(status_code=400, detail="Google Drive not connected")
    
    try:
        search_query = f"name contains '{query}' and trashed = false"
        
        results = service.files().list(
            q=search_query,
            pageSize=50,
            fields="files(id, name, mimeType, size, modifiedTime, webViewLink, iconLink, thumbnailLink)",
            orderBy="modifiedTime desc"
        ).execute()
        
        files = results.get('files', [])
        
        formatted_files = []
        for file in files:
            formatted_files.append({
                "id": file.get('id'),
                "name": file.get('name'),
                "mimeType": file.get('mimeType'),
                "isFolder": file.get('mimeType') == 'application/vnd.google-apps.folder',
                "size": int(file.get('size', 0)) if file.get('size') else None,
                "modifiedTime": file.get('modifiedTime'),
                "webViewLink": file.get('webViewLink'),
                "iconLink": file.get('iconLink'),
                "thumbnailLink": file.get('thumbnailLink')
            })
        
        return {"files": formatted_files}
    
    except Exception as e:
        logging.error(f"Failed to search Drive files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to search files: {str(e)}")


# Export router and helper functions
__all__ = [
    'router',
    'CalendarSyncRequest',
    'get_google_credentials',
    'get_drive_service',
    'get_calendar_service',
    'GOOGLE_SCOPES'
]
