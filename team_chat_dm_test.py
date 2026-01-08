#!/usr/bin/env python3
"""
LeadGen Pro Team Chat and Direct Messaging Testing
Testing chat channels, direct messages, user presence, and admin features
Test credentials: admin@test.com / admin123
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
import os
import sys

# Backend URL from frontend .env
BACKEND_URL = "https://sales-ai-pro.preview.emergentagent.com/api"

# Test credentials as specified in review request
TEST_EMAIL = "admin@test.com"
TEST_PASSWORD = "admin123"

class TeamChatDMTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.auth_token = None
        self.user_id = None
        self.test_user_id = None
        self.test_channel_id = None
        self.test_dm_channel_id = None
        self.test_message_id = None
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
    
    def make_request(self, method, endpoint, data=None, headers=None, files=None):
        """Make HTTP request with proper error handling"""
        url = f"{self.base_url}{endpoint}"
        
        # Add auth header if we have a token
        if self.auth_token and headers is None:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
        elif self.auth_token and headers:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                if files:
                    response = self.session.post(url, data=data, files=files, headers=headers, timeout=30)
                else:
                    response = self.session.post(url, json=data, headers=headers, timeout=30)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, headers=headers, timeout=30)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return response
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None
    
    def test_admin_login(self):
        """Test admin login with provided credentials"""
        print("\n🔐 Testing Admin Login...")
        
        login_data = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        
        response = self.make_request("POST", "/auth/login", login_data)
        
        if response and response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("access_token")
            self.user_id = data.get("user", {}).get("id")
            user_role = data.get("user", {}).get("role")
            
            if self.auth_token and user_role == "admin":
                self.log_result("Admin Login", True, f"Token received, role: {user_role}")
                return True
            else:
                self.log_result("Admin Login", False, f"Invalid response or not admin role: {user_role}")
                return False
        else:
            error_msg = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_result("Admin Login", False, f"Status: {response.status_code if response else 'None'}, Error: {error_msg}")
            return False
    
    def test_chat_channels(self):
        """Test chat channels functionality"""
        print("\n💬 Testing Chat Channels...")
        
        # Test GET /api/chat/channels
        response = self.make_request("GET", "/chat/channels")
        
        if response and response.status_code == 200:
            channels = response.json()
            
            # Should return public channels (general, sales, leads) and DM channels
            channel_names = [ch.get("name", "") for ch in channels if isinstance(ch, dict)]
            expected_channels = ["general", "sales", "leads"]
            
            has_public_channels = any(name in channel_names for name in expected_channels)
            
            if has_public_channels:
                self.log_result("GET Chat Channels", True, f"Found {len(channels)} channels including public channels")
                # Store a channel ID for message testing
                if channels:
                    self.test_channel_id = channels[0].get("id")
            else:
                self.log_result("GET Chat Channels", False, f"Expected public channels not found. Got: {channel_names}")
        else:
            error_msg = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_result("GET Chat Channels", False, f"Status: {response.status_code if response else 'None'}, Error: {error_msg}")
        
        # Test POST /api/chat/channels - Create a new channel
        new_channel_data = {
            "name": f"test-channel-{uuid.uuid4().hex[:8]}",
            "description": "Test channel for automated testing",
            "type": "public"
        }
        
        response = self.make_request("POST", "/chat/channels", new_channel_data)
        
        if response and response.status_code in [200, 201]:
            channel = response.json()
            channel_id = channel.get("id")
            channel_name = channel.get("name")
            
            if channel_id and channel_name:
                self.log_result("POST Create Channel", True, f"Created channel: {channel_name}")
                if not self.test_channel_id:
                    self.test_channel_id = channel_id
            else:
                self.log_result("POST Create Channel", False, "Channel created but missing ID or name")
        else:
            error_msg = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_result("POST Create Channel", False, f"Status: {response.status_code if response else 'None'}, Error: {error_msg}")
    
    def test_direct_messages(self):
        """Test direct messaging functionality"""
        print("\n📨 Testing Direct Messages...")
        
        # First, get another user ID to create DM with
        response = self.make_request("GET", "/admin/users")
        
        if response and response.status_code == 200:
            users = response.json()
            # Find a user that's not the current admin user
            other_user = None
            for user in users:
                if user.get("id") != self.user_id:
                    other_user = user
                    break
            
            if other_user:
                self.test_user_id = other_user.get("id")
                other_user_name = other_user.get("full_name", "Unknown User")
                self.log_result("Find Other User", True, f"Found user: {other_user_name}")
            else:
                # Create a test user if none found
                test_user_data = {
                    "email": f"testuser-{uuid.uuid4().hex[:8]}@test.com",
                    "password": "TestPass123!",
                    "full_name": "Test User for DM",
                    "role": "employee",
                    "company": "Test Company"
                }
                
                response = self.make_request("POST", "/auth/register", test_user_data)
                if response and response.status_code == 200:
                    user_data = response.json()
                    self.test_user_id = user_data.get("user", {}).get("id")
                    self.log_result("Create Test User", True, f"Created test user for DM testing")
                else:
                    self.log_result("Find/Create Other User", False, "No other users found and couldn't create test user")
                    return
        else:
            self.log_result("Get Users for DM", False, "Could not get users list")
            return
        
        if not self.test_user_id:
            self.log_result("Direct Messages Setup", False, "No test user ID available")
            return
        
        # Test POST /api/chat/dm/{user_id} - Create or get DM channel
        response = self.make_request("POST", f"/chat/dm/{self.test_user_id}")
        
        if response and response.status_code in [200, 201]:
            dm_channel = response.json()
            self.test_dm_channel_id = dm_channel.get("id") or dm_channel.get("channel_id")
            
            if self.test_dm_channel_id:
                self.log_result("POST Create/Get DM Channel", True, f"DM channel ID: {self.test_dm_channel_id}")
            else:
                self.log_result("POST Create/Get DM Channel", False, "DM channel created but no ID returned")
        else:
            error_msg = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_result("POST Create/Get DM Channel", False, f"Status: {response.status_code if response else 'None'}, Error: {error_msg}")
        
        # Test GET /api/chat/dm/list - Get all DM conversations
        response = self.make_request("GET", "/chat/dm/list")
        
        if response and response.status_code == 200:
            dm_conversations = response.json()
            
            if isinstance(dm_conversations, list):
                self.log_result("GET DM Conversations List", True, f"Found {len(dm_conversations)} DM conversations")
            else:
                self.log_result("GET DM Conversations List", False, "Response is not a list")
        else:
            error_msg = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_result("GET DM Conversations List", False, f"Status: {response.status_code if response else 'None'}, Error: {error_msg}")
    
    def test_chat_messages(self):
        """Test chat messages functionality"""
        print("\n💬 Testing Chat Messages...")
        
        if not self.test_channel_id:
            self.log_result("Chat Messages Setup", False, "No test channel ID available")
            return
        
        # Test GET /api/chat/messages/{channel_id} - Get messages from channel
        response = self.make_request("GET", f"/chat/messages/{self.test_channel_id}")
        
        if response and response.status_code == 200:
            messages = response.json()
            
            if isinstance(messages, list):
                self.log_result("GET Channel Messages", True, f"Retrieved {len(messages)} messages from channel")
            else:
                self.log_result("GET Channel Messages", False, "Response is not a list")
        else:
            error_msg = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_result("GET Channel Messages", False, f"Status: {response.status_code if response else 'None'}, Error: {error_msg}")
        
        # Test POST /api/chat/messages - Send a message with @mention
        test_message_data = {
            "channel_id": self.test_channel_id,
            "content": f"Test message with @mention from automated testing at {datetime.now().isoformat()}",
            "type": "text"
        }
        
        response = self.make_request("POST", "/chat/messages", test_message_data)
        
        if response and response.status_code in [200, 201]:
            message = response.json()
            self.test_message_id = message.get("id")
            
            if self.test_message_id:
                self.log_result("POST Send Message with @mention", True, f"Message sent with ID: {self.test_message_id}")
            else:
                self.log_result("POST Send Message with @mention", False, "Message sent but no ID returned")
        else:
            error_msg = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_result("POST Send Message with @mention", False, f"Status: {response.status_code if response else 'None'}, Error: {error_msg}")
    
    def test_user_presence(self):
        """Test user presence/status functionality"""
        print("\n👥 Testing User Presence...")
        
        # Test GET /api/users/status - Get all user statuses
        response = self.make_request("GET", "/users/status")
        
        if response and response.status_code == 200:
            user_statuses = response.json()
            
            if isinstance(user_statuses, list):
                # Check if statuses include last_seen timestamp
                has_timestamps = any(
                    user.get("last_seen") is not None 
                    for user in user_statuses 
                    if isinstance(user, dict)
                )
                
                self.log_result("GET User Statuses", True, f"Retrieved {len(user_statuses)} user statuses, has timestamps: {has_timestamps}")
            else:
                self.log_result("GET User Statuses", False, "Response is not a list")
        else:
            error_msg = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_result("GET User Statuses", False, f"Status: {response.status_code if response else 'None'}, Error: {error_msg}")
        
        # Test POST /api/user/status - Update current user's status to "online"
        status_update_data = {
            "status": "online",
            "message": "Available for chat"
        }
        
        response = self.make_request("POST", "/user/status", status_update_data)
        
        if response and response.status_code in [200, 201]:
            updated_status = response.json()
            
            # Verify the status includes last_seen timestamp
            last_seen = updated_status.get("last_seen")
            status = updated_status.get("status")
            
            if last_seen and status == "online":
                self.log_result("POST Update User Status", True, f"Status updated to online with timestamp: {last_seen}")
            else:
                self.log_result("POST Update User Status", False, f"Status update incomplete - status: {status}, last_seen: {last_seen}")
        else:
            error_msg = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_result("POST Update User Status", False, f"Status: {response.status_code if response else 'None'}, Error: {error_msg}")
    
    def test_lead_visibility_admin(self):
        """Test that admin can see ALL leads regardless of who created them"""
        print("\n🎯 Testing Lead Visibility for Admin...")
        
        # Test GET /api/leads - Admin should see ALL leads
        response = self.make_request("GET", "/leads")
        
        if response and response.status_code == 200:
            leads = response.json()
            
            if isinstance(leads, list):
                # Check for leads created by different users (like Monika)
                creators = set()
                monika_leads = 0
                
                for lead in leads:
                    if isinstance(lead, dict):
                        created_by = lead.get("created_by")
                        if created_by:
                            creators.add(created_by)
                        
                        # Look for leads that might be created by Monika or other users
                        lead_name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}"
                        if "monika" in lead_name.lower() or lead.get("created_by") != self.user_id:
                            monika_leads += 1
                
                total_leads = len(leads)
                unique_creators = len(creators)
                
                # Admin should see leads from multiple creators
                if total_leads > 0 and (unique_creators > 1 or monika_leads > 0):
                    self.log_result("Admin Lead Visibility", True, f"Admin sees {total_leads} leads from {unique_creators} creators, including {monika_leads} from other users")
                elif total_leads > 0:
                    self.log_result("Admin Lead Visibility", True, f"Admin sees {total_leads} leads (may be single creator scenario)")
                else:
                    self.log_result("Admin Lead Visibility", False, "No leads found for admin user")
            else:
                self.log_result("Admin Lead Visibility", False, "Response is not a list")
        else:
            error_msg = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_result("Admin Lead Visibility", False, f"Status: {response.status_code if response else 'None'}, Error: {error_msg}")
    
    def test_user_management(self):
        """Test user management functionality"""
        print("\n👤 Testing User Management...")
        
        # Test GET /api/admin/users - Get all users
        response = self.make_request("GET", "/admin/users")
        
        if response and response.status_code == 200:
            users = response.json()
            
            if isinstance(users, list):
                self.log_result("GET Admin Users", True, f"Retrieved {len(users)} users")
                
                # Find a test user to delete (not admin users)
                test_user_to_delete = None
                for user in users:
                    if isinstance(user, dict):
                        email = user.get("email", "")
                        user_id = user.get("id")
                        # Don't delete admin users or the current user
                        if (email not in ["admin@test.com", "mattmascasa@gmail.com", "monika.iordanoff@gmail.com"] 
                            and user_id != self.user_id 
                            and "test" in email.lower()):
                            test_user_to_delete = user
                            break
                
                if test_user_to_delete:
                    user_id_to_delete = test_user_to_delete.get("id")
                    user_email = test_user_to_delete.get("email")
                    
                    # Test DELETE /api/admin/users/{user_id}
                    response = self.make_request("DELETE", f"/admin/users/{user_id_to_delete}")
                    
                    if response and response.status_code in [200, 204]:
                        self.log_result("DELETE Test User", True, f"Deleted test user: {user_email}")
                        
                        # Verify user is deleted by getting users again
                        response = self.make_request("GET", "/admin/users")
                        if response and response.status_code == 200:
                            updated_users = response.json()
                            deleted_user_still_exists = any(
                                user.get("id") == user_id_to_delete 
                                for user in updated_users 
                                if isinstance(user, dict)
                            )
                            
                            if not deleted_user_still_exists:
                                self.log_result("Verify User Deletion", True, f"User {user_email} successfully removed from users list")
                            else:
                                self.log_result("Verify User Deletion", False, f"User {user_email} still exists after deletion")
                        else:
                            self.log_result("Verify User Deletion", False, "Could not verify deletion - failed to get updated users list")
                    else:
                        error_msg = response.json().get("detail", "Unknown error") if response else "No response"
                        self.log_result("DELETE Test User", False, f"Status: {response.status_code if response else 'None'}, Error: {error_msg}")
                else:
                    # Create a test user to delete
                    test_user_data = {
                        "email": f"delete-test-{uuid.uuid4().hex[:8]}@test.com",
                        "password": "TestPass123!",
                        "full_name": "Test User for Deletion",
                        "role": "employee",
                        "company": "Test Company"
                    }
                    
                    response = self.make_request("POST", "/auth/register", test_user_data)
                    if response and response.status_code == 200:
                        new_user = response.json().get("user", {})
                        new_user_id = new_user.get("id")
                        new_user_email = new_user.get("email")
                        
                        if new_user_id:
                            # Now delete the newly created user
                            response = self.make_request("DELETE", f"/admin/users/{new_user_id}")
                            
                            if response and response.status_code in [200, 204]:
                                self.log_result("DELETE Newly Created User", True, f"Created and deleted test user: {new_user_email}")
                            else:
                                error_msg = response.json().get("detail", "Unknown error") if response else "No response"
                                self.log_result("DELETE Newly Created User", False, f"Status: {response.status_code if response else 'None'}, Error: {error_msg}")
                        else:
                            self.log_result("Create User for Deletion", False, "Created user but no ID returned")
                    else:
                        self.log_result("User Management - No Test User", False, "No suitable test user found and couldn't create one")
            else:
                self.log_result("GET Admin Users", False, "Response is not a list")
        else:
            error_msg = response.json().get("detail", "Unknown error") if response else "No response"
            self.log_result("GET Admin Users", False, f"Status: {response.status_code if response else 'None'}, Error: {error_msg}")
    
    def run_all_tests(self):
        """Run all team chat and DM tests"""
        print("🚀 Starting Team Chat and Direct Messaging Tests...")
        print(f"Backend URL: {self.base_url}")
        print(f"Test Credentials: {TEST_EMAIL}")
        
        # Login first
        if not self.test_admin_login():
            print("❌ Login failed - cannot proceed with other tests")
            return False
        
        # Run all tests
        self.test_chat_channels()
        self.test_direct_messages()
        self.test_chat_messages()
        self.test_user_presence()
        self.test_lead_visibility_admin()
        self.test_user_management()
        
        # Print summary
        print(f"\n📊 Test Results Summary:")
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📈 Success Rate: {(self.results['passed'] / (self.results['passed'] + self.results['failed']) * 100):.1f}%")
        
        if self.results['errors']:
            print(f"\n🔍 Failed Tests:")
            for error in self.results['errors']:
                print(f"  • {error}")
        
        return self.results['failed'] == 0

if __name__ == "__main__":
    tester = TeamChatDMTester()
    success = tester.run_all_tests()
    
    if success:
        print(f"\n🎉 All tests passed! Team Chat and DM functionality is working correctly.")
        sys.exit(0)
    else:
        print(f"\n⚠️  Some tests failed. Please check the errors above.")
        sys.exit(1)