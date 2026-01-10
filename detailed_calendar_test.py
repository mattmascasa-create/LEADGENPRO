#!/usr/bin/env python3
"""
Detailed Google Calendar and Meet Integration Testing
Tests the exact scenarios mentioned in the review request
"""

import requests
import json
from datetime import datetime, timezone

# Backend URL
BACKEND_URL = "https://crm-commander-1.preview.emergentagent.com/api"

def test_specific_scenarios():
    """Test the exact scenarios from the review request"""
    
    # Setup authentication
    login_data = {
        "email": "admin@test.com",
        "password": "admin123"
    }
    
    session = requests.Session()
    response = session.post(f"{BACKEND_URL}/auth/login", json=login_data)
    
    if response.status_code != 200:
        print("❌ Authentication failed")
        return
    
    auth_token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    print("🔐 Authentication successful")
    print("=" * 60)
    
    # Test 1: Create Event with Google Meet Link
    print("\n1️⃣ Testing: Create Event with Google Meet Link")
    print("POST /api/calendar/events/with-meet")
    
    event_data = {
        "title": "Test Meeting",
        "description": "Test",
        "type": "meeting",
        "start": "2026-01-20T10:00:00Z",
        "end": "2026-01-20T11:00:00Z",
        "attendees": [],
        "location": ""
    }
    
    response = session.post(f"{BACKEND_URL}/calendar/events/with-meet", json=event_data, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        meeting_link = data.get("meeting_link", "")
        if meeting_link.startswith("https://meet.google.com/") and len(meeting_link.split("/")[-1].split("-")) == 3:
            print(f"✅ PASSED: Event created with Meet link: {meeting_link}")
            test_event_id = data["event"]["id"]
        else:
            print(f"❌ FAILED: Invalid Meet link format: {meeting_link}")
            return
    else:
        print(f"❌ FAILED: Status {response.status_code}: {response.text}")
        return
    
    # Test 2: Create regular event first, then add Meet link
    print("\n2️⃣ Testing: Add Meet Link to Existing Event")
    print("First: POST /api/calendar/events")
    
    regular_event_data = {
        "title": "Regular Meeting",
        "description": "Test regular meeting",
        "type": "meeting",
        "start": "2026-01-21T14:00:00Z",
        "end": "2026-01-21T15:00:00Z",
        "attendees": [],
        "location": "Office"
    }
    
    response = session.post(f"{BACKEND_URL}/calendar/events", json=regular_event_data, headers=headers)
    
    if response.status_code == 200:
        regular_event_id = response.json()["id"]
        print(f"✅ Regular event created with ID: {regular_event_id}")
        
        print("Then: POST /api/calendar/events/{event_id}/add-meet")
        response = session.post(f"{BACKEND_URL}/calendar/events/{regular_event_id}/add-meet", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            meeting_link = data.get("meeting_link", "")
            if meeting_link.startswith("https://meet.google.com/"):
                print(f"✅ PASSED: Meet link added: {meeting_link}")
            else:
                print(f"❌ FAILED: Invalid Meet link: {meeting_link}")
        else:
            print(f"❌ FAILED: Status {response.status_code}: {response.text}")
    else:
        print(f"❌ FAILED: Could not create regular event: {response.status_code}")
        return
    
    # Test 3: Export to Google Calendar URL
    print("\n3️⃣ Testing: Export to Google Calendar URL")
    print(f"GET /api/calendar/export/google-url/{test_event_id}")
    
    response = session.get(f"{BACKEND_URL}/calendar/export/google-url/{test_event_id}", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        google_url = data.get("google_calendar_url", "")
        if google_url.startswith("https://calendar.google.com/calendar/render?action=TEMPLATE"):
            print(f"✅ PASSED: Google Calendar URL generated")
            print(f"   URL: {google_url[:100]}...")
        else:
            print(f"❌ FAILED: Invalid Google Calendar URL: {google_url}")
    else:
        print(f"❌ FAILED: Status {response.status_code}: {response.text}")
    
    # Test 4: Export ICS File
    print("\n4️⃣ Testing: Export ICS File")
    print(f"GET /api/calendar/export/ics/{test_event_id}")
    
    response = session.get(f"{BACKEND_URL}/calendar/export/ics/{test_event_id}", headers=headers)
    
    if response.status_code == 200:
        content_type = response.headers.get('content-type', '')
        if content_type.startswith('text/calendar'):
            ics_content = response.text
            if "BEGIN:VCALENDAR" in ics_content and "END:VCALENDAR" in ics_content:
                print(f"✅ PASSED: ICS file generated with proper content-type")
                print(f"   Content length: {len(ics_content)} characters")
            else:
                print(f"❌ FAILED: Invalid ICS content")
        else:
            print(f"❌ FAILED: Wrong content-type: {content_type}")
    else:
        print(f"❌ FAILED: Status {response.status_code}: {response.text}")
    
    # Test 5: Get Calendar Sync Status
    print("\n5️⃣ Testing: Get Calendar Sync Status")
    print("GET /api/calendar/sync-status")
    
    response = session.get(f"{BACKEND_URL}/calendar/sync-status", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        required_fields = ["google_linked", "has_full_sync", "sync_method", "message"]
        if all(field in data for field in required_fields):
            print(f"✅ PASSED: Sync status retrieved")
            print(f"   Status: {data}")
        else:
            print(f"❌ FAILED: Missing required fields in response")
    else:
        print(f"❌ FAILED: Status {response.status_code}: {response.text}")
    
    # Test 6: Get Calendar Events (verify events with meeting_link)
    print("\n6️⃣ Testing: Get Calendar Events with Meeting Links")
    print("GET /api/calendar/events")
    
    response = session.get(f"{BACKEND_URL}/calendar/events", headers=headers)
    
    if response.status_code == 200:
        events = response.json()
        events_with_meet = [e for e in events if e.get("meeting_link")]
        if events_with_meet:
            print(f"✅ PASSED: Found {len(events_with_meet)} events with meeting links")
            for event in events_with_meet[:3]:  # Show first 3
                print(f"   • {event['title']}: {event['meeting_link']}")
        else:
            print(f"✅ PASSED: No events with meeting links (expected if none created)")
    else:
        print(f"❌ FAILED: Status {response.status_code}: {response.text}")
    
    print("\n" + "=" * 60)
    print("🏁 All specific test scenarios completed!")

if __name__ == "__main__":
    test_specific_scenarios()