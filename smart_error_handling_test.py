#!/usr/bin/env python3
"""
Smart Error Handling & Auto-Fix System Testing for LeadGen Pro
Tests the new error reporting, diagnosis, and auto-fix capabilities
"""

import requests
import json
import uuid
import io
import csv
from datetime import datetime, timedelta
import os
import sys

# Backend URL from frontend .env
BACKEND_URL = "https://leadgenpro-7.preview.emergentagent.com/api"

class SmartErrorHandlingTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.auth_token = None
        self.admin_user_id = None
        self.test_error_id = None
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
    
    def setup_admin_auth(self):
        """Login with admin credentials"""
        print("\n🔐 Setting up Admin Authentication...")
        
        login_data = {
            "email": "admin@test.com",
            "password": "admin123"
        }
        
        response, error = self.make_request("POST", "/auth/login", login_data)
        
        if error:
            self.log_result("Admin Login Setup", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data and "user" in data:
                self.auth_token = data["access_token"]
                self.admin_user_id = data["user"]["id"]
                self.log_result("Admin Login Setup", True, f"Admin authenticated: {data['user']['email']}")
                return True
            else:
                self.log_result("Admin Login Setup", False, "Missing token or user in response")
                return False
        else:
            self.log_result("Admin Login Setup", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_error_reporting_api(self):
        """Test POST /api/errors/report - Report various error categories"""
        print("\n🚨 Testing Error Reporting API...")
        
        if not self.auth_token:
            self.log_result("Error Reporting API", False, "No auth token available")
            return False
        
        # Test different error categories (using correct ErrorReport model structure)
        test_errors = [
            {
                "error_type": "authentication_failed",
                "error_message": "JWT token has expired",
                "endpoint": "/api/leads",
                "request_data": {"action": "get_leads"},
                "stack_trace": "TokenExpiredError: JWT token expired at 2024-01-08T10:30:00Z",
                "user_agent": "Mozilla/5.0 (Chrome/120.0.0.0)",
                "page_url": "https://leadgenpro-7.preview.emergentagent.com/leads"
            },
            {
                "error_type": "file_upload_failed",
                "error_message": "Authorization header missing in CSV upload request",
                "endpoint": "/api/leads/bulk-import",
                "request_data": {"filename": "leads.csv"},
                "stack_trace": "HTTPException: Authorization header required",
                "user_agent": "Mozilla/5.0 (Chrome/120.0.0.0)",
                "page_url": "https://leadgenpro-7.preview.emergentagent.com/leads"
            },
            {
                "error_type": "database_connection_failed",
                "error_message": "Cannot connect to MongoDB database",
                "endpoint": "/api/leads",
                "request_data": {"query": "find_all"},
                "stack_trace": "ConnectionError: MongoDB connection timeout",
                "user_agent": "Mozilla/5.0 (Chrome/120.0.0.0)",
                "page_url": "https://leadgenpro-7.preview.emergentagent.com/dashboard"
            },
            {
                "error_type": "network_timeout",
                "error_message": "Request to external API timed out",
                "endpoint": "/api/assistant/chat",
                "request_data": {"message": "How do I add a lead?"},
                "stack_trace": "TimeoutError: Request timeout after 30 seconds",
                "user_agent": "Mozilla/5.0 (Chrome/120.0.0.0)",
                "page_url": "https://leadgenpro-7.preview.emergentagent.com/dashboard"
            }
        ]
        
        success_count = 0
        for i, error_data in enumerate(test_errors):
            response, error = self.make_request("POST", "/errors/report", error_data)
            
            if error:
                self.log_result(f"Error Report {i+1} ({error_data['error_type']})", False, f"Request failed: {error}")
                continue
            
            if response.status_code == 200:
                result = response.json()
                if "error_id" in result and "user_suggestion" in result:
                    # Store first error ID for later tests
                    if i == 0:
                        self.test_error_id = result["error_id"]
                    
                    # Check auto-fix suggestions
                    user_suggestion = result["user_suggestion"]
                    category = result.get("category", "unknown")
                    severity = result.get("severity", "unknown")
                    
                    if user_suggestion:
                        self.log_result(f"Error Report {i+1} ({error_data['error_type']})", True, 
                                      f"Category: {category} | Severity: {severity} | Suggestion: {user_suggestion[:40]}...")
                        success_count += 1
                    else:
                        self.log_result(f"Error Report {i+1} ({error_data['error_type']})", False, 
                                      "Missing user_suggestion")
                else:
                    self.log_result(f"Error Report {i+1} ({error_data['error_type']})", False, 
                                  f"Missing error_id or user_suggestion in response: {result}")
            else:
                self.log_result(f"Error Report {i+1} ({error_data['error_type']})", False, 
                              f"Status {response.status_code}: {response.text}")
        
        # Overall test result
        if success_count == len(test_errors):
            self.log_result("Error Reporting API", True, f"All {success_count} error categories tested successfully")
            return True
        else:
            self.log_result("Error Reporting API", False, f"Only {success_count}/{len(test_errors)} error reports succeeded")
            return False
    
    def test_support_bot_diagnosis(self):
        """Test POST /api/support-bot/diagnose - AI-powered error diagnosis"""
        print("\n🤖 Testing Support Bot Diagnosis...")
        
        if not self.auth_token:
            self.log_result("Support Bot Diagnosis", False, "No auth token available")
            return False
        
        # Test AI diagnosis for different error scenarios (using correct SupportBotRequest model)
        test_scenarios = [
            {
                "question": "CSV upload failed with 401 Unauthorized error",
                "context": {
                    "endpoint": "/api/leads/bulk-import",
                    "user_action": "Uploading leads CSV file",
                    "browser": "Chrome 120",
                    "page": "/leads"
                }
            },
            {
                "question": "Database connection timeout when loading leads page",
                "context": {
                    "endpoint": "/api/leads",
                    "user_action": "Loading leads page",
                    "error_code": "ECONNREFUSED",
                    "page": "/leads"
                }
            },
            {
                "question": "Google Sign-In redirect failed with invalid session",
                "context": {
                    "endpoint": "/auth/google",
                    "user_action": "Signing in with Google",
                    "session_id": "invalid_session_123",
                    "page": "/login"
                }
            }
        ]
        
        # If we have a test error ID from previous test, also test with error_id
        if self.test_error_id:
            test_scenarios.append({
                "error_id": self.test_error_id,
                "question": "What caused this authentication error and how can I fix it?",
                "context": {"page": "/dashboard"}
            })
        
        success_count = 0
        for i, scenario in enumerate(test_scenarios):
            response, error = self.make_request("POST", "/support-bot/diagnose", scenario)
            
            if error:
                self.log_result(f"AI Diagnosis {i+1}", False, f"Request failed: {error}")
                continue
            
            if response.status_code == 200:
                result = response.json()
                required_fields = ["diagnosis", "fix_steps"]
                
                if all(field in result for field in required_fields):
                    # Check if fix_steps is a list with actual steps
                    if isinstance(result["fix_steps"], list) and len(result["fix_steps"]) > 0:
                        diagnosis = result["diagnosis"]
                        fix_steps_count = len(result["fix_steps"])
                        can_auto_fix = result.get("can_auto_fix", False)
                        
                        self.log_result(f"AI Diagnosis {i+1}", True, 
                                      f"Diagnosis: {diagnosis[:40]}... | Steps: {fix_steps_count} | Auto-fix: {can_auto_fix}")
                        success_count += 1
                    else:
                        self.log_result(f"AI Diagnosis {i+1}", False, "fix_steps is empty or not a list")
                else:
                    missing = [f for f in required_fields if f not in result]
                    self.log_result(f"AI Diagnosis {i+1}", False, f"Missing fields: {missing}")
            else:
                self.log_result(f"AI Diagnosis {i+1}", False, f"Status {response.status_code}: {response.text}")
        
        # Overall test result
        if success_count >= 3:  # At least 3 out of 3-4 scenarios should work
            self.log_result("Support Bot Diagnosis", True, f"{success_count} AI diagnosis scenarios working")
            return True
        else:
            self.log_result("Support Bot Diagnosis", False, f"Only {success_count} diagnoses succeeded")
            return False
    
    def test_system_health_api(self):
        """Test GET /api/admin/system-health - System health monitoring"""
        print("\n🏥 Testing System Health API...")
        
        if not self.auth_token:
            self.log_result("System Health API", False, "No auth token available")
            return False
        
        response, error = self.make_request("GET", "/admin/system-health")
        
        if error:
            self.log_result("System Health API", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            health_data = response.json()
            
            # Check required fields
            required_fields = ["overall_status", "services", "last_checked"]
            if all(field in health_data for field in required_fields):
                
                # Check services status
                services = health_data["services"]
                expected_services = ["database", "email", "ai"]
                
                if all(service in services for service in expected_services):
                    # Check each service has status
                    all_services_ok = True
                    service_statuses = []
                    
                    for service in expected_services:
                        if "status" in services[service]:
                            status = services[service]["status"]
                            service_statuses.append(f"{service}:{status}")
                        else:
                            all_services_ok = False
                            break
                    
                    if all_services_ok:
                        self.log_result("System Health API", True, 
                                      f"Overall: {health_data['overall_status']} | Services: {', '.join(service_statuses)}")
                        return True
                    else:
                        self.log_result("System Health API", False, "Some services missing status field")
                        return False
                else:
                    missing_services = [s for s in expected_services if s not in services]
                    self.log_result("System Health API", False, f"Missing services: {missing_services}")
                    return False
            else:
                missing_fields = [f for f in required_fields if f not in health_data]
                self.log_result("System Health API", False, f"Missing fields: {missing_fields}")
                return False
        else:
            self.log_result("System Health API", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_admin_errors_list(self):
        """Test GET /api/admin/errors - Admin errors list with filtering"""
        print("\n📋 Testing Admin Errors List...")
        
        if not self.auth_token:
            self.log_result("Admin Errors List", False, "No auth token available")
            return False
        
        # Test basic errors list
        response, error = self.make_request("GET", "/admin/errors")
        
        if error:
            self.log_result("Admin Errors List (Basic)", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            data = response.json()
            
            if "errors" in data and "stats" in data:
                errors = data["errors"]
                stats = data["stats"]
                
                # Check stats structure
                expected_stats = ["total", "by_severity", "by_category", "resolved_count"]
                if all(stat in stats for stat in expected_stats):
                    self.log_result("Admin Errors List (Basic)", True, 
                                  f"Retrieved {len(errors)} errors | Total: {stats['total']}")
                    
                    # Test filtering by severity
                    filter_tests = [
                        ("severity=critical", "Critical severity filter"),
                        ("category=authentication", "Authentication category filter"),
                        ("resolved=false", "Unresolved errors filter")
                    ]
                    
                    filter_success = 0
                    for filter_param, test_name in filter_tests:
                        filter_response, filter_error = self.make_request("GET", f"/admin/errors?{filter_param}")
                        
                        if not filter_error and filter_response.status_code == 200:
                            filter_data = filter_response.json()
                            if "errors" in filter_data:
                                self.log_result(f"Admin Errors List ({test_name})", True, 
                                              f"Filtered to {len(filter_data['errors'])} errors")
                                filter_success += 1
                            else:
                                self.log_result(f"Admin Errors List ({test_name})", False, "Missing errors in filtered response")
                        else:
                            self.log_result(f"Admin Errors List ({test_name})", False, 
                                          f"Filter failed: {filter_error or filter_response.text}")
                    
                    # Overall result
                    if filter_success == len(filter_tests):
                        self.log_result("Admin Errors List", True, "All filtering options working")
                        return True
                    else:
                        self.log_result("Admin Errors List", False, f"Only {filter_success}/{len(filter_tests)} filters working")
                        return False
                else:
                    missing_stats = [s for s in expected_stats if s not in stats]
                    self.log_result("Admin Errors List (Basic)", False, f"Missing stats: {missing_stats}")
                    return False
            else:
                self.log_result("Admin Errors List (Basic)", False, "Missing errors or stats in response")
                return False
        else:
            self.log_result("Admin Errors List (Basic)", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_notifications_api(self):
        """Test GET /api/notifications - Notifications endpoint"""
        print("\n🔔 Testing Notifications API...")
        
        if not self.auth_token:
            self.log_result("Notifications API", False, "No auth token available")
            return False
        
        response, error = self.make_request("GET", "/notifications")
        
        if error:
            self.log_result("Notifications API", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            data = response.json()
            
            # Check required fields
            if "notifications" in data and "unread_count" in data:
                notifications = data["notifications"]
                unread_count = data["unread_count"]
                
                # Check notification structure if any exist
                if len(notifications) > 0:
                    first_notification = notifications[0]
                    required_fields = ["id", "type", "message", "created_at"]
                    
                    if all(field in first_notification for field in required_fields):
                        self.log_result("Notifications API", True, 
                                      f"Retrieved {len(notifications)} notifications | Unread: {unread_count}")
                        return True
                    else:
                        missing_fields = [f for f in required_fields if f not in first_notification]
                        self.log_result("Notifications API", False, f"Notification missing fields: {missing_fields}")
                        return False
                else:
                    # No notifications is also valid
                    self.log_result("Notifications API", True, 
                                  f"No notifications found | Unread count: {unread_count}")
                    return True
            else:
                self.log_result("Notifications API", False, "Missing notifications or unread_count in response")
                return False
        else:
            self.log_result("Notifications API", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_csv_upload_with_auth(self):
        """Test POST /api/leads/bulk-import - CSV upload with proper Authorization header"""
        print("\n📁 Testing CSV Upload with Authorization...")
        
        if not self.auth_token:
            self.log_result("CSV Upload with Auth", False, "No auth token available")
            return False
        
        # Create test CSV content
        csv_content = """first_name,last_name,email,phone,company,title
John,Smith,john.smith@techcorp.com,+1-555-0101,TechCorp Inc,Sales Manager
Jane,Doe,jane.doe@innovate.com,+1-555-0102,Innovate Solutions,Marketing Director
Bob,Johnson,bob.johnson@startup.io,+1-555-0103,Startup IO,CEO"""
        
        # Create file-like object
        csv_file = io.StringIO(csv_content)
        
        # Prepare files for upload
        files = {
            'file': ('test_leads.csv', csv_file.getvalue(), 'text/csv')
        }
        
        # Make request with proper Authorization header
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        response, error = self.make_request("POST", "/leads/bulk-import", files=files, headers=headers)
        
        if error:
            self.log_result("CSV Upload with Auth", False, f"Request failed: {error}")
            return False
        
        if response.status_code == 200:
            result = response.json()
            
            # Check response structure
            if "success" in result and "failed" in result:
                success_count = result["success"]
                failed_count = result["failed"]
                
                if success_count > 0:
                    self.log_result("CSV Upload with Auth", True, 
                                  f"Uploaded {success_count} leads successfully | Failed: {failed_count}")
                    return True
                else:
                    errors = result.get("errors", [])
                    self.log_result("CSV Upload with Auth", False, 
                                  f"No leads uploaded | Errors: {errors}")
                    return False
            else:
                self.log_result("CSV Upload with Auth", False, "Missing success/failed counts in response")
                return False
        else:
            self.log_result("CSV Upload with Auth", False, f"Status {response.status_code}: {response.text}")
            return False
    
    def test_auto_fix_suggestions(self):
        """Test rule-based auto-fix suggestions for different error categories"""
        print("\n🔧 Testing Auto-Fix Suggestions...")
        
        if not self.auth_token:
            self.log_result("Auto-Fix Suggestions", False, "No auth token available")
            return False
        
        # Test auto-fix for different error categories
        auto_fix_tests = [
            {
                "error_type": "token_expired",
                "error_message": "JWT token has expired",
                "category": "authentication",
                "severity": "low",
                "expected_fix": "refresh_token"
            },
            {
                "error_type": "missing_auth_header",
                "error_message": "Authorization header missing in upload request",
                "category": "file_upload", 
                "severity": "medium",
                "expected_fix": "inject_auth_header"
            },
            {
                "error_type": "connection_failed",
                "error_message": "Cannot connect to database",
                "category": "database",
                "severity": "critical",
                "expected_fix": "retry_connection"
            },
            {
                "error_type": "timeout",
                "error_message": "Request timed out",
                "category": "network",
                "severity": "medium",
                "expected_fix": "retry_request"
            }
        ]
        
        success_count = 0
        for i, test_case in enumerate(auto_fix_tests):
            response, error = self.make_request("POST", "/errors/report", test_case)
            
            if error:
                self.log_result(f"Auto-Fix Test {i+1} ({test_case['category']})", False, f"Request failed: {error}")
                continue
            
            if response.status_code == 200:
                result = response.json()
                
                if "auto_fix_suggestions" in result:
                    suggestions = result["auto_fix_suggestions"]
                    
                    # Check if auto-fix suggestions contain expected elements
                    if "user_action" in suggestions and "admin_action" in suggestions:
                        user_action = suggestions["user_action"]
                        admin_action = suggestions["admin_action"]
                        
                        # Verify suggestions are relevant to the error category
                        category_keywords = {
                            "authentication": ["log in", "token", "credentials"],
                            "file_upload": ["upload", "file", "authorization"],
                            "database": ["database", "connection", "MongoDB"],
                            "network": ["try again", "request", "service"]
                        }
                        
                        expected_keywords = category_keywords.get(test_case["category"], [])
                        suggestion_text = (user_action + " " + admin_action).lower()
                        
                        if any(keyword in suggestion_text for keyword in expected_keywords):
                            self.log_result(f"Auto-Fix Test {i+1} ({test_case['category']})", True, 
                                          f"Relevant suggestions provided: {user_action[:40]}...")
                            success_count += 1
                        else:
                            self.log_result(f"Auto-Fix Test {i+1} ({test_case['category']})", False, 
                                          f"Suggestions not relevant to {test_case['category']}")
                    else:
                        self.log_result(f"Auto-Fix Test {i+1} ({test_case['category']})", False, 
                                      "Missing user_action or admin_action in suggestions")
                else:
                    self.log_result(f"Auto-Fix Test {i+1} ({test_case['category']})", False, 
                                  "No auto_fix_suggestions in response")
            else:
                self.log_result(f"Auto-Fix Test {i+1} ({test_case['category']})", False, 
                              f"Status {response.status_code}: {response.text}")
        
        # Overall result
        if success_count == len(auto_fix_tests):
            self.log_result("Auto-Fix Suggestions", True, f"All {success_count} auto-fix categories working correctly")
            return True
        else:
            self.log_result("Auto-Fix Suggestions", False, f"Only {success_count}/{len(auto_fix_tests)} auto-fix tests passed")
            return False
    
    def run_all_tests(self):
        """Run all Smart Error Handling & Auto-Fix tests"""
        print("🚀 Starting Smart Error Handling & Auto-Fix System Testing...")
        print(f"🌐 Backend URL: {self.base_url}")
        print("=" * 70)
        
        # Setup authentication
        if not self.setup_admin_auth():
            print("❌ Failed to authenticate admin user. Cannot proceed with tests.")
            return self.results
        
        print("\n🔧 SMART ERROR HANDLING TESTS")
        print("-" * 40)
        
        # Test all error handling endpoints
        self.test_error_reporting_api()
        self.test_support_bot_diagnosis()
        self.test_system_health_api()
        self.test_admin_errors_list()
        self.test_notifications_api()
        self.test_csv_upload_with_auth()
        self.test_auto_fix_suggestions()
        
        # Print final results
        print("\n" + "=" * 70)
        print("🏁 SMART ERROR HANDLING TESTING COMPLETE")
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
    tester = SmartErrorHandlingTester()
    results = tester.run_all_tests()
    
    # Exit with error code if tests failed
    if results['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)