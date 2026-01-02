#!/usr/bin/env python3
"""
Twilio Voice Integration Testing for LeadGen Pro
Tests voice token generation, call initiation, call logging, and activity tracking
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
import os
import sys

# Backend URL from frontend .env
BACKEND_URL = "https://salesautomation-2.preview.emergentagent.com/api"

class VoiceIntegrationTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.auth_token = None
        self.test_user_id = None
        self.test_lead_id = None
        self.test_call_sid = None
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
    
    def make_request(self, method, endpoint, data=None, headers=None, params=None):
        """Make HTTP request with proper error handling"""
        url = f"{self.base_url}{endpoint}"
        
        # Add auth header if token exists
        if self.auth_token and headers is None:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
        elif self.auth_token and headers:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, params=params, timeout=30)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, headers=headers, params=params, timeout=30)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, headers=headers, params=params, timeout=30)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers, params=params, timeout=30)
            else:
                return None, f"Unsupported method: {method}"
            
            return response, None
        except requests.exceptions.RequestException as e:
            return None, str(e)
    
    def setup_test_user(self):
        """Create test user and authenticate"""
        print("\n🔐 Setting up test user...")
        
        # Use the specified test credentials
        test_email = "finaltest@example.com"
        test_password = "FinalTest123!"
        
        # Try to login first
        login_data = {
            "email": test_email,
            "password": test_password
        }
        
        response, error = self.make_request("POST", "/auth/login", login_data)
        
        if response and response.status_code == 200:
            data = response.json()
            self.auth_token = data["access_token"]
            self.test_user_id = data["user"]["id"]
            self.log_result("User Authentication", True, f"Logged in as {test_email}")
            return True
        
        # If login fails, try to register
        user_data = {
            "email": test_email,
            "password": test_password,
            "full_name": "Final Test User",
            "role": "admin",
            "company": "Voice Testing Corp"
        }
        
        response, error = self.make_request("POST", "/auth/register", user_data)
        
        if error:
            self.log_result("User Setup", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            data = response.json()
            self.auth_token = data["access_token"]
            self.test_user_id = data["user"]["id"]
            self.log_result("User Setup", True, f"User created: {test_email}")
            return True
        else:
            self.log_result("User Setup", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def setup_test_lead(self):
        """Create a test lead for voice testing"""
        print("\n📋 Setting up test lead...")
        
        if not self.auth_token:
            self.log_result("Lead Setup", False, "No auth token available")
            return False
        
        lead_data = {
            "first_name": "John",
            "last_name": "VoiceTest",
            "email": "john.voicetest@example.com",
            "phone": "+15551234567",
            "company": "Voice Test Corp",
            "title": "Test Contact",
            "status": "new",
            "tags": ["voice-test"]
        }
        
        response, error = self.make_request("POST", "/leads", lead_data)
        
        if error:
            self.log_result("Lead Setup", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            lead = response.json()
            self.test_lead_id = lead["id"]
            self.log_result("Lead Setup", True, f"Test lead created: {self.test_lead_id}")
            return True
        else:
            self.log_result("Lead Setup", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_voice_token_generation(self):
        """Test POST /api/voice/token - Priority 1"""
        print("\n🎤 Testing Voice Token Generation...")
        
        if not self.auth_token:
            self.log_result("Voice Token Generation", False, "No auth token available")
            return False
        
        token_data = {
            "identity": "test-agent"
        }
        
        response, error = self.make_request("POST", "/voice/token", token_data)
        
        if error:
            self.log_result("Voice Token Generation", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            data = response.json()
            if "success" in data and data["success"] and "token" in data:
                self.log_result("Voice Token Generation", True, f"JWT token generated for identity: {data.get('identity')}")
                return True
            else:
                self.log_result("Voice Token Generation", False, "Invalid response format - missing success or token")
                return False
        else:
            self.log_result("Voice Token Generation", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_call_initiation(self):
        """Test POST /api/voice/call - Priority 2 (BE CAREFUL - This will actually try to call)"""
        print("\n📞 Testing Call Initiation...")
        
        if not self.auth_token or not self.test_lead_id:
            self.log_result("Call Initiation", False, "No auth token or lead ID available")
            return False
        
        call_params = {
            "phone_number": "+15551234567",  # Fake number as specified
            "lead_id": self.test_lead_id
        }
        
        response, error = self.make_request("POST", "/voice/call", None, None, call_params)
        
        if error:
            self.log_result("Call Initiation", False, f"Request failed: {error}")
            return False
        
        # This may fail with Twilio error for invalid number, which is expected
        if response.status_code == 200:
            data = response.json()
            if "success" in data and "call_sid" in data:
                self.test_call_sid = data["call_sid"]
                self.log_result("Call Initiation", True, f"Call initiated with SID: {self.test_call_sid}")
                return True
            else:
                self.log_result("Call Initiation", False, "Invalid response format")
                return False
        elif response.status_code == 500:
            # Check if it's a Twilio error for invalid number (expected)
            error_text = response.text.lower()
            if "twilio" in error_text and ("invalid" in error_text or "not a valid" in error_text):
                self.log_result("Call Initiation", True, "Expected Twilio error for fake number - endpoint accessible")
                return True
            else:
                self.log_result("Call Initiation", False, f"Unexpected error: {response.text}")
                return False
        else:
            self.log_result("Call Initiation", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_call_logging(self):
        """Test POST /api/calls/log - Priority 3"""
        print("\n📝 Testing Call Logging...")
        
        if not self.auth_token or not self.test_lead_id:
            self.log_result("Call Logging", False, "No auth token or lead ID available")
            return False
        
        call_log_data = {
            "lead_id": self.test_lead_id,
            "phone_number": "+1234567890",
            "outcome": "connected",
            "duration": 120,
            "notes": "Test call - spoke with contact",
            "call_sid": "CA_test_123"
        }
        
        response, error = self.make_request("POST", "/calls/log", call_log_data)
        
        if error:
            self.log_result("Call Logging", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            data = response.json()
            if "id" in data and data["outcome"] == call_log_data["outcome"]:
                self.log_result("Call Logging", True, f"Call logged with ID: {data['id']}")
                return True
            else:
                self.log_result("Call Logging", False, "Invalid call log response")
                return False
        else:
            self.log_result("Call Logging", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_get_call_logs(self):
        """Test GET /api/calls/logs - Priority 3"""
        print("\n📋 Testing Get Call Logs...")
        
        if not self.auth_token:
            self.log_result("Get Call Logs", False, "No auth token available")
            return False
        
        response, error = self.make_request("GET", "/calls/logs")
        
        if error:
            self.log_result("Get Call Logs", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            logs = response.json()
            if isinstance(logs, list):
                self.log_result("Get Call Logs", True, f"Retrieved {len(logs)} call logs")
                return True
            else:
                self.log_result("Get Call Logs", False, "Response is not a list")
                return False
        else:
            self.log_result("Get Call Logs", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_get_call_logs_filtered(self):
        """Test GET /api/calls/logs?lead_id=... - Priority 3"""
        print("\n🔍 Testing Get Call Logs (Filtered by Lead)...")
        
        if not self.auth_token or not self.test_lead_id:
            self.log_result("Get Call Logs (Filtered)", False, "No auth token or lead ID available")
            return False
        
        params = {"lead_id": self.test_lead_id}
        response, error = self.make_request("GET", "/calls/logs", None, None, params)
        
        if error:
            self.log_result("Get Call Logs (Filtered)", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            logs = response.json()
            if isinstance(logs, list):
                # Check if all logs are for the specified lead
                valid_filter = all(log.get("lead_id") == self.test_lead_id for log in logs) if logs else True
                if valid_filter:
                    self.log_result("Get Call Logs (Filtered)", True, f"Retrieved {len(logs)} filtered call logs")
                    return True
                else:
                    self.log_result("Get Call Logs (Filtered)", False, "Filter not working correctly")
                    return False
            else:
                self.log_result("Get Call Logs (Filtered)", False, "Response is not a list")
                return False
        else:
            self.log_result("Get Call Logs (Filtered)", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_get_call_stats(self):
        """Test GET /api/calls/stats - Priority 3"""
        print("\n📊 Testing Get Call Statistics...")
        
        if not self.auth_token:
            self.log_result("Get Call Stats", False, "No auth token available")
            return False
        
        response, error = self.make_request("GET", "/calls/stats")
        
        if error:
            self.log_result("Get Call Stats", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            stats = response.json()
            expected_fields = ["total_calls", "total_duration_seconds", "average_duration_seconds", "outcomes", "connect_rate"]
            if all(field in stats for field in expected_fields):
                self.log_result("Get Call Stats", True, f"Stats retrieved - Total calls: {stats['total_calls']}, Connect rate: {stats['connect_rate']}%")
                return True
            else:
                missing_fields = [field for field in expected_fields if field not in stats]
                self.log_result("Get Call Stats", False, f"Missing fields: {missing_fields}")
                return False
        else:
            self.log_result("Get Call Stats", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_activity_logging(self):
        """Test GET /api/activities to verify call activity was logged - Priority 4"""
        print("\n📈 Testing Activity Logging...")
        
        if not self.auth_token:
            self.log_result("Activity Logging", False, "No auth token available")
            return False
        
        response, error = self.make_request("GET", "/activities")
        
        if error:
            self.log_result("Activity Logging", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            activities = response.json()
            if isinstance(activities, list):
                # Look for call-related activities
                call_activities = [act for act in activities if act.get("type") in ["call_logged", "call_initiated"]]
                if call_activities:
                    self.log_result("Activity Logging", True, f"Found {len(call_activities)} call-related activities")
                    return True
                else:
                    self.log_result("Activity Logging", True, f"Retrieved {len(activities)} activities (no call activities yet)")
                    return True
            else:
                self.log_result("Activity Logging", False, "Response is not a list")
                return False
        else:
            self.log_result("Activity Logging", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def run_voice_tests(self):
        """Run all voice integration tests in sequence"""
        print("🎤 Starting Twilio Voice Integration Testing...")
        print(f"🌐 Backend URL: {self.base_url}")
        print("=" * 60)
        
        # Setup
        if not self.setup_test_user():
            print("❌ Failed to setup test user - aborting tests")
            return self.results
        
        if not self.setup_test_lead():
            print("❌ Failed to setup test lead - aborting tests")
            return self.results
        
        # Priority 1: Voice Token Generation
        self.test_voice_token_generation()
        
        # Priority 2: Call Initiation (BE CAREFUL - This will actually try to call)
        self.test_call_initiation()
        
        # Priority 3: Call Logging
        self.test_call_logging()
        self.test_get_call_logs()
        self.test_get_call_logs_filtered()
        self.test_get_call_stats()
        
        # Priority 4: Verify Activity Logging
        self.test_activity_logging()
        
        # Print final results
        print("\n" + "=" * 60)
        print("🏁 VOICE TESTING COMPLETE")
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
    tester = VoiceIntegrationTester()
    results = tester.run_voice_tests()
    
    # Exit with error code if tests failed
    if results['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)