#!/usr/bin/env python3
"""
LeadGen Pro Pre-Deployment Testing
Testing critical features before deployment with admin@test.com credentials
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
import os
import sys
import io
import csv

# Backend URL from frontend .env
BACKEND_URL = "https://sales-ai-pro.preview.emergentagent.com/api"

# Test credentials as specified in review request
TEST_EMAIL = "admin@test.com"
TEST_PASSWORD = "admin123"

class LeadGenProDeploymentTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.auth_token = None
        self.user_id = None
        self.test_lead_id = None
        self.test_appointment_id = None
        self.test_meeting_type_id = None
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
    
    def make_request(self, method, endpoint, data=None, headers=None, files=None):
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
                if files:
                    response = self.session.post(url, data=data, files=files, headers=headers, timeout=30)
                else:
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
    
    # ==================== CRITICAL FEATURE TESTS ====================
    
    def test_admin_login(self):
        """Test login with admin@test.com credentials"""
        print("\n🔐 Testing Admin Login...")
        
        login_data = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        
        response, error = self.make_request("POST", "/auth/login", login_data)
        
        if error:
            self.log_result("Admin Login", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data and "user" in data:
                self.auth_token = data["access_token"]
                self.user_id = data["user"]["id"]
                self.log_result("Admin Login", True, f"Login successful: {data['user']['email']}")
                return True
            else:
                self.log_result("Admin Login", False, "Missing token or user in response")
                return False
        else:
            self.log_result("Admin Login", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_get_current_user(self):
        """Test GET /api/auth/me - Get current user"""
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
    
    def test_csv_lead_import(self):
        """Test POST /api/leads/bulk-import - CSV Lead Import (PRIORITY)"""
        print("\n📊 Testing CSV Lead Import (PRIORITY)...")
        
        if not self.auth_token:
            self.log_result("CSV Lead Import", False, "No auth token available")
            return False
        
        # Create test CSV data
        csv_data = [
            ["first_name", "last_name", "email", "phone", "company", "title"],
            ["Michael", "Chen", "michael.chen@techstartup.com", "+1-555-0101", "TechStartup Inc", "CTO"],
            ["Sarah", "Williams", "sarah.williams@salesforce.com", "+1-555-0102", "Salesforce", "VP Sales"],
            ["David", "Rodriguez", "david.rodriguez@microsoft.com", "+1-555-0103", "Microsoft", "Product Manager"]
        ]
        
        # Convert to CSV string
        csv_string = io.StringIO()
        writer = csv.writer(csv_string)
        writer.writerows(csv_data)
        csv_content = csv_string.getvalue()
        
        # Create file-like object
        files = {
            'file': ('test_leads.csv', csv_content, 'text/csv')
        }
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        response, error = self.make_request("POST", "/leads/bulk-import", files=files, headers=headers)
        
        if error:
            self.log_result("CSV Lead Import", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            result = response.json()
            if "success" in result and result["success"] >= 3:
                self.log_result("CSV Lead Import", True, f"Successfully imported {result['success']} leads, {result.get('failed', 0)} failed")
                return True
            else:
                self.log_result("CSV Lead Import", False, f"Import failed or insufficient leads imported: {result}")
                return False
        else:
            self.log_result("CSV Lead Import", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_leads_management(self):
        """Test leads management endpoints"""
        print("\n📋 Testing Leads Management...")
        
        if not self.auth_token:
            self.log_result("Leads Management", False, "No auth token available")
            return False
        
        # Test GET /api/leads
        response, error = self.make_request("GET", "/leads")
        
        if error:
            self.log_result("Leads Management - Get All", False, f"Request failed: {error}")
            return False
        
        if response.status_code != 200:
            self.log_result("Leads Management - Get All", False, f"Status {response.status_code}: {response.text}")
            return False
        
        leads = response.json()
        if not isinstance(leads, list):
            self.log_result("Leads Management - Get All", False, "Response is not a list")
            return False
        
        self.log_result("Leads Management - Get All", True, f"Retrieved {len(leads)} leads")
        
        # Test POST /api/leads - Create new lead
        lead_data = {
            "first_name": "Emma",
            "last_name": "Thompson",
            "email": "emma.thompson@enterprise.com",
            "phone": "+1-555-0199",
            "company": "Enterprise Solutions",
            "title": "Director of Operations",
            "status": "new",
            "tags": ["enterprise", "high-value"]
        }
        
        response, error = self.make_request("POST", "/leads", lead_data)
        
        if error:
            self.log_result("Leads Management - Create", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            lead = response.json()
            if "id" in lead:
                self.test_lead_id = lead["id"]
                self.log_result("Leads Management - Create", True, f"Lead created with ID: {self.test_lead_id}")
                
                # Test PUT /api/leads/{id} - Update lead
                update_data = {
                    "first_name": "Emma",
                    "last_name": "Thompson-Smith",
                    "email": "emma.thompson@enterprise.com",
                    "phone": "+1-555-0199",
                    "company": "Enterprise Solutions Corp",
                    "title": "VP of Operations",
                    "status": "qualified",
                    "tags": ["enterprise", "high-value", "updated"]
                }
                
                response, error = self.make_request("PUT", f"/leads/{self.test_lead_id}", update_data)
                
                if error:
                    self.log_result("Leads Management - Update", False, f"Request failed: {error}")
                    return False
                
                if response.status_code == 200:
                    updated_lead = response.json()
                    if updated_lead.get("title") == "VP of Operations":
                        self.log_result("Leads Management - Update", True, "Lead updated successfully")
                        return True
                    else:
                        self.log_result("Leads Management - Update", False, f"Update not reflected: {updated_lead}")
                        return False
                else:
                    self.log_result("Leads Management - Update", False, f"Status {response.status_code}: {response.text}")
                    return False
            else:
                self.log_result("Leads Management - Create", False, "No ID in created lead")
                return False
        else:
            self.log_result("Leads Management - Create", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_appointments(self):
        """Test GET /api/appointments - Verify appointments load without errors"""
        print("\n📅 Testing Appointments...")
        
        if not self.auth_token:
            self.log_result("Appointments", False, "No auth token available")
            return False
        
        response, error = self.make_request("GET", "/appointments")
        
        if error:
            self.log_result("Appointments", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            appointments = response.json()
            if isinstance(appointments, list):
                self.log_result("Appointments", True, f"Retrieved {len(appointments)} appointments without errors")
                return True
            else:
                self.log_result("Appointments", False, "Response is not a list")
                return False
        else:
            self.log_result("Appointments", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_scheduling_system(self):
        """Test Calendly-like scheduling system"""
        print("\n🗓️ Testing Scheduling System...")
        
        if not self.auth_token:
            self.log_result("Scheduling System", False, "No auth token available")
            return False
        
        # Test GET /api/meeting-types
        response, error = self.make_request("GET", "/meeting-types")
        
        if error:
            self.log_result("Scheduling - Meeting Types", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            meeting_types = response.json()
            if isinstance(meeting_types, list):
                self.log_result("Scheduling - Meeting Types", True, f"Retrieved {len(meeting_types)} meeting types")
                
                # Test GET /api/availability
                response, error = self.make_request("GET", "/availability")
                
                if error:
                    self.log_result("Scheduling - Availability", False, f"Request failed: {error}")
                    return False
                
                if response.status_code == 200:
                    availability = response.json()
                    if isinstance(availability, list):
                        self.log_result("Scheduling - Availability", True, f"Retrieved {len(availability)} availability rules")
                        return True
                    else:
                        self.log_result("Scheduling - Availability", False, "Response is not a list")
                        return False
                else:
                    self.log_result("Scheduling - Availability", False, f"Status {response.status_code}: {response.text}")
                    return False
            else:
                self.log_result("Scheduling - Meeting Types", False, "Response is not a list")
                return False
        else:
            self.log_result("Scheduling - Meeting Types", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_call_analytics(self):
        """Test call analytics endpoints"""
        print("\n📞 Testing Call Analytics...")
        
        if not self.auth_token:
            self.log_result("Call Analytics", False, "No auth token available")
            return False
        
        # Test GET /api/calls/logs
        response, error = self.make_request("GET", "/calls/logs")
        
        if error:
            self.log_result("Call Analytics - Logs", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            call_logs = response.json()
            if isinstance(call_logs, list):
                self.log_result("Call Analytics - Logs", True, f"Retrieved {len(call_logs)} call logs")
                
                # Test GET /api/calls/stats
                response, error = self.make_request("GET", "/calls/stats")
                
                if error:
                    self.log_result("Call Analytics - Stats", False, f"Request failed: {error}")
                    return False
                
                if response.status_code == 200:
                    stats = response.json()
                    if isinstance(stats, dict) and "total_calls" in stats:
                        self.log_result("Call Analytics - Stats", True, f"Retrieved call statistics: {stats.get('total_calls', 0)} total calls")
                        return True
                    else:
                        self.log_result("Call Analytics - Stats", False, f"Invalid stats format: {stats}")
                        return False
                else:
                    self.log_result("Call Analytics - Stats", False, f"Status {response.status_code}: {response.text}")
                    return False
            else:
                self.log_result("Call Analytics - Logs", False, "Response is not a list")
                return False
        else:
            self.log_result("Call Analytics - Logs", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_team_chat(self):
        """Test team chat endpoints"""
        print("\n💬 Testing Team Chat...")
        
        if not self.auth_token:
            self.log_result("Team Chat", False, "No auth token available")
            return False
        
        # Test GET /api/chat/channels
        response, error = self.make_request("GET", "/chat/channels")
        
        if error:
            self.log_result("Team Chat - Channels", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            channels = response.json()
            if isinstance(channels, list):
                self.log_result("Team Chat - Channels", True, f"Retrieved {len(channels)} chat channels")
                
                if len(channels) > 0:
                    channel_id = channels[0]["id"]
                    
                    # Test GET /api/chat/messages/{channel_id}
                    response, error = self.make_request("GET", f"/chat/messages/{channel_id}")
                    
                    if error:
                        self.log_result("Team Chat - Messages", False, f"Request failed: {error}")
                        return False
                    
                    if response.status_code == 200:
                        messages = response.json()
                        if isinstance(messages, list):
                            self.log_result("Team Chat - Messages", True, f"Retrieved {len(messages)} messages from channel")
                            return True
                        else:
                            self.log_result("Team Chat - Messages", False, "Response is not a list")
                            return False
                    else:
                        self.log_result("Team Chat - Messages", False, f"Status {response.status_code}: {response.text}")
                        return False
                else:
                    self.log_result("Team Chat - Messages", True, "No channels available (expected for new system)")
                    return True
            else:
                self.log_result("Team Chat - Channels", False, "Response is not a list")
                return False
        else:
            self.log_result("Team Chat - Channels", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_user_management(self):
        """Test user management endpoints"""
        print("\n👥 Testing User Management...")
        
        if not self.auth_token:
            self.log_result("User Management", False, "No auth token available")
            return False
        
        # Test GET /api/users
        response, error = self.make_request("GET", "/users")
        
        if error:
            self.log_result("User Management - Get Users", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            users = response.json()
            if isinstance(users, list):
                self.log_result("User Management - Get Users", True, f"Retrieved {len(users)} users")
                
                # Test GET /api/users/status (if endpoint exists)
                response, error = self.make_request("GET", "/users/status")
                
                if error:
                    self.log_result("User Management - Status", False, f"Request failed: {error}")
                    return True  # Don't fail the whole test if this endpoint doesn't exist
                
                if response.status_code == 200:
                    status_data = response.json()
                    self.log_result("User Management - Status", True, f"Retrieved user status data")
                    return True
                else:
                    self.log_result("User Management - Status", False, f"Status {response.status_code}: {response.text}")
                    return True  # Don't fail the whole test
            else:
                self.log_result("User Management - Get Users", False, "Response is not a list")
                return False
        else:
            self.log_result("User Management - Get Users", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def run_deployment_tests(self):
        """Run critical pre-deployment tests"""
        print("🚀 Starting LeadGen Pro Pre-Deployment Testing...")
        print(f"🌐 Backend URL: {self.base_url}")
        print(f"🔑 Test Credentials: {TEST_EMAIL}")
        print("=" * 60)
        
        # Critical Feature Tests (as specified in review request)
        print("\n🔐 AUTHENTICATION TESTS")
        print("-" * 30)
        if not self.test_admin_login():
            print("❌ CRITICAL: Admin login failed - cannot proceed with other tests")
            return self.results
        
        self.test_get_current_user()
        
        print("\n📊 CSV LEAD IMPORT (PRIORITY)")
        print("-" * 30)
        self.test_csv_lead_import()
        
        print("\n📋 LEADS MANAGEMENT")
        print("-" * 30)
        self.test_leads_management()
        
        print("\n📅 MEETINGS/APPOINTMENTS")
        print("-" * 30)
        self.test_appointments()
        
        print("\n🗓️ SCHEDULING SYSTEM (CALENDLY-LIKE)")
        print("-" * 30)
        self.test_scheduling_system()
        
        print("\n📞 CALL ANALYTICS")
        print("-" * 30)
        self.test_call_analytics()
        
        print("\n💬 TEAM CHAT")
        print("-" * 30)
        self.test_team_chat()
        
        print("\n👥 USER MANAGEMENT")
        print("-" * 30)
        self.test_user_management()
        
        # Print final results
        print("\n" + "=" * 60)
        print("🏁 PRE-DEPLOYMENT TESTING COMPLETE")
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['errors']:
            print("\n🚨 FAILED TESTS:")
            for error in self.results['errors']:
                print(f"   • {error}")
        
        success_rate = (self.results['passed'] / (self.results['passed'] + self.results['failed'])) * 100 if (self.results['passed'] + self.results['failed']) > 0 else 0
        print(f"\n📊 Success Rate: {success_rate:.1f}%")
        
        # Deployment readiness assessment
        critical_failures = [error for error in self.results['errors'] if any(critical in error.lower() for critical in ['login', 'csv', 'auth'])]
        
        if critical_failures:
            print("\n🚨 DEPLOYMENT NOT RECOMMENDED - Critical failures detected:")
            for failure in critical_failures:
                print(f"   ⚠️ {failure}")
        elif self.results['failed'] == 0:
            print("\n✅ DEPLOYMENT READY - All tests passed!")
        elif success_rate >= 90:
            print("\n⚠️ DEPLOYMENT READY WITH MINOR ISSUES - Success rate above 90%")
        else:
            print(f"\n❌ DEPLOYMENT NOT RECOMMENDED - Success rate {success_rate:.1f}% below threshold")
        
        return self.results

if __name__ == "__main__":
    tester = LeadGenProDeploymentTester()
    results = tester.run_deployment_tests()
    
    # Exit with error code if critical tests failed
    critical_failures = [error for error in results['errors'] if any(critical in error.lower() for critical in ['login', 'csv', 'auth'])]
    if critical_failures or results['failed'] > results['passed']:
        sys.exit(1)
    else:
        sys.exit(0)