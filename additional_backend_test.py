#!/usr/bin/env python3
"""
Additional Backend API Testing for LeadGen Pro
Tests bulk import and website scraper functionality
"""

import requests
import json
import uuid
import tempfile
import csv
import os

# Backend URL from frontend .env
BACKEND_URL = "https://salesautomation-2.preview.emergentagent.com/api"

class AdditionalTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.auth_token = None
        self.test_user_id = None
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
    
    def setup_auth(self):
        """Setup authentication for testing"""
        print("🔐 Setting up authentication...")
        
        # Register a test user
        test_email = f"bulktest_{uuid.uuid4().hex[:8]}@leadgenpro.com"
        user_data = {
            "email": test_email,
            "password": "BulkTest123!",
            "full_name": "Bulk Test User",
            "role": "admin"
        }
        
        response = self.session.post(f"{self.base_url}/auth/register", json=user_data, timeout=30)
        if response.status_code == 200:
            data = response.json()
            self.auth_token = data["access_token"]
            self.test_user_id = data["user"]["id"]
            print(f"✅ Authentication setup complete")
            return True
        else:
            print(f"❌ Authentication setup failed: {response.text}")
            return False
    
    def test_bulk_import_leads(self):
        """Test bulk import leads functionality"""
        print("\n📁 Testing Bulk Import Leads...")
        
        if not self.auth_token:
            self.log_result("Bulk Import Leads", False, "No auth token available")
            return False
        
        # Create a test CSV file
        csv_data = [
            ["first_name", "last_name", "email", "company", "title", "phone"],
            ["John", "Smith", "john.smith@acmecorp.com", "ACME Corp", "CEO", "+1-555-0101"],
            ["Jane", "Doe", "jane.doe@techstart.com", "TechStart Inc", "CTO", "+1-555-0102"],
            ["Mike", "Johnson", "mike.j@innovate.com", "Innovate LLC", "VP Sales", "+1-555-0103"]
        ]
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerows(csv_data)
            csv_file_path = f.name
        
        try:
            # Upload the CSV file
            with open(csv_file_path, 'rb') as f:
                files = {'file': ('test_leads.csv', f, 'text/csv')}
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                
                response = self.session.post(
                    f"{self.base_url}/leads/bulk-import",
                    files=files,
                    headers=headers,
                    timeout=60
                )
            
            if response.status_code == 200:
                result = response.json()
                if "success" in result and result["success"] > 0:
                    self.log_result("Bulk Import Leads", True, f"Imported {result['success']} leads successfully")
                    return True
                else:
                    self.log_result("Bulk Import Leads", False, f"No leads imported: {result}")
                    return False
            else:
                self.log_result("Bulk Import Leads", False, f"Status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Bulk Import Leads", False, f"Exception: {str(e)}")
            return False
        finally:
            # Clean up temp file
            if os.path.exists(csv_file_path):
                os.unlink(csv_file_path)
    
    def test_website_scraper(self):
        """Test website scraper functionality"""
        print("\n🕷️ Testing Website Scraper...")
        
        if not self.auth_token:
            self.log_result("Website Scraper", False, "No auth token available")
            return False
        
        # Test with a simple website that should have contact info
        scrape_data = {
            "url": "https://example.com"
        }
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            response = self.session.post(
                f"{self.base_url}/leads/scrape",
                json=scrape_data,
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if "message" in result and "contacts_found" in result:
                    self.log_result("Website Scraper", True, f"Scraper executed: {result['message']}")
                    return True
                else:
                    self.log_result("Website Scraper", False, f"Invalid response format: {result}")
                    return False
            else:
                self.log_result("Website Scraper", False, f"Status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Website Scraper", False, f"Exception: {str(e)}")
            return False
    
    def test_stats_endpoint(self):
        """Test stats endpoint"""
        print("\n📊 Testing Stats Endpoint...")
        
        if not self.auth_token:
            self.log_result("Stats Endpoint", False, "No auth token available")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            response = self.session.get(f"{self.base_url}/stats", headers=headers, timeout=30)
            
            if response.status_code == 200:
                stats = response.json()
                required_fields = ["total_leads", "total_users", "total_appointments", "conversion_rate", "pipeline_value"]
                
                if all(field in stats for field in required_fields):
                    self.log_result("Stats Endpoint", True, f"Stats retrieved: {stats['total_leads']} leads, {stats['total_users']} users")
                    return True
                else:
                    self.log_result("Stats Endpoint", False, f"Missing required fields in stats: {stats}")
                    return False
            else:
                self.log_result("Stats Endpoint", False, f"Status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Stats Endpoint", False, f"Exception: {str(e)}")
            return False
    
    def test_ai_insights_endpoint(self):
        """Test AI insights endpoint"""
        print("\n🤖 Testing AI Insights Endpoint...")
        
        if not self.auth_token:
            self.log_result("AI Insights Endpoint", False, "No auth token available")
            return False
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        try:
            response = self.session.get(f"{self.base_url}/insights", headers=headers, timeout=30)
            
            if response.status_code == 200:
                insights = response.json()
                if isinstance(insights, list):
                    self.log_result("AI Insights Endpoint", True, f"Retrieved {len(insights)} AI insights")
                    return True
                else:
                    self.log_result("AI Insights Endpoint", False, f"Invalid response format: {insights}")
                    return False
            else:
                self.log_result("AI Insights Endpoint", False, f"Status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("AI Insights Endpoint", False, f"Exception: {str(e)}")
            return False
    
    def run_additional_tests(self):
        """Run additional backend tests"""
        print("🚀 Starting Additional LeadGen Pro Backend API Testing...")
        print(f"🌐 Backend URL: {self.base_url}")
        print("=" * 60)
        
        # Setup authentication
        if not self.setup_auth():
            print("❌ Failed to setup authentication. Aborting tests.")
            return self.results
        
        # Run additional tests
        self.test_bulk_import_leads()
        self.test_website_scraper()
        self.test_stats_endpoint()
        self.test_ai_insights_endpoint()
        
        # Print final results
        print("\n" + "=" * 60)
        print("🏁 ADDITIONAL TESTING COMPLETE")
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
    tester = AdditionalTester()
    results = tester.run_additional_tests()