#!/usr/bin/env python3
"""
Google Calendar and Meet Integration Testing for LeadGen Pro
Tests all Google Calendar and Meet related endpoints
"""

import requests
import json
import uuid
from datetime import datetime, timedelta, timezone
import os
import sys

# Backend URL from frontend .env
BACKEND_URL = "https://sales-ai-pro.preview.emergentagent.com/api"

class GoogleCalendarMeetTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.auth_token = None
        self.test_user_id = None
        self.test_event_id = None
        self.test_event_with_meet_id = None
        self.results = {
            "passed": 0,
            "failed": 0,
            "errors": []
        }
    
    def log_result(self, test_name, success, message=""):
        if success:
            self.results["passed"] += 1
            print(f"✅ {test_name}: PASSED {message}")
        else:
            self.results["failed"] += 1
            self.results["errors"].append(f"{test_name}: {message}")
            print(f"❌ {test_name}: FAILED - {message}")
    
    def make_request(self, method, endpoint, data=None, headers=None):
        """Make HTTP request with proper error handling"""
        url = f"{self.base_url}{endpoint}"
        
        # Add auth header if token exists
        if self.auth_token and headers is None:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
        elif self.auth_token and headers:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, headers=headers, timeout=30)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, headers=headers, timeout=30)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=30)
            else:
                return None, f"Unsupported method: {method}"
            
            return response, None
        except requests.exceptions.RequestException as e:
            return None, str(e)
    
    def setup_authentication(self):
        """Setup authentication using admin credentials"""
        print("\n🔐 Setting up authentication...")
        
        login_data = {
            "email": "admin@test.com",
            "password": "admin123"
        }
        
        response, error = self.make_request("POST", "/auth/login", login_data)
        
        if error:
            self.log_result("Authentication Setup", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data and "user" in data:
                self.auth_token = data["access_token"]
                self.test_user_id = data["user"]["id"]
                self.log_result("Authentication Setup", True, f"Logged in as: {data['user']['email']}")
                return True
            else:
                self.log_result("Authentication Setup", False, "Missing token or user in response")
                return False
        else:
            self.log_result("Authentication Setup", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_get_calendar_events(self):
        """Test GET /api/calendar/events"""
        print("\n📅 Testing Get Calendar Events...")
        
        if not self.auth_token:
            self.log_result("Get Calendar Events", False, "No auth token available")
            return False
        
        response, error = self.make_request("GET", "/calendar/events")
        
        if error:
            self.log_result("Get Calendar Events", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            events = response.json()
            if isinstance(events, list):
                self.log_result("Get Calendar Events", True, f"Retrieved {len(events)} events")
                return True
            else:
                self.log_result("Get Calendar Events", False, "Response is not a list")
                return False
        else:
            self.log_result("Get Calendar Events", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_create_regular_event(self):
        """Test creating a regular calendar event (for later adding Meet link)"""
        print("\n📝 Testing Create Regular Event...")
        
        if not self.auth_token:
            self.log_result("Create Regular Event", False, "No auth token available")
            return False
        
        # Create event for tomorrow at 2 PM
        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        start_time = start_time.replace(hour=14, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)
        
        event_data = {
            "title": "Test Meeting",
            "description": "Test meeting for Google Calendar integration",
            "type": "meeting",
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "attendees": [],
            "location": "Conference Room A"
        }
        
        response, error = self.make_request("POST", "/calendar/events", event_data)
        
        if error:
            self.log_result("Create Regular Event", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            event = response.json()
            if "id" in event and event["title"] == event_data["title"]:
                self.test_event_id = event["id"]
                self.log_result("Create Regular Event", True, f"Event created with ID: {self.test_event_id}")
                return True
            else:
                self.log_result("Create Regular Event", False, "Invalid event data in response")
                return False
        else:
            self.log_result("Create Regular Event", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_create_event_with_meet_link(self):
        """Test POST /api/calendar/events/with-meet"""
        print("\n🎥 Testing Create Event with Google Meet Link...")
        
        if not self.auth_token:
            self.log_result("Create Event with Meet", False, "No auth token available")
            return False
        
        # Create event for tomorrow at 3 PM
        start_time = datetime.now(timezone.utc) + timedelta(days=1)
        start_time = start_time.replace(hour=15, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)
        
        event_data = {
            "title": "Test Meeting with Meet",
            "description": "Test meeting with Google Meet integration",
            "type": "meeting",
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "attendees": [],
            "location": ""
        }
        
        response, error = self.make_request("POST", "/calendar/events/with-meet", event_data)
        
        if error:
            self.log_result("Create Event with Meet", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            data = response.json()
            if ("event" in data and "meeting_link" in data and 
                data["meeting_link"] and data["meeting_link"].startswith("https://meet.google.com/")):
                
                self.test_event_with_meet_id = data["event"]["id"]
                meet_link = data["meeting_link"]
                
                # Verify Meet link format: https://meet.google.com/xxx-xxxx-xxx
                import re
                meet_pattern = r"https://meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}"
                if re.match(meet_pattern, meet_link):
                    self.log_result("Create Event with Meet", True, f"Event created with Meet link: {meet_link}")
                    return True
                else:
                    self.log_result("Create Event with Meet", False, f"Invalid Meet link format: {meet_link}")
                    return False
            else:
                self.log_result("Create Event with Meet", False, "Missing event or meeting_link in response")
                return False
        else:
            self.log_result("Create Event with Meet", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_add_meet_to_existing_event(self):
        """Test POST /api/calendar/events/{event_id}/add-meet"""
        print("\n➕ Testing Add Meet Link to Existing Event...")
        
        if not self.auth_token or not self.test_event_id:
            self.log_result("Add Meet to Event", False, "No auth token or event ID available")
            return False
        
        response, error = self.make_request("POST", f"/calendar/events/{self.test_event_id}/add-meet")
        
        if error:
            self.log_result("Add Meet to Event", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            data = response.json()
            if ("event" in data and "meeting_link" in data and 
                data["meeting_link"] and data["meeting_link"].startswith("https://meet.google.com/")):
                
                meet_link = data["meeting_link"]
                
                # Verify Meet link format
                import re
                meet_pattern = r"https://meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}"
                if re.match(meet_pattern, meet_link):
                    self.log_result("Add Meet to Event", True, f"Meet link added: {meet_link}")
                    return True
                else:
                    self.log_result("Add Meet to Event", False, f"Invalid Meet link format: {meet_link}")
                    return False
            else:
                self.log_result("Add Meet to Event", False, "Missing event or meeting_link in response")
                return False
        else:
            self.log_result("Add Meet to Event", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_export_google_calendar_url(self):
        """Test GET /api/calendar/export/google-url/{event_id}"""
        print("\n🔗 Testing Export to Google Calendar URL...")
        
        if not self.auth_token or not self.test_event_with_meet_id:
            self.log_result("Export Google Calendar URL", False, "No auth token or event ID available")
            return False
        
        response, error = self.make_request("GET", f"/calendar/export/google-url/{self.test_event_with_meet_id}")
        
        if error:
            self.log_result("Export Google Calendar URL", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            data = response.json()
            if ("google_calendar_url" in data and 
                data["google_calendar_url"].startswith("https://calendar.google.com/calendar/render?action=TEMPLATE")):
                
                google_url = data["google_calendar_url"]
                self.log_result("Export Google Calendar URL", True, f"Google Calendar URL generated: {google_url[:100]}...")
                return True
            else:
                self.log_result("Export Google Calendar URL", False, "Invalid or missing google_calendar_url")
                return False
        else:
            self.log_result("Export Google Calendar URL", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_export_ics_file(self):
        """Test GET /api/calendar/export/ics/{event_id}"""
        print("\n📄 Testing Export ICS File...")
        
        if not self.auth_token or not self.test_event_with_meet_id:
            self.log_result("Export ICS File", False, "No auth token or event ID available")
            return False
        
        response, error = self.make_request("GET", f"/calendar/export/ics/{self.test_event_with_meet_id}")
        
        if error:
            self.log_result("Export ICS File", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if content_type.startswith('text/calendar'):
                ics_content = response.text
                
                # Verify ICS content contains required elements
                required_elements = [
                    "BEGIN:VCALENDAR",
                    "END:VCALENDAR", 
                    "BEGIN:VEVENT",
                    "END:VEVENT",
                    "SUMMARY:Test Meeting with Meet",
                    "DTSTART:",
                    "DTEND:"
                ]
                
                missing_elements = [elem for elem in required_elements if elem not in ics_content]
                
                if not missing_elements:
                    self.log_result("Export ICS File", True, f"ICS file generated with {len(ics_content)} characters")
                    return True
                else:
                    self.log_result("Export ICS File", False, f"Missing ICS elements: {missing_elements}")
                    return False
            else:
                self.log_result("Export ICS File", False, f"Wrong content type: {content_type}")
                return False
        else:
            self.log_result("Export ICS File", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_calendar_sync_status(self):
        """Test GET /api/calendar/sync-status"""
        print("\n🔄 Testing Calendar Sync Status...")
        
        if not self.auth_token:
            self.log_result("Calendar Sync Status", False, "No auth token available")
            return False
        
        response, error = self.make_request("GET", "/calendar/sync-status")
        
        if error:
            self.log_result("Calendar Sync Status", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            data = response.json()
            required_fields = ["google_linked", "has_full_sync", "sync_method", "message"]
            
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                self.log_result("Calendar Sync Status", True, f"Sync status: {data}")
                return True
            else:
                self.log_result("Calendar Sync Status", False, f"Missing fields: {missing_fields}")
                return False
        else:
            self.log_result("Calendar Sync Status", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_calendar_events_with_meet_links(self):
        """Test that calendar events with meeting links are returned correctly"""
        print("\n🔍 Testing Calendar Events with Meet Links...")
        
        if not self.auth_token:
            self.log_result("Events with Meet Links", False, "No auth token available")
            return False
        
        response, error = self.make_request("GET", "/calendar/events")
        
        if error:
            self.log_result("Events with Meet Links", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            events = response.json()
            
            # Find events with meeting links
            events_with_meet = [event for event in events if event.get("meeting_link")]
            
            if events_with_meet:
                # Verify at least one event has a proper Meet link
                valid_meet_links = []
                for event in events_with_meet:
                    meet_link = event.get("meeting_link", "")
                    if meet_link.startswith("https://meet.google.com/"):
                        valid_meet_links.append(meet_link)
                
                if valid_meet_links:
                    self.log_result("Events with Meet Links", True, f"Found {len(valid_meet_links)} events with valid Meet links")
                    return True
                else:
                    self.log_result("Events with Meet Links", False, "No events with valid Meet links found")
                    return False
            else:
                self.log_result("Events with Meet Links", True, "No events with Meet links found (expected if no events created)")
                return True
        else:
            self.log_result("Events with Meet Links", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def run_all_tests(self):
        """Run all Google Calendar and Meet integration tests"""
        print("🚀 Starting Google Calendar & Meet Integration Testing...")
        print(f"🌐 Backend URL: {self.base_url}")
        print("=" * 70)
        
        # Setup authentication
        if not self.setup_authentication():
            print("❌ Authentication failed - cannot proceed with tests")
            return self.results
        
        # Test sequence
        print("\n📅 CALENDAR EVENTS TESTS")
        print("-" * 40)
        self.test_get_calendar_events()
        self.test_create_regular_event()
        
        print("\n🎥 GOOGLE MEET INTEGRATION TESTS")
        print("-" * 40)
        self.test_create_event_with_meet_link()
        self.test_add_meet_to_existing_event()
        
        print("\n🔗 GOOGLE CALENDAR EXPORT TESTS")
        print("-" * 40)
        self.test_export_google_calendar_url()
        self.test_export_ics_file()
        
        print("\n🔄 SYNC STATUS TESTS")
        print("-" * 40)
        self.test_calendar_sync_status()
        
        print("\n🔍 VERIFICATION TESTS")
        print("-" * 40)
        self.test_calendar_events_with_meet_links()
        
        # Print final results
        print("\n" + "=" * 70)
        print("🏁 GOOGLE CALENDAR & MEET TESTING COMPLETE")
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['errors']:
            print("\n🚨 FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        success_rate = (self.results['passed'] / (self.results['passed'] + self.results['failed'])) * 100 if (self.results['passed'] + self.results['failed']) > 0 else 0
        print(f"\n📊 Success Rate: {success_rate:.1f}%")
        
        return self.results

if __name__ == "__main__":
    tester = GoogleCalendarMeetTester()
    results = tester.run_all_tests()
    
    # Exit with error code if tests failed
    if results['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)