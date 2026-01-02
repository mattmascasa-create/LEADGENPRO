#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for LeadGen Pro
Tests all backend endpoints with realistic data
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
import os
import sys

# Backend URL from frontend .env
BACKEND_URL = "https://salesautomation-2.preview.emergentagent.com/api"

class LeadGenProTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.auth_token = None
        self.test_user_id = None
        self.test_lead_id = None
        self.test_task_id = None
        self.test_channel_id = None
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
    
    def test_user_registration(self):
        """Test user registration endpoint"""
        print("\n🔐 Testing User Registration...")
        
        # Generate unique email for testing
        test_email = f"testuser_{uuid.uuid4().hex[:8]}@leadgenpro.com"
        
        user_data = {
            "email": test_email,
            "password": "TestPass123!",
            "full_name": "Test User Pro",
            "role": "admin",
            "company": "LeadGen Testing Corp"
        }
        
        response, error = self.make_request("POST", "/auth/register", user_data)
        
        if error:
            self.log_result("User Registration", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data and "user" in data:
                self.auth_token = data["access_token"]
                self.test_user_id = data["user"]["id"]
                self.log_result("User Registration", True, f"User created with ID: {self.test_user_id}")
                return True
            else:
                self.log_result("User Registration", False, "Missing token or user in response")
                return False
        else:
            self.log_result("User Registration", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_user_login(self):
        """Test user login endpoint"""
        print("\n🔑 Testing User Login...")
        
        # First register a user for login test
        test_email = f"logintest_{uuid.uuid4().hex[:8]}@leadgenpro.com"
        
        # Register user
        user_data = {
            "email": test_email,
            "password": "LoginTest123!",
            "full_name": "Login Test User",
            "role": "admin"
        }
        
        reg_response, reg_error = self.make_request("POST", "/auth/register", user_data)
        if reg_error or reg_response.status_code != 200:
            self.log_result("User Login (Setup)", False, "Failed to create test user for login")
            return False
        
        # Now test login
        login_data = {
            "email": test_email,
            "password": "LoginTest123!"
        }
        
        response, error = self.make_request("POST", "/auth/login", login_data)
        
        if error:
            self.log_result("User Login", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data and "user" in data:
                self.log_result("User Login", True, "Login successful with token")
                return True
            else:
                self.log_result("User Login", False, "Missing token or user in response")
                return False
        else:
            self.log_result("User Login", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_get_current_user(self):
        """Test getting current user info"""
        print("\n👤 Testing Get Current User...")
        
        if not self.auth_token:
            self.log_result("Get Current User", False, "No auth token available")
            return False
        
        response, error = self.make_request("GET", "/auth/me")
        
        if error:
            self.log_result("Get Current User", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            user_data = response.json()
            if "id" in user_data and "email" in user_data:
                self.log_result("Get Current User", True, f"User info retrieved: {user_data['email']}")
                return True
            else:
                self.log_result("Get Current User", False, "Invalid user data structure")
                return False
        else:
            self.log_result("Get Current User", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_create_lead(self):
        """Test creating a new lead"""
        print("\n📋 Testing Create Lead...")
        
        if not self.auth_token:
            self.log_result("Create Lead", False, "No auth token available")
            return False
        
        lead_data = {
            "first_name": "Sarah",
            "last_name": "Johnson",
            "email": "sarah.johnson@techcorp.com",
            "phone": "+1-555-0123",
            "company": "TechCorp Solutions",
            "title": "VP of Sales",
            "status": "new",
            "tags": ["enterprise", "high-priority"]
        }
        
        response, error = self.make_request("POST", "/leads", lead_data)
        
        if error:
            self.log_result("Create Lead", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            lead = response.json()
            if "id" in lead and lead["email"] == lead_data["email"]:
                self.test_lead_id = lead["id"]
                self.log_result("Create Lead", True, f"Lead created with ID: {self.test_lead_id}")
                return True
            else:
                self.log_result("Create Lead", False, "Invalid lead data in response")
                return False
        else:
            self.log_result("Create Lead", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_get_leads(self):
        """Test getting all leads"""
        print("\n📊 Testing Get All Leads...")
        
        if not self.auth_token:
            self.log_result("Get All Leads", False, "No auth token available")
            return False
        
        response, error = self.make_request("GET", "/leads")
        
        if error:
            self.log_result("Get All Leads", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            leads = response.json()
            if isinstance(leads, list):
                self.log_result("Get All Leads", True, f"Retrieved {len(leads)} leads")
                return True
            else:
                self.log_result("Get All Leads", False, "Response is not a list")
                return False
        else:
            self.log_result("Get All Leads", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_update_lead_stage(self):
        """Test updating lead stage (critical for Kanban)"""
        print("\n🔄 Testing Update Lead Stage...")
        
        if not self.auth_token or not self.test_lead_id:
            self.log_result("Update Lead Stage", False, "No auth token or lead ID available")
            return False
        
        # Test moving from prospecting to qualified
        response, error = self.make_request("POST", f"/leads/{self.test_lead_id}/stage?stage=qualified")
        
        if error:
            self.log_result("Update Lead Stage", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            result = response.json()
            if "message" in result:
                self.log_result("Update Lead Stage", True, "Stage updated to qualified")
                
                # Test moving to proposal stage
                response2, error2 = self.make_request("POST", f"/leads/{self.test_lead_id}/stage?stage=proposal")
                if not error2 and response2.status_code == 200:
                    self.log_result("Update Lead Stage (Proposal)", True, "Stage updated to proposal")
                    return True
                else:
                    self.log_result("Update Lead Stage (Proposal)", False, f"Failed to update to proposal: {error2 or response2.text}")
                    return False
            else:
                self.log_result("Update Lead Stage", False, "Invalid response format")
                return False
        else:
            self.log_result("Update Lead Stage", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_delete_lead(self):
        """Test deleting a lead"""
        print("\n🗑️ Testing Delete Lead...")
        
        if not self.auth_token:
            self.log_result("Delete Lead", False, "No auth token available")
            return False
        
        # Create a lead specifically for deletion
        lead_data = {
            "first_name": "Delete",
            "last_name": "TestLead",
            "email": "delete.test@example.com",
            "company": "Test Company",
            "status": "new"
        }
        
        create_response, create_error = self.make_request("POST", "/leads", lead_data)
        if create_error or create_response.status_code != 200:
            self.log_result("Delete Lead (Setup)", False, "Failed to create lead for deletion test")
            return False
        
        delete_lead_id = create_response.json()["id"]
        
        # Now delete the lead
        response, error = self.make_request("DELETE", f"/leads/{delete_lead_id}")
        
        if error:
            self.log_result("Delete Lead", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            result = response.json()
            if "message" in result:
                self.log_result("Delete Lead", True, "Lead deleted successfully")
                return True
            else:
                self.log_result("Delete Lead", False, "Invalid response format")
                return False
        else:
            self.log_result("Delete Lead", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_create_task(self):
        """Test creating a task"""
        print("\n📝 Testing Create Task...")
        
        if not self.auth_token or not self.test_user_id:
            self.log_result("Create Task", False, "No auth token or user ID available")
            return False
        
        task_data = {
            "title": "Follow up with Sarah Johnson",
            "description": "Schedule demo call and send pricing information",
            "type": "call",
            "assigned_to": self.test_user_id,
            "due_date": (datetime.now() + timedelta(days=2)).isoformat(),
            "priority": "high"
        }
        
        if self.test_lead_id:
            task_data["lead_id"] = self.test_lead_id
        
        response, error = self.make_request("POST", "/tasks", task_data)
        
        if error:
            self.log_result("Create Task", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            task = response.json()
            if "id" in task and task["title"] == task_data["title"]:
                self.test_task_id = task["id"]
                self.log_result("Create Task", True, f"Task created with ID: {self.test_task_id}")
                return True
            else:
                self.log_result("Create Task", False, "Invalid task data in response")
                return False
        else:
            self.log_result("Create Task", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_get_tasks(self):
        """Test getting all tasks"""
        print("\n📋 Testing Get All Tasks...")
        
        if not self.auth_token:
            self.log_result("Get All Tasks", False, "No auth token available")
            return False
        
        response, error = self.make_request("GET", "/tasks")
        
        if error:
            self.log_result("Get All Tasks", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            tasks = response.json()
            if isinstance(tasks, list):
                self.log_result("Get All Tasks", True, f"Retrieved {len(tasks)} tasks")
                return True
            else:
                self.log_result("Get All Tasks", False, "Response is not a list")
                return False
        else:
            self.log_result("Get All Tasks", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_complete_task(self):
        """Test completing a task"""
        print("\n✅ Testing Complete Task...")
        
        if not self.auth_token or not self.test_task_id:
            self.log_result("Complete Task", False, "No auth token or task ID available")
            return False
        
        response, error = self.make_request("PUT", f"/tasks/{self.test_task_id}/complete")
        
        if error:
            self.log_result("Complete Task", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            result = response.json()
            if "message" in result:
                self.log_result("Complete Task", True, "Task completed successfully")
                return True
            else:
                self.log_result("Complete Task", False, "Invalid response format")
                return False
        else:
            self.log_result("Complete Task", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_get_chat_channels(self):
        """Test getting chat channels"""
        print("\n💬 Testing Get Chat Channels...")
        
        if not self.auth_token:
            self.log_result("Get Chat Channels", False, "No auth token available")
            return False
        
        response, error = self.make_request("GET", "/chat/channels")
        
        if error:
            self.log_result("Get Chat Channels", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            channels = response.json()
            if isinstance(channels, list) and len(channels) > 0:
                self.test_channel_id = channels[0]["id"]
                self.log_result("Get Chat Channels", True, f"Retrieved {len(channels)} channels")
                return True
            else:
                self.log_result("Get Chat Channels", False, "No channels found or invalid response")
                return False
        else:
            self.log_result("Get Chat Channels", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_send_chat_message(self):
        """Test sending a chat message"""
        print("\n📨 Testing Send Chat Message...")
        
        if not self.auth_token or not self.test_channel_id:
            self.log_result("Send Chat Message", False, "No auth token or channel ID available")
            return False
        
        message_data = {
            "channel_id": self.test_channel_id,
            "content": "Hello team! This is a test message from the API testing suite.",
            "type": "text"
        }
        
        response, error = self.make_request("POST", "/chat/messages", message_data)
        
        if error:
            self.log_result("Send Chat Message", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            message = response.json()
            if "id" in message and message["content"] == message_data["content"]:
                self.log_result("Send Chat Message", True, f"Message sent with ID: {message['id']}")
                return True
            else:
                self.log_result("Send Chat Message", False, "Invalid message data in response")
                return False
        else:
            self.log_result("Send Chat Message", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_get_chat_messages(self):
        """Test getting chat messages"""
        print("\n📬 Testing Get Chat Messages...")
        
        if not self.auth_token or not self.test_channel_id:
            self.log_result("Get Chat Messages", False, "No auth token or channel ID available")
            return False
        
        response, error = self.make_request("GET", f"/chat/messages/{self.test_channel_id}")
        
        if error:
            self.log_result("Get Chat Messages", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            messages = response.json()
            if isinstance(messages, list):
                self.log_result("Get Chat Messages", True, f"Retrieved {len(messages)} messages")
                return True
            else:
                self.log_result("Get Chat Messages", False, "Response is not a list")
                return False
        else:
            self.log_result("Get Chat Messages", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def run_all_tests(self):
        """Run all backend tests in sequence"""
        print("🚀 Starting LeadGen Pro Backend API Testing...")
        print(f"🌐 Backend URL: {self.base_url}")
        print("=" * 60)
        
        # Priority 1: Authentication Flow
        self.test_user_registration()
        self.test_user_login()
        self.test_get_current_user()
        
        # Priority 2: Lead Management & Pipeline
        self.test_create_lead()
        self.test_get_leads()
        self.test_update_lead_stage()
        self.test_delete_lead()
        
        # Priority 3: Tasks Management
        self.test_create_task()
        self.test_get_tasks()
        self.test_complete_task()
        
        # Priority 4: Team Chat
        self.test_get_chat_channels()
        self.test_send_chat_message()
        self.test_get_chat_messages()
        
        # Print final results
        print("\n" + "=" * 60)
        print("🏁 TESTING COMPLETE")
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
    tester = LeadGenProTester()
    results = tester.run_all_tests()
    
    # Exit with error code if tests failed
    if results['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)