"""
Test suite for Booking System and Admin User Management features
- Booking page public access (no auth) - /book/:userId should load user info
- Booking page available slots - GET /api/booking/{user_id}/slots
- Booking page create booking - POST /api/booking/{user_id}/book
- Admin user management list - GET /api/admin/users requires admin role
- Admin create user - POST /api/admin/users
- Admin update user - PUT /api/admin/users/{user_id}
- Admin delete user - DELETE /api/admin/users/{user_id}
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://leadgen-pro-23.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "admin123"
TEST_USER_ID = "9a23a45f-4d64-44fb-980f-f6e06816c8f4"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def authenticated_client(api_client, admin_token):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {admin_token}"})
    return api_client


class TestBookingPublicAccess:
    """Test public booking page endpoints (no auth required)"""
    
    def test_get_booking_info_valid_user(self, api_client):
        """Test GET /api/booking/{user_id} returns user info"""
        response = api_client.get(f"{BASE_URL}/api/booking/{TEST_USER_ID}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "user" in data
        assert "booked_slots" in data
        
        # Verify user data
        user = data["user"]
        assert user["id"] == TEST_USER_ID
        assert "email" in user
        assert "full_name" in user
        assert "role" in user
        
    def test_get_booking_info_invalid_user(self, api_client):
        """Test GET /api/booking/{user_id} returns 404 for invalid user"""
        invalid_user_id = str(uuid.uuid4())
        response = api_client.get(f"{BASE_URL}/api/booking/{invalid_user_id}")
        
        assert response.status_code == 404
        
    def test_get_available_slots_valid_date(self, api_client):
        """Test GET /api/booking/{user_id}/slots returns available slots"""
        # Use a future date
        future_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        response = api_client.get(
            f"{BASE_URL}/api/booking/{TEST_USER_ID}/slots",
            params={"date": future_date}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "slots" in data
        assert "date" in data
        assert data["date"] == future_date
        
        # Slots should be a list of time strings
        assert isinstance(data["slots"], list)
        if len(data["slots"]) > 0:
            # Verify slot format (HH:MM)
            assert ":" in data["slots"][0]
            
    def test_get_available_slots_invalid_date_format(self, api_client):
        """Test GET /api/booking/{user_id}/slots with invalid date format"""
        response = api_client.get(
            f"{BASE_URL}/api/booking/{TEST_USER_ID}/slots",
            params={"date": "invalid-date"}
        )
        
        assert response.status_code == 400
        
    def test_create_booking_success(self, api_client):
        """Test POST /api/booking/{user_id}/book creates booking"""
        # Use a future date and time
        future_datetime = datetime.now() + timedelta(days=10, hours=10)
        
        booking_data = {
            "name": f"TEST_Booking_{uuid.uuid4().hex[:8]}",
            "email": f"test_booking_{uuid.uuid4().hex[:8]}@example.com",
            "phone": "+1555000000",
            "company": "Test Company",
            "notes": "Test booking notes",
            "datetime": future_datetime.isoformat(),
            "duration": 30
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/booking/{TEST_USER_ID}/book",
            json=booking_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response
        assert data["success"] == True
        assert "event_id" in data
        assert "message" in data
        assert "details" in data
        
        # Verify details
        assert "with" in data["details"]
        assert "datetime" in data["details"]
        assert data["details"]["duration"] == 30
        
    def test_create_booking_missing_required_fields(self, api_client):
        """Test POST /api/booking/{user_id}/book fails without required fields"""
        booking_data = {
            "notes": "Test notes only"
        }
        
        response = api_client.post(
            f"{BASE_URL}/api/booking/{TEST_USER_ID}/book",
            json=booking_data
        )
        
        # Should fail validation
        assert response.status_code == 422


class TestAdminUserManagement:
    """Test admin user management endpoints (requires admin auth)"""
    
    def test_get_users_requires_auth(self, api_client):
        """Test GET /api/admin/users requires authentication"""
        response = api_client.get(f"{BASE_URL}/api/admin/users")
        
        assert response.status_code in [401, 403]
        
    def test_get_users_as_admin(self, authenticated_client):
        """Test GET /api/admin/users returns user list for admin"""
        response = authenticated_client.get(f"{BASE_URL}/api/admin/users")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return a list
        assert isinstance(data, list)
        
        # Each user should have required fields
        if len(data) > 0:
            user = data[0]
            assert "id" in user
            assert "email" in user
            assert "full_name" in user
            assert "role" in user
            # Password should NOT be returned
            assert "password" not in user
            
    def test_create_user_as_admin(self, authenticated_client):
        """Test POST /api/admin/users creates new user"""
        unique_id = uuid.uuid4().hex[:8]
        user_data = {
            "email": f"TEST_newuser_{unique_id}@example.com",
            "password": "testpass123",
            "full_name": f"TEST New User {unique_id}",
            "role": "employee",
            "department": "Sales",
            "phone": "+1555111222",
            "company": "Test Corp"
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/admin/users",
            json=user_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response
        assert data["success"] == True
        assert "user" in data
        assert "message" in data
        
        # Verify user data
        created_user = data["user"]
        assert created_user["email"] == user_data["email"]
        assert created_user["full_name"] == user_data["full_name"]
        assert created_user["role"] == user_data["role"]
        assert created_user["onboarding_completed"] == True  # Admin-created users skip onboarding
        
        # Store user ID for cleanup
        return created_user["id"]
        
    def test_create_user_duplicate_email(self, authenticated_client):
        """Test POST /api/admin/users fails for duplicate email"""
        user_data = {
            "email": ADMIN_EMAIL,  # Already exists
            "password": "testpass123",
            "full_name": "Duplicate User",
            "role": "employee"
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/admin/users",
            json=user_data
        )
        
        assert response.status_code == 400
        assert "already registered" in response.json().get("detail", "").lower()
        
    def test_create_user_invalid_role(self, authenticated_client):
        """Test POST /api/admin/users fails for invalid role"""
        unique_id = uuid.uuid4().hex[:8]
        user_data = {
            "email": f"TEST_invalid_{unique_id}@example.com",
            "password": "testpass123",
            "full_name": "Invalid Role User",
            "role": "superadmin"  # Invalid role
        }
        
        response = authenticated_client.post(
            f"{BASE_URL}/api/admin/users",
            json=user_data
        )
        
        assert response.status_code == 400
        
    def test_update_user_as_admin(self, authenticated_client):
        """Test PUT /api/admin/users/{user_id} updates user"""
        # First create a user to update
        unique_id = uuid.uuid4().hex[:8]
        create_data = {
            "email": f"TEST_update_{unique_id}@example.com",
            "password": "testpass123",
            "full_name": f"TEST Update User {unique_id}",
            "role": "employee",
            "department": "Sales"
        }
        
        create_response = authenticated_client.post(
            f"{BASE_URL}/api/admin/users",
            json=create_data
        )
        assert create_response.status_code == 200
        user_id = create_response.json()["user"]["id"]
        
        # Now update the user
        update_data = {
            "full_name": f"TEST Updated Name {unique_id}",
            "role": "manager",
            "department": "Marketing",
            "phone": "+1555999888"
        }
        
        update_response = authenticated_client.put(
            f"{BASE_URL}/api/admin/users/{user_id}",
            json=update_data
        )
        
        assert update_response.status_code == 200
        updated_user = update_response.json()
        
        # Verify updates
        assert updated_user["full_name"] == update_data["full_name"]
        assert updated_user["role"] == update_data["role"]
        assert updated_user["department"] == update_data["department"]
        assert updated_user["phone"] == update_data["phone"]
        
        # Verify by GET
        get_response = authenticated_client.get(f"{BASE_URL}/api/admin/users")
        users = get_response.json()
        updated = next((u for u in users if u["id"] == user_id), None)
        assert updated is not None
        assert updated["full_name"] == update_data["full_name"]
        
    def test_update_nonexistent_user(self, authenticated_client):
        """Test PUT /api/admin/users/{user_id} returns 404 for invalid user"""
        invalid_user_id = str(uuid.uuid4())
        update_data = {"full_name": "Test Name"}
        
        response = authenticated_client.put(
            f"{BASE_URL}/api/admin/users/{invalid_user_id}",
            json=update_data
        )
        
        assert response.status_code == 404
        
    def test_delete_user_as_admin(self, authenticated_client):
        """Test DELETE /api/admin/users/{user_id} deletes user"""
        # First create a user to delete
        unique_id = uuid.uuid4().hex[:8]
        create_data = {
            "email": f"TEST_delete_{unique_id}@example.com",
            "password": "testpass123",
            "full_name": f"TEST Delete User {unique_id}",
            "role": "employee"
        }
        
        create_response = authenticated_client.post(
            f"{BASE_URL}/api/admin/users",
            json=create_data
        )
        assert create_response.status_code == 200
        user_id = create_response.json()["user"]["id"]
        
        # Delete the user
        delete_response = authenticated_client.delete(
            f"{BASE_URL}/api/admin/users/{user_id}"
        )
        
        assert delete_response.status_code == 200
        assert "deleted" in delete_response.json().get("message", "").lower()
        
        # Verify user is deleted by checking user list
        get_response = authenticated_client.get(f"{BASE_URL}/api/admin/users")
        users = get_response.json()
        deleted_user = next((u for u in users if u["id"] == user_id), None)
        assert deleted_user is None
        
    def test_delete_nonexistent_user(self, authenticated_client):
        """Test DELETE /api/admin/users/{user_id} returns 404 for invalid user"""
        invalid_user_id = str(uuid.uuid4())
        
        response = authenticated_client.delete(
            f"{BASE_URL}/api/admin/users/{invalid_user_id}"
        )
        
        assert response.status_code == 404
        
    def test_cannot_delete_self(self, authenticated_client, admin_token):
        """Test admin cannot delete their own account"""
        # Get current user ID from token
        me_response = authenticated_client.get(f"{BASE_URL}/api/auth/me")
        assert me_response.status_code == 200
        current_user_id = me_response.json()["id"]
        
        # Try to delete self
        response = authenticated_client.delete(
            f"{BASE_URL}/api/admin/users/{current_user_id}"
        )
        
        assert response.status_code == 400
        assert "cannot delete your own" in response.json().get("detail", "").lower()


class TestNonAdminAccess:
    """Test that non-admin users cannot access admin endpoints"""
    
    def test_employee_cannot_access_admin_users(self, api_client):
        """Test employee role cannot access admin user management"""
        # First login as employee (if exists) or skip
        employee_response = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": "employee@test.com",
            "password": "employee123"
        })
        
        if employee_response.status_code != 200:
            pytest.skip("Employee test account not available")
            
        employee_token = employee_response.json()["access_token"]
        
        # Try to access admin users endpoint
        response = api_client.get(
            f"{BASE_URL}/api/admin/users",
            headers={"Authorization": f"Bearer {employee_token}"}
        )
        
        assert response.status_code == 403


class TestBookingLinkGeneration:
    """Test booking link generation endpoint"""
    
    def test_get_booking_link_as_admin(self, authenticated_client):
        """Test GET /api/booking/link/{user_id} returns booking link"""
        response = authenticated_client.get(
            f"{BASE_URL}/api/booking/link/{TEST_USER_ID}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "booking_link" in data
        assert "user_id" in data
        assert data["user_id"] == TEST_USER_ID
        assert "/book/" in data["booking_link"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
