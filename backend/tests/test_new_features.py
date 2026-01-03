#!/usr/bin/env python3
"""
Test New Features for LeadGen Pro
Tests the newly added features: Calendar, AI Assistant, Users, and Call Analysis
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
import os
import sys

# Backend URL from frontend .env
BACKEND_URL = "https://teamsales.preview.emergentagent.com/api"

class NewFeaturesTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.auth_token = None
        self.test_user_id = None
        self.test_event_id = None
        self.test_call_id = None
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
    
    def setup_test_user(self):
        """Setup test user with the specified credentials"""
        print("\n🔐 Setting up test user...")
        
        # Use the specified test credentials
        test_email = "finaltest@example.com"
        test_password = "FinalTest123!"
        
        # Try to register first
        user_data = {
            "email": test_email,
            "password": test_password,
            "full_name": "Final Test User",
            "role": "admin",
            "company": "Test Company"
        }
        
        response, error = self.make_request("POST", "/auth/register", user_data)
        
        if response and response.status_code == 200:
            data = response.json()
            self.auth_token = data["access_token"]
            self.test_user_id = data["user"]["id"]
            self.log_result("User Setup (Register)", True, f"User registered with ID: {self.test_user_id}")
            return True
        else:
            # If registration fails (user might exist), try login
            login_data = {
                "email": test_email,
                "password": test_password
            }
            
            login_response, login_error = self.make_request("POST", "/auth/login", login_data)
            
            if login_response and login_response.status_code == 200:
                data = login_response.json()
                self.auth_token = data["access_token"]
                self.test_user_id = data["user"]["id"]
                self.log_result("User Setup (Login)", True, f"User logged in with ID: {self.test_user_id}")
                return True
            else:
                self.log_result("User Setup", False, f"Failed to register or login: {error or login_error}")
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
    
    def test_create_calendar_event(self):
        """Test POST /api/calendar/events"""
        print("\n📅 Testing Create Calendar Event...")
        
        if not self.auth_token:
            self.log_result("Create Calendar Event", False, "No auth token available")
            return False
        
        # Create event with the specified data
        event_data = {
            "title": "Team Standup",
            "description": "Daily sync meeting",
            "type": "meeting",
            "start": "2026-01-05T09:00:00Z",
            "end": "2026-01-05T09:30:00Z",
            "attendees": [],
            "location": "Conference Room A"
        }
        
        response, error = self.make_request("POST", "/calendar/events", event_data)
        
        if error:
            self.log_result("Create Calendar Event", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            event = response.json()
            if "id" in event and event["title"] == event_data["title"]:
                self.test_event_id = event["id"]
                self.log_result("Create Calendar Event", True, f"Event created with ID: {self.test_event_id}")
                return True
            else:
                self.log_result("Create Calendar Event", False, "Invalid event data in response")
                return False
        else:
            self.log_result("Create Calendar Event", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_delete_calendar_event(self):
        """Test DELETE /api/calendar/events/{event_id}"""
        print("\n🗑️ Testing Delete Calendar Event...")
        
        if not self.auth_token or not self.test_event_id:
            self.log_result("Delete Calendar Event", False, "No auth token or event ID available")
            return False
        
        response, error = self.make_request("DELETE", f"/calendar/events/{self.test_event_id}")
        
        if error:
            self.log_result("Delete Calendar Event", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            result = response.json()
            if "message" in result:
                self.log_result("Delete Calendar Event", True, "Event deleted successfully")
                return True
            else:
                self.log_result("Delete Calendar Event", False, "Invalid response format")
                return False
        else:
            self.log_result("Delete Calendar Event", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_ai_assistant_chat(self):
        """Test POST /api/assistant/chat"""
        print("\n🤖 Testing AI Assistant Chat...")
        
        if not self.auth_token:
            self.log_result("AI Assistant Chat", False, "No auth token available")
            return False
        
        chat_data = {
            "message": "How do I add a new lead?",
            "context": "platform_help"
        }
        
        response, error = self.make_request("POST", "/assistant/chat", chat_data)
        
        if error:
            self.log_result("AI Assistant Chat", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            result = response.json()
            if "response" in result and isinstance(result["response"], str) and len(result["response"]) > 0:
                self.log_result("AI Assistant Chat", True, f"Got helpful response: {result['response'][:100]}...")
                return True
            else:
                self.log_result("AI Assistant Chat", False, "Invalid or empty response")
                return False
        else:
            self.log_result("AI Assistant Chat", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_get_users(self):
        """Test GET /api/users"""
        print("\n👥 Testing Get Users...")
        
        if not self.auth_token:
            self.log_result("Get Users", False, "No auth token available")
            return False
        
        response, error = self.make_request("GET", "/users")
        
        if error:
            self.log_result("Get Users", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            users = response.json()
            if isinstance(users, list) and len(users) > 0:
                self.log_result("Get Users", True, f"Retrieved {len(users)} team members")
                return True
            else:
                self.log_result("Get Users", False, "No users found or invalid response")
                return False
        else:
            self.log_result("Get Users", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_log_call(self):
        """Test POST /api/calls/log to create a call for analysis"""
        print("\n📞 Testing Log Call...")
        
        if not self.auth_token:
            self.log_result("Log Call", False, "No auth token available")
            return False
        
        # First create a lead to associate with the call
        lead_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "company": "Example Corp",
            "phone": "+1-555-0199"
        }
        
        lead_response, lead_error = self.make_request("POST", "/leads", lead_data)
        if lead_error or lead_response.status_code != 200:
            self.log_result("Log Call (Setup)", False, "Failed to create test lead")
            return False
        
        lead_id = lead_response.json()["id"]
        
        # Now log a call
        call_data = {
            "lead_id": lead_id,
            "phone_number": "+1-555-0199",
            "outcome": "connected",
            "duration": 180,
            "notes": "Discussed product features and pricing. Customer interested in demo.",
            "call_sid": f"CA{uuid.uuid4().hex[:32]}"
        }
        
        response, error = self.make_request("POST", "/calls/log", call_data)
        
        if error:
            self.log_result("Log Call", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            call = response.json()
            if "id" in call and call["outcome"] == call_data["outcome"]:
                self.test_call_id = call["id"]
                self.log_result("Log Call", True, f"Call logged with ID: {self.test_call_id}")
                return True
            else:
                self.log_result("Log Call", False, "Invalid call data in response")
                return False
        else:
            self.log_result("Log Call", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_call_analysis(self):
        """Test GET /api/calls/{call_id}/analysis"""
        print("\n📊 Testing Call Analysis...")
        
        if not self.auth_token or not self.test_call_id:
            self.log_result("Call Analysis", False, "No auth token or call ID available")
            return False
        
        response, error = self.make_request("GET", f"/calls/{self.test_call_id}/analysis")
        
        if error:
            self.log_result("Call Analysis", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            result = response.json()
            if "analysis" in result:
                analysis = result["analysis"]
                required_fields = ["sentiment", "talk_ratio", "topics", "coaching_tip"]
                
                if all(field in analysis for field in required_fields):
                    self.log_result("Call Analysis", True, f"Analysis generated with sentiment: {analysis['sentiment']}, coaching tip: {analysis['coaching_tip'][:50]}...")
                    return True
                else:
                    missing_fields = [field for field in required_fields if field not in analysis]
                    self.log_result("Call Analysis", False, f"Missing analysis fields: {missing_fields}")
                    return False
            else:
                self.log_result("Call Analysis", False, "No analysis field in response")
                return False
        else:
            self.log_result("Call Analysis", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def run_all_tests(self):
        """Run all new feature tests in sequence"""
        print("🚀 Starting LeadGen Pro New Features Testing...")
        print(f"🌐 Backend URL: {self.base_url}")
        print("=" * 60)
        
        # Setup test user
        if not self.setup_test_user():
            print("❌ Failed to setup test user. Aborting tests.")
            return self.results
        
        # Priority 1: Calendar Endpoints
        print("\n📅 PRIORITY 1: CALENDAR ENDPOINTS")
        self.test_get_calendar_events()
        self.test_create_calendar_event()
        self.test_delete_calendar_event()
        
        # Priority 2: AI Assistant Endpoint
        print("\n🤖 PRIORITY 2: AI ASSISTANT ENDPOINT")
        self.test_ai_assistant_chat()
        
        # Priority 3: Users Endpoint
        print("\n👥 PRIORITY 3: USERS ENDPOINT")
        self.test_get_users()
        
        # Priority 4: Call Analysis Endpoint
        print("\n📊 PRIORITY 4: CALL ANALYSIS ENDPOINT")
        self.test_log_call()
        self.test_call_analysis()
        
        # Print final results
        print("\n" + "=" * 60)
        print("🏁 NEW FEATURES TESTING COMPLETE")
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
    tester = NewFeaturesTester()
    results = tester.run_all_tests()
    
    # Exit with error code if tests failed
    if results['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)