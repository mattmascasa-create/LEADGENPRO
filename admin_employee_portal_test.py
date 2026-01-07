#!/usr/bin/env python3
"""
Admin/Employee Portal System Testing for LeadGen Pro
Tests all new admin and employee portal backend APIs
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
import os
import sys

# Backend URL from frontend .env
BACKEND_URL = "https://leadgen-pro-23.preview.emergentagent.com/api"

class AdminEmployeePortalTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.admin_token = None
        self.employee_token = None
        self.admin_user_id = None
        self.employee_user_id = None
        self.test_lead_ids = []
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
    
    def make_request(self, method, endpoint, data=None, headers=None, token=None):
        """Make HTTP request with proper error handling"""
        url = f"{self.base_url}{endpoint}"
        
        # Add auth header if token exists
        if token and headers is None:
            headers = {"Authorization": f"Bearer {token}"}
        elif token and headers:
            headers["Authorization"] = f"Bearer {token}"
        
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
    
    def setup_test_users(self):
        """Setup admin and employee test users"""
        print("\n🔧 Setting up test users...")
        
        # Test with provided admin credentials first
        admin_login_data = {
            "email": "admin@test.com",
            "password": "admin123"
        }
        
        response, error = self.make_request("POST", "/auth/login", admin_login_data)
        
        if not error and response.status_code == 200:
            data = response.json()
            self.admin_token = data["access_token"]
            self.admin_user_id = data["user"]["id"]
            self.log_result("Admin Login Setup", True, f"Admin logged in: {data['user']['email']}")
        else:
            # If admin@test.com doesn't exist, create it
            admin_reg_data = {
                "email": "admin@test.com",
                "password": "admin123",
                "full_name": "Test Admin",
                "role": "admin",
                "company": "LeadGen Pro"
            }
            
            reg_response, reg_error = self.make_request("POST", "/auth/register", admin_reg_data)
            if not reg_error and reg_response.status_code == 200:
                data = reg_response.json()
                self.admin_token = data["access_token"]
                self.admin_user_id = data["user"]["id"]
                self.log_result("Admin Registration Setup", True, f"Admin created: {data['user']['email']}")
            else:
                self.log_result("Admin Setup", False, f"Failed to setup admin user: {reg_error or reg_response.text}")
                return False
        
        # Create employee test user
        employee_email = f"employee_{uuid.uuid4().hex[:8]}@leadgenpro.com"
        employee_data = {
            "email": employee_email,
            "password": "Employee123!",
            "full_name": "Test Employee",
            "role": "employee",
            "company": "LeadGen Pro"
        }
        
        response, error = self.make_request("POST", "/auth/register", employee_data)
        
        if not error and response.status_code == 200:
            data = response.json()
            self.employee_token = data["access_token"]
            self.employee_user_id = data["user"]["id"]
            self.log_result("Employee Setup", True, f"Employee created: {data['user']['email']}")
            return True
        else:
            self.log_result("Employee Setup", False, f"Failed to create employee: {error or response.text}")
            return False
    
    def create_test_leads(self):
        """Create test leads for testing"""
        print("\n📋 Creating test leads...")
        
        if not self.admin_token:
            self.log_result("Create Test Leads", False, "No admin token available")
            return False
        
        test_leads = [
            {
                "first_name": "John",
                "last_name": "Smith",
                "email": "john.smith@techcorp.com",
                "phone": "+1-555-0101",
                "company": "TechCorp Inc",
                "title": "CEO",
                "status": "new",
                "tags": ["enterprise"]
            },
            {
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane.doe@startup.com",
                "phone": "+1-555-0102",
                "company": "Startup Solutions",
                "title": "CTO",
                "status": "new",
                "tags": ["startup"]
            },
            {
                "first_name": "Mike",
                "last_name": "Johnson",
                "email": "mike.johnson@enterprise.com",
                "phone": "+1-555-0103",
                "company": "Enterprise Corp",
                "title": "VP Sales",
                "status": "new",
                "tags": ["enterprise", "high-priority"]
            }
        ]
        
        for lead_data in test_leads:
            response, error = self.make_request("POST", "/leads", lead_data, token=self.admin_token)
            
            if not error and response.status_code == 200:
                lead = response.json()
                self.test_lead_ids.append(lead["id"])
            else:
                self.log_result("Create Test Lead", False, f"Failed to create lead: {error or response.text}")
        
        self.log_result("Create Test Leads", True, f"Created {len(self.test_lead_ids)} test leads")
        return len(self.test_lead_ids) > 0
    
    def test_admin_dashboard_stats(self):
        """Test GET /api/admin/dashboard/stats"""
        print("\n📊 Testing Admin Dashboard Stats...")
        
        if not self.admin_token:
            self.log_result("Admin Dashboard Stats", False, "No admin token available")
            return False
        
        response, error = self.make_request("GET", "/admin/dashboard/stats", token=self.admin_token)
        
        if error:
            self.log_result("Admin Dashboard Stats", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            stats = response.json()
            required_fields = ["total_employees", "total_leads", "calls_today", "meetings_today", "pipeline_stages", "conversion_rate"]
            
            missing_fields = [field for field in required_fields if field not in stats]
            if missing_fields:
                self.log_result("Admin Dashboard Stats", False, f"Missing fields: {missing_fields}")
                return False
            
            self.log_result("Admin Dashboard Stats", True, f"Retrieved stats: {len(stats)} fields")
            return True
        else:
            self.log_result("Admin Dashboard Stats", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_employee_performance(self):
        """Test GET /api/admin/employees/performance"""
        print("\n👥 Testing Employee Performance...")
        
        if not self.admin_token:
            self.log_result("Employee Performance", False, "No admin token available")
            return False
        
        response, error = self.make_request("GET", "/admin/employees/performance", token=self.admin_token)
        
        if error:
            self.log_result("Employee Performance", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            performance = response.json()
            if isinstance(performance, list):
                # Check if each employee has required fields
                if performance:
                    required_fields = ["calls_today", "calls_total", "meetings_today", "leads_assigned", "conversion_rate"]
                    employee = performance[0]
                    missing_fields = [field for field in required_fields if field not in employee]
                    if missing_fields:
                        self.log_result("Employee Performance", False, f"Missing fields in employee data: {missing_fields}")
                        return False
                
                self.log_result("Employee Performance", True, f"Retrieved performance for {len(performance)} employees")
                return True
            else:
                self.log_result("Employee Performance", False, "Response is not a list")
                return False
        else:
            self.log_result("Employee Performance", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_check_admin_status(self):
        """Test GET /api/auth/check-admin"""
        print("\n🔐 Testing Check Admin Status...")
        
        if not self.admin_token:
            self.log_result("Check Admin Status", False, "No admin token available")
            return False
        
        response, error = self.make_request("GET", "/auth/check-admin", token=self.admin_token)
        
        if error:
            self.log_result("Check Admin Status", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            admin_status = response.json()
            required_fields = ["is_admin", "role", "email"]
            
            missing_fields = [field for field in required_fields if field not in admin_status]
            if missing_fields:
                self.log_result("Check Admin Status", False, f"Missing fields: {missing_fields}")
                return False
            
            if admin_status["is_admin"] != True:
                self.log_result("Check Admin Status", False, f"Expected is_admin=True, got {admin_status['is_admin']}")
                return False
            
            self.log_result("Check Admin Status", True, f"Admin status confirmed: {admin_status['email']}")
            return True
        else:
            self.log_result("Check Admin Status", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_employee_dashboard(self):
        """Test GET /api/employee/dashboard"""
        print("\n📋 Testing Employee Dashboard...")
        
        if not self.employee_token:
            self.log_result("Employee Dashboard", False, "No employee token available")
            return False
        
        response, error = self.make_request("GET", "/employee/dashboard", token=self.employee_token)
        
        if error:
            self.log_result("Employee Dashboard", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            dashboard = response.json()
            required_fields = ["daily_goals", "progress", "admin_notes", "my_leads_count", "personal_stats"]
            
            missing_fields = [field for field in required_fields if field not in dashboard]
            if missing_fields:
                self.log_result("Employee Dashboard", False, f"Missing fields: {missing_fields}")
                return False
            
            self.log_result("Employee Dashboard", True, f"Retrieved dashboard with {len(dashboard)} sections")
            return True
        else:
            self.log_result("Employee Dashboard", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_my_leads(self):
        """Test GET /api/employee/my-leads"""
        print("\n📝 Testing My Leads...")
        
        if not self.employee_token:
            self.log_result("My Leads", False, "No employee token available")
            return False
        
        response, error = self.make_request("GET", "/employee/my-leads", token=self.employee_token)
        
        if error:
            self.log_result("My Leads", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            leads = response.json()
            if isinstance(leads, list):
                self.log_result("My Leads", True, f"Retrieved {len(leads)} assigned leads")
                return True
            else:
                self.log_result("My Leads", False, "Response is not a list")
                return False
        else:
            self.log_result("My Leads", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_my_stats(self):
        """Test GET /api/employee/my-stats"""
        print("\n📈 Testing My Stats...")
        
        if not self.employee_token:
            self.log_result("My Stats", False, "No employee token available")
            return False
        
        response, error = self.make_request("GET", "/employee/my-stats", token=self.employee_token)
        
        if error:
            self.log_result("My Stats", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            stats = response.json()
            required_fields = ["daily_calls", "total_calls", "conversion_rate", "connect_rate"]
            
            missing_fields = [field for field in required_fields if field not in stats]
            if missing_fields:
                self.log_result("My Stats", False, f"Missing fields: {missing_fields}")
                return False
            
            self.log_result("My Stats", True, f"Retrieved personal stats with {len(stats)} metrics")
            return True
        else:
            self.log_result("My Stats", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_set_daily_goals(self):
        """Test POST /api/admin/daily-goals"""
        print("\n🎯 Testing Set Daily Goals...")
        
        if not self.admin_token or not self.employee_user_id:
            self.log_result("Set Daily Goals", False, "No admin token or employee ID available")
            return False
        
        goals_data = {
            "employee_id": self.employee_user_id,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "calls_target": 25,
            "meetings_target": 3,
            "emails_target": 15,
            "notes": "Focus on enterprise leads this week"
        }
        
        response, error = self.make_request("POST", "/admin/daily-goals", goals_data, token=self.admin_token)
        
        if error:
            self.log_result("Set Daily Goals", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            result = response.json()
            if "message" in result or "success" in result:
                self.log_result("Set Daily Goals", True, "Daily goals set successfully")
                return True
            else:
                self.log_result("Set Daily Goals", False, "Invalid response format")
                return False
        else:
            self.log_result("Set Daily Goals", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_round_robin_distribution(self):
        """Test POST /api/admin/distribute-leads-roundrobin"""
        print("\n🔄 Testing Round Robin Distribution...")
        
        if not self.admin_token:
            self.log_result("Round Robin Distribution", False, "No admin token available")
            return False
        
        response, error = self.make_request("POST", "/admin/distribute-leads-roundrobin", token=self.admin_token)
        
        if error:
            self.log_result("Round Robin Distribution", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            result = response.json()
            if "message" in result or "distributed" in result:
                self.log_result("Round Robin Distribution", True, "Leads distributed successfully")
                return True
            else:
                self.log_result("Round Robin Distribution", False, "Invalid response format")
                return False
        else:
            self.log_result("Round Robin Distribution", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def run_all_tests(self):
        """Run all admin/employee portal tests"""
        print("🚀 Starting Admin/Employee Portal System Testing...")
        print(f"🌐 Backend URL: {self.base_url}")
        print("=" * 60)
        
        # Setup phase
        if not self.setup_test_users():
            print("❌ Failed to setup test users. Aborting tests.")
            return self.results
        
        self.create_test_leads()
        
        # Admin Portal Tests
        print("\n🔧 ADMIN PORTAL TESTS")
        print("-" * 30)
        self.test_admin_dashboard_stats()
        self.test_employee_performance()
        self.test_check_admin_status()
        self.test_set_daily_goals()
        self.test_round_robin_distribution()
        
        # Employee Portal Tests
        print("\n👤 EMPLOYEE PORTAL TESTS")
        print("-" * 30)
        self.test_employee_dashboard()
        self.test_my_leads()
        self.test_my_stats()
        
        # Print final results
        print("\n" + "=" * 60)
        print("🏁 ADMIN/EMPLOYEE PORTAL TESTING COMPLETE")
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
    tester = AdminEmployeePortalTester()
    results = tester.run_all_tests()
    
    # Exit with error code if tests failed
    if results['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)