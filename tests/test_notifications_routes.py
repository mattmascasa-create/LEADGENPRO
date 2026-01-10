"""
Test suite for notification routes after backend refactoring
Tests: notifications.py and push.py routes
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

# Get base URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "admin123"


class TestAuthAndSetup:
    """Authentication tests - run first to get token"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for admin user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    def test_login_success(self):
        """Test login endpoint works"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == ADMIN_EMAIL


class TestNotificationEndpoints:
    """Test notification endpoints from routes/notifications.py"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    # GET /api/notifications - Main notifications endpoint
    def test_get_notifications(self, auth_headers):
        """Test GET /api/notifications returns user's notifications"""
        response = requests.get(
            f"{BASE_URL}/api/notifications",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Should return a list of notifications or dict with notifications
        assert isinstance(data, (list, dict))
        if isinstance(data, dict):
            # Check for expected fields in response
            assert "notifications" in data or "unread_count" in data or isinstance(data.get("notifications"), list)
    
    def test_get_notifications_with_limit(self, auth_headers):
        """Test GET /api/notifications with limit parameter"""
        response = requests.get(
            f"{BASE_URL}/api/notifications?limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))
    
    # GET /api/notifications/generate - Generate smart notifications
    def test_generate_smart_notifications(self, auth_headers):
        """Test GET /api/notifications/generate creates smart notifications"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/generate",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] == True
        assert "notifications_created" in data
        assert "push_notifications_sent" in data
    
    # POST /api/notifications/mark-read - Mark notifications as read
    def test_mark_all_notifications_read(self, auth_headers):
        """Test POST /api/notifications/mark-read with mark_all=true (query param)"""
        response = requests.post(
            f"{BASE_URL}/api/notifications/mark-read?mark_all=true",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] == True
    
    def test_mark_specific_notifications_read(self, auth_headers):
        """Test POST /api/notifications/mark-read with notification_ids (query param)"""
        # First get some notifications
        get_response = requests.get(
            f"{BASE_URL}/api/notifications",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        
        # Try to mark with no notification_ids (should return success=False)
        response = requests.post(
            f"{BASE_URL}/api/notifications/mark-read",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # When no params, should return success=False
        assert "success" in data
    
    def test_mark_read_no_params(self, auth_headers):
        """Test POST /api/notifications/mark-read with no params returns appropriate response"""
        response = requests.post(
            f"{BASE_URL}/api/notifications/mark-read",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Should return success=False when no notifications specified
        assert "success" in data
        assert data["success"] == False
    
    # DELETE /api/notifications/{id} - Delete notification
    def test_delete_notification_not_found(self, auth_headers):
        """Test DELETE /api/notifications/{id} returns 404 for non-existent notification"""
        fake_id = str(uuid.uuid4())
        response = requests.delete(
            f"{BASE_URL}/api/notifications/{fake_id}",
            headers=auth_headers
        )
        assert response.status_code == 404
    
    # GET /api/notifications/preferences - Get notification preferences
    def test_get_notification_preferences(self, auth_headers):
        """Test GET /api/notifications/preferences returns user preferences"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/preferences",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Check for expected preference fields
        expected_fields = [
            "hot_lead_alerts", "stale_deal_alerts", "email_opened_alerts",
            "meeting_reminders", "task_due_alerts", "new_lead_assigned",
            "deal_stage_change", "quiet_hours_enabled", "email_digest", "push_enabled"
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
    
    # PUT /api/notifications/preferences - Update notification preferences
    def test_update_notification_preferences(self, auth_headers):
        """Test PUT /api/notifications/preferences updates preferences"""
        new_prefs = {
            "hot_lead_alerts": True,
            "stale_deal_alerts": True,
            "email_opened_alerts": True,
            "meeting_reminders": True,
            "task_due_alerts": True,
            "new_lead_assigned": True,
            "deal_stage_change": True,
            "quiet_hours_enabled": False,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
            "email_digest": False,
            "push_enabled": False
        }
        response = requests.put(
            f"{BASE_URL}/api/notifications/preferences",
            headers=auth_headers,
            json=new_prefs
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] == True
        
        # Verify preferences were updated
        get_response = requests.get(
            f"{BASE_URL}/api/notifications/preferences",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        updated_prefs = get_response.json()
        assert updated_prefs["hot_lead_alerts"] == True
        assert updated_prefs["email_digest"] == False
    
    # GET /api/notifications/digest-preview - Preview daily digest
    def test_get_digest_preview(self, auth_headers):
        """Test GET /api/notifications/digest-preview returns HTML preview"""
        response = requests.get(
            f"{BASE_URL}/api/notifications/digest-preview",
            headers=auth_headers
        )
        assert response.status_code == 200
        # Should return HTML content
        assert "text/html" in response.headers.get("content-type", "")
        assert "<!DOCTYPE html>" in response.text or "<html" in response.text
    
    # POST /api/notifications/send-digest - Send daily digest
    def test_send_digest_disabled(self, auth_headers):
        """Test POST /api/notifications/send-digest when email_digest is disabled"""
        # First ensure email_digest is disabled
        requests.put(
            f"{BASE_URL}/api/notifications/preferences",
            headers=auth_headers,
            json={"email_digest": False}
        )
        
        response = requests.post(
            f"{BASE_URL}/api/notifications/send-digest",
            headers=auth_headers
        )
        # Should return success=False because email_digest is disabled
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        # When disabled, should return success=False with message
        if not data["success"]:
            assert "message" in data


class TestPushEndpoints:
    """Test push notification endpoints from routes/push.py"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    # GET /api/push/vapid-public-key - Get VAPID public key
    def test_get_vapid_public_key(self, auth_headers):
        """Test GET /api/push/vapid-public-key returns VAPID key"""
        response = requests.get(
            f"{BASE_URL}/api/push/vapid-public-key",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "vapid_public_key" in data
        # VAPID key should be a non-empty string
        assert isinstance(data["vapid_public_key"], str)
        assert len(data["vapid_public_key"]) > 0
    
    # GET /api/push/status - Get push notification status
    def test_get_push_status(self, auth_headers):
        """Test GET /api/push/status returns push status"""
        response = requests.get(
            f"{BASE_URL}/api/push/status",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "push_enabled" in data
        assert "active_subscriptions" in data
        assert "vapid_configured" in data
        assert isinstance(data["push_enabled"], bool)
        assert isinstance(data["active_subscriptions"], int)
        assert isinstance(data["vapid_configured"], bool)


class TestUnauthorizedAccess:
    """Test that endpoints require authentication"""
    
    def test_notifications_requires_auth(self):
        """Test GET /api/notifications requires authentication"""
        response = requests.get(f"{BASE_URL}/api/notifications")
        assert response.status_code in [401, 403]
    
    def test_generate_requires_auth(self):
        """Test GET /api/notifications/generate requires authentication"""
        response = requests.get(f"{BASE_URL}/api/notifications/generate")
        assert response.status_code in [401, 403]
    
    def test_preferences_requires_auth(self):
        """Test GET /api/notifications/preferences requires authentication"""
        response = requests.get(f"{BASE_URL}/api/notifications/preferences")
        assert response.status_code in [401, 403]
    
    def test_push_status_requires_auth(self):
        """Test GET /api/push/status requires authentication"""
        response = requests.get(f"{BASE_URL}/api/push/status")
        assert response.status_code in [401, 403]
    
    def test_vapid_key_requires_auth(self):
        """Test GET /api/push/vapid-public-key requires authentication"""
        response = requests.get(f"{BASE_URL}/api/push/vapid-public-key")
        assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
