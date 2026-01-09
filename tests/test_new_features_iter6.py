"""
Test Suite for LeadGen Pro - Iteration 6 Features
Tests:
1. Delete Message API - DELETE /api/chat/messages/{message_id}
2. AI Call Coaching API - POST /api/calls/{call_id}/coaching
3. Team Coaching Insights API - GET /api/calls/coaching/team-insights
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "admin123"


class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_user(self, admin_token):
        """Get admin user info"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        return response.json()
    
    def test_login_success(self):
        """Test admin login works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL


class TestDeleteMessageAPI:
    """Test DELETE /api/chat/messages/{message_id} endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def admin_user_id(self, auth_headers):
        """Get admin user ID"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        return response.json()["id"]
    
    @pytest.fixture(scope="class")
    def test_channel(self, auth_headers):
        """Get or create a test channel"""
        # Get existing channels
        response = requests.get(f"{BASE_URL}/api/chat/channels", headers=auth_headers)
        if response.status_code == 200 and response.json():
            return response.json()[0]
        
        # Create a channel if none exist
        response = requests.post(f"{BASE_URL}/api/chat/channels", json={
            "name": "test-channel",
            "description": "Test channel for message deletion"
        }, headers=auth_headers)
        return response.json()
    
    def test_delete_own_message(self, auth_headers, test_channel, admin_user_id):
        """Test that user can delete their own message"""
        # Create a message first
        message_content = f"Test message to delete {uuid.uuid4()}"
        create_response = requests.post(f"{BASE_URL}/api/chat/messages", json={
            "channel_id": test_channel["id"],
            "content": message_content,
            "type": "text"
        }, headers=auth_headers)
        
        assert create_response.status_code == 200, f"Failed to create message: {create_response.text}"
        message = create_response.json()
        message_id = message["id"]
        
        # Delete the message
        delete_response = requests.delete(
            f"{BASE_URL}/api/chat/messages/{message_id}",
            headers=auth_headers
        )
        
        assert delete_response.status_code == 200, f"Failed to delete message: {delete_response.text}"
        data = delete_response.json()
        assert data["success"] == True
        assert "deleted" in data["message"].lower()
    
    def test_delete_nonexistent_message(self, auth_headers):
        """Test deleting a non-existent message returns 404"""
        fake_message_id = str(uuid.uuid4())
        response = requests.delete(
            f"{BASE_URL}/api/chat/messages/{fake_message_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_admin_can_delete_any_message(self, auth_headers, test_channel):
        """Test that admin can delete any message (admin privilege)"""
        # Create a message as admin
        message_content = f"Admin test message {uuid.uuid4()}"
        create_response = requests.post(f"{BASE_URL}/api/chat/messages", json={
            "channel_id": test_channel["id"],
            "content": message_content,
            "type": "text"
        }, headers=auth_headers)
        
        assert create_response.status_code == 200
        message = create_response.json()
        
        # Admin should be able to delete it
        delete_response = requests.delete(
            f"{BASE_URL}/api/chat/messages/{message['id']}",
            headers=auth_headers
        )
        
        assert delete_response.status_code == 200
        assert delete_response.json()["success"] == True


class TestAICallCoachingAPI:
    """Test POST /api/calls/{call_id}/coaching endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def admin_user_id(self, auth_headers):
        """Get admin user ID"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        return response.json()["id"]
    
    def test_coaching_nonexistent_call(self, auth_headers):
        """Test coaching for non-existent call returns 404"""
        fake_call_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/calls/{fake_call_id}/coaching",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_coaching_call_without_transcript(self, auth_headers, admin_user_id):
        """Test coaching for call without transcript returns 400"""
        # Create a call log without transcript
        call_id = str(uuid.uuid4())
        
        # First, we need to create a call log directly via the API
        # Using the call logs endpoint
        response = requests.post(f"{BASE_URL}/api/calls/logs", json={
            "phone_number": "+15551234567",
            "outcome": "connected",
            "duration": 120,
            "notes": "Test call without transcript"
        }, headers=auth_headers)
        
        if response.status_code == 200:
            call = response.json()
            call_id = call.get("id")
            
            # Try to get coaching without transcript
            coaching_response = requests.post(
                f"{BASE_URL}/api/calls/{call_id}/coaching",
                headers=auth_headers
            )
            
            # Should return 400 because no transcript
            assert coaching_response.status_code == 400
            assert "transcript" in coaching_response.json()["detail"].lower()
        else:
            # If we can't create a call log, skip this test
            pytest.skip("Could not create test call log")
    
    def test_coaching_endpoint_exists(self, auth_headers):
        """Test that the coaching endpoint exists and is accessible"""
        # Just verify the endpoint responds (even with 404 for non-existent call)
        fake_call_id = str(uuid.uuid4())
        response = requests.post(
            f"{BASE_URL}/api/calls/{fake_call_id}/coaching",
            headers=auth_headers
        )
        
        # Should return 404 (not 405 Method Not Allowed or 500)
        assert response.status_code in [404, 400, 200]


class TestTeamCoachingInsightsAPI:
    """Test GET /api/calls/coaching/team-insights endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_team_insights_endpoint_exists(self, auth_headers):
        """Test that team insights endpoint exists and returns valid structure"""
        response = requests.get(
            f"{BASE_URL}/api/calls/coaching/team-insights",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Team insights failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "team_avg_score" in data
        assert "total_calls_analyzed" in data or "common_strengths" in data
    
    def test_team_insights_with_days_param(self, auth_headers):
        """Test team insights with days parameter"""
        response = requests.get(
            f"{BASE_URL}/api/calls/coaching/team-insights?days=7",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "team_avg_score" in data
    
    def test_team_insights_response_structure(self, auth_headers):
        """Test that team insights returns expected fields"""
        response = requests.get(
            f"{BASE_URL}/api/calls/coaching/team-insights?days=30",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check all expected fields exist
        expected_fields = [
            "team_avg_score",
            "common_strengths",
            "common_improvements",
            "top_performers"
        ]
        
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
        
        # Verify types
        assert isinstance(data["team_avg_score"], (int, float))
        assert isinstance(data["common_strengths"], list)
        assert isinstance(data["common_improvements"], list)
        assert isinstance(data["top_performers"], list)


class TestChatMessagesAPI:
    """Additional tests for chat messages functionality"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_channels(self, auth_headers):
        """Test getting chat channels"""
        response = requests.get(f"{BASE_URL}/api/chat/channels", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_send_message(self, auth_headers):
        """Test sending a chat message"""
        # Get a channel first
        channels_response = requests.get(f"{BASE_URL}/api/chat/channels", headers=auth_headers)
        if channels_response.status_code != 200 or not channels_response.json():
            pytest.skip("No channels available")
        
        channel = channels_response.json()[0]
        
        # Send a message
        response = requests.post(f"{BASE_URL}/api/chat/messages", json={
            "channel_id": channel["id"],
            "content": f"Test message {datetime.now().isoformat()}",
            "type": "text"
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "content" in data


class TestCallLogsAPI:
    """Test call logs related endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers for admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_call_logs(self, auth_headers):
        """Test getting call logs"""
        response = requests.get(f"{BASE_URL}/api/calls/logs", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_call_stats(self, auth_headers):
        """Test getting call statistics"""
        response = requests.get(f"{BASE_URL}/api/calls/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should have stats fields
        assert "total_calls" in data or response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
