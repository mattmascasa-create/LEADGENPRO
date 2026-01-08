#!/usr/bin/env python3
"""
Pre-Deployment Testing for LeadGen Pro
Final verification of core functionality before deployment
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
import os
import sys

# Backend URL from frontend .env
BACKEND_URL = "https://leadgen-pro-23.preview.emergentagent.com/api"

class PreDeploymentTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.admin_token = None
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
        if self.admin_token and headers is None:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
        elif self.admin_token and headers:
            headers["Authorization"] = f"Bearer {self.admin_token}"
        
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
    
    def test_admin_login(self):
        """Test admin login with provided credentials"""
        print("\n🔐 Testing Admin Login...")
        
        login_data = {
            "email": "admin@test.com",
            "password": "admin123"
        }
        
        response, error = self.make_request("POST", "/auth/login", login_data)
        
        if error:
            self.log_result("Admin Login", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data and "user" in data:
                self.admin_token = data["access_token"]
                self.log_result("Admin Login", True, f"Admin login successful: {data['user']['email']}")
                return True
            else:
                self.log_result("Admin Login", False, "Missing token or user in response")
                return False
        else:
            self.log_result("Admin Login", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_check_admin_status(self):
        """Test GET /api/auth/check-admin - Should return is_admin: true"""
        print("\n👑 Testing Check Admin Status...")
        
        if not self.admin_token:
            self.log_result("Check Admin Status", False, "No admin token available")
            return False
        
        response, error = self.make_request("GET", "/auth/check-admin")
        
        if error:
            self.log_result("Check Admin Status", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            data = response.json()
            if "is_admin" in data and data["is_admin"] is True:
                self.log_result("Check Admin Status", True, f"Admin status confirmed: is_admin={data['is_admin']}")
                return True
            else:
                self.log_result("Check Admin Status", False, f"Admin status not confirmed: {data}")
                return False
        else:
            self.log_result("Check Admin Status", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_admin_dashboard_stats(self):
        """Test GET /api/admin/dashboard/stats - Should return company stats"""
        print("\n📊 Testing Admin Dashboard Stats...")
        
        if not self.admin_token:
            self.log_result("Admin Dashboard Stats", False, "No admin token available")
            return False
        
        response, error = self.make_request("GET", "/admin/dashboard/stats")
        
        if error:
            self.log_result("Admin Dashboard Stats", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            data = response.json()
            required_fields = ["total_employees", "total_leads", "calls_today", "meetings_today"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                self.log_result("Admin Dashboard Stats", True, f"Retrieved stats with {len(data)} fields")
                return True
            else:
                self.log_result("Admin Dashboard Stats", False, f"Missing required fields: {missing_fields}")
                return False
        else:
            self.log_result("Admin Dashboard Stats", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_employee_dashboard(self):
        """Test GET /api/employee/dashboard - Should return personal stats"""
        print("\n👤 Testing Employee Dashboard...")
        
        if not self.admin_token:
            self.log_result("Employee Dashboard", False, "No admin token available")
            return False
        
        response, error = self.make_request("GET", "/employee/dashboard")
        
        if error:
            self.log_result("Employee Dashboard", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            data = response.json()
            required_fields = ["daily_goals", "progress", "personal_stats"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                self.log_result("Employee Dashboard", True, f"Retrieved dashboard with {len(data)} sections")
                return True
            else:
                self.log_result("Employee Dashboard", False, f"Missing required fields: {missing_fields}")
                return False
        else:
            self.log_result("Employee Dashboard", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_calendar_with_meet(self):
        """Test POST /api/calendar/events/with-meet - Should create event with Meet link"""
        print("\n📅 Testing Calendar with Meet...")
        
        if not self.admin_token:
            self.log_result("Calendar with Meet", False, "No admin token available")
            return False
        
        event_data = {
            "title": "Pre-deployment Test Meeting",
            "description": "Testing Google Meet integration",
            "type": "meeting",
            "start": (datetime.now() + timedelta(hours=1)).isoformat(),
            "end": (datetime.now() + timedelta(hours=2)).isoformat(),
            "attendees": ["admin@test.com"],
            "location": "Virtual"
        }
        
        response, error = self.make_request("POST", "/calendar/events/with-meet", event_data)
        
        if error:
            self.log_result("Calendar with Meet", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            data = response.json()
            if "meeting_link" in data and data["meeting_link"] and "meet.google.com" in data["meeting_link"]:
                self.log_result("Calendar with Meet", True, f"Event created with Meet link: {data['meeting_link']}")
                return True
            else:
                self.log_result("Calendar with Meet", False, f"No valid Meet link in response: {data}")
                return False
        else:
            self.log_result("Calendar with Meet", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_crm_integrations(self):
        """Test GET /api/integrations/crm - Should return empty array or integrations"""
        print("\n🔗 Testing CRM Integrations...")
        
        if not self.admin_token:
            self.log_result("CRM Integrations", False, "No admin token available")
            return False
        
        response, error = self.make_request("GET", "/integrations/crm")
        
        if error:
            self.log_result("CRM Integrations", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                self.log_result("CRM Integrations", True, f"Retrieved {len(data)} CRM integrations")
                return True
            else:
                self.log_result("CRM Integrations", False, f"Expected array, got: {type(data)}")
                return False
        else:
            self.log_result("CRM Integrations", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_email_configuration(self):
        """Verify SENDER_EMAIL is team@leadgenpro2.com"""
        print("\n📧 Testing Email Configuration...")
        
        # Check backend .env file for SENDER_EMAIL
        try:
            with open('/app/backend/.env', 'r') as f:
                env_content = f.read()
                
            if 'SENDER_EMAIL=team@leadgenpro2.com' in env_content:
                self.log_result("Email Configuration", True, "SENDER_EMAIL correctly set to team@leadgenpro2.com")
                return True
            else:
                self.log_result("Email Configuration", False, "SENDER_EMAIL not set to team@leadgenpro2.com")
                return False
        except Exception as e:
            self.log_result("Email Configuration", False, f"Failed to read .env file: {e}")
            return False
    
    def run_pre_deployment_tests(self):
        """Run all pre-deployment tests"""
        print("🚀 Starting LeadGen Pro Pre-Deployment Testing...")
        print(f"🌐 Backend URL: {self.base_url}")
        print("🔑 Test Credentials: admin@test.com / admin123")
        print("=" * 60)
        
        # Test sequence as specified in review request
        tests = [
            ("Authentication", self.test_admin_login),
            ("Check Admin Status", self.test_check_admin_status),
            ("Admin Dashboard Stats", self.test_admin_dashboard_stats),
            ("Employee Dashboard", self.test_employee_dashboard),
            ("Calendar with Meet", self.test_calendar_with_meet),
            ("CRM Integrations", self.test_crm_integrations),
            ("Email Configuration", self.test_email_configuration)
        ]
        
        for test_name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                self.log_result(test_name, False, f"Test threw exception: {e}")
        
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
        
        if success_rate == 100:
            print("\n🎉 ALL TESTS PASSED - READY FOR DEPLOYMENT!")
        else:
            print("\n⚠️  SOME TESTS FAILED - REVIEW BEFORE DEPLOYMENT")
        
        return self.results

if __name__ == "__main__":
    tester = PreDeploymentTester()
    results = tester.run_pre_deployment_tests()
    
    # Exit with error code if tests failed
    if results['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)