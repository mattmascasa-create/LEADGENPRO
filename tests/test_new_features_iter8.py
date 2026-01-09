"""
Test suite for LeadGen Pro - Iteration 8
Testing new features:
1. Email Tracking Stats API
2. Email Sequences API
3. Pipeline Forecasting API
4. Deal Analysis API
"""

import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://leadgen-pro-24.preview.emergentagent.com')

class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@test.com", "password": "admin123"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        return data["access_token"]
    
    def test_login_success(self):
        """Test successful login"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@test.com", "password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == "admin@test.com"


class TestEmailTrackingStats:
    """Email Tracking Stats API tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@test.com", "password": "admin123"}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_email_tracking_stats(self, auth_headers):
        """Test GET /api/email/tracking/stats returns proper structure"""
        response = requests.get(
            f"{BASE_URL}/api/email/tracking/stats",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "summary" in data
        assert "daily_breakdown" in data
        assert "recent_emails" in data
        
        # Verify summary fields
        summary = data["summary"]
        assert "total_sent" in summary
        assert "total_opened" in summary
        assert "total_clicked" in summary
        assert "total_replied" in summary
        assert "open_rate" in summary
        assert "click_rate" in summary
        assert "reply_rate" in summary
        
        # Verify types
        assert isinstance(summary["total_sent"], int)
        assert isinstance(summary["open_rate"], (int, float))
        
    def test_get_email_tracking_stats_with_days_param(self, auth_headers):
        """Test GET /api/email/tracking/stats with days parameter"""
        response = requests.get(
            f"{BASE_URL}/api/email/tracking/stats?days=7",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        
    def test_get_email_tracking_stats_with_90_days(self, auth_headers):
        """Test GET /api/email/tracking/stats with 90 days"""
        response = requests.get(
            f"{BASE_URL}/api/email/tracking/stats?days=90",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data


class TestEmailSequences:
    """Email Sequences API tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@test.com", "password": "admin123"}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_sequences(self, auth_headers):
        """Test GET /api/sequences returns list"""
        response = requests.get(
            f"{BASE_URL}/api/sequences",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Should return a list
        assert isinstance(data, list)
        
        # If sequences exist, verify structure
        if len(data) > 0:
            seq = data[0]
            # Check for expected fields
            assert "id" in seq or "name" in seq


class TestPipelineForecasting:
    """Pipeline Forecasting API tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@test.com", "password": "admin123"}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_pipeline_forecast(self, auth_headers):
        """Test GET /api/forecasting/pipeline returns proper structure"""
        response = requests.get(
            f"{BASE_URL}/api/forecasting/pipeline",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "summary" in data
        assert "stage_distribution" in data
        assert "top_deals" in data
        assert "at_risk_deals" in data
        
        # Verify summary fields
        summary = data["summary"]
        assert "total_pipeline" in summary
        assert "weighted_pipeline" in summary
        assert "monthly_forecast" in summary
        assert "quarterly_forecast" in summary
        assert "total_deals" in summary
        assert "avg_deal_size" in summary
        assert "avg_probability" in summary
        
        # Verify types
        assert isinstance(summary["total_pipeline"], (int, float))
        assert isinstance(summary["weighted_pipeline"], (int, float))
        assert isinstance(summary["total_deals"], int)
        
        # Verify stage_distribution is a list
        assert isinstance(data["stage_distribution"], list)
        
        # Verify top_deals is a list
        assert isinstance(data["top_deals"], list)
        
        # If top_deals exist, verify structure
        if len(data["top_deals"]) > 0:
            deal = data["top_deals"][0]
            assert "lead_id" in deal
            assert "lead_name" in deal
            assert "deal_value" in deal
            assert "stage" in deal
            assert "probability" in deal


class TestDealAnalysis:
    """Deal Analysis API tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@test.com", "password": "admin123"}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def test_lead_id(self, auth_headers):
        """Get a lead ID for testing"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            headers=auth_headers
        )
        if response.status_code == 200:
            leads = response.json()
            if len(leads) > 0:
                return leads[0]["id"]
        return None
    
    def test_analyze_deal_with_valid_lead(self, auth_headers, test_lead_id):
        """Test POST /api/forecasting/analyze-deal/{lead_id}"""
        if not test_lead_id:
            pytest.skip("No leads available for testing")
        
        response = requests.post(
            f"{BASE_URL}/api/forecasting/analyze-deal/{test_lead_id}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "lead" in data
        assert "analysis" in data
        
        # Verify analysis fields
        analysis = data["analysis"]
        assert "close_probability" in analysis
        assert "engagement_score" in analysis
        assert "confidence_factors" in analysis
        assert "risk_factors" in analysis
        assert "activity_count" in analysis
        assert "call_count" in analysis
        assert "email_count" in analysis
        assert "recommendation" in analysis
        
        # Verify types
        assert isinstance(analysis["close_probability"], (int, float))
        assert isinstance(analysis["engagement_score"], int)
        assert isinstance(analysis["confidence_factors"], list)
        assert isinstance(analysis["risk_factors"], list)
    
    def test_analyze_deal_with_invalid_lead(self, auth_headers):
        """Test POST /api/forecasting/analyze-deal with invalid lead ID"""
        response = requests.post(
            f"{BASE_URL}/api/forecasting/analyze-deal/invalid-lead-id-12345",
            headers=auth_headers
        )
        assert response.status_code == 404


class TestLeadsAPI:
    """Leads API tests - verify leads exist for forecasting"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@test.com", "password": "admin123"}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_leads(self, auth_headers):
        """Test GET /api/leads returns list"""
        response = requests.get(
            f"{BASE_URL}/api/leads",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"Total leads: {len(data)}")
        
        # Check if any leads have deal_value set
        leads_with_deal_value = [l for l in data if l.get("deal_value")]
        print(f"Leads with deal_value: {len(leads_with_deal_value)}")


class TestHealthCheck:
    """Basic health check tests"""
    
    def test_api_accessible(self):
        """Test that API is accessible"""
        response = requests.get(f"{BASE_URL}/api/stats")
        # Should return 401 (unauthorized) or 200 - either means API is up
        assert response.status_code in [200, 401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
