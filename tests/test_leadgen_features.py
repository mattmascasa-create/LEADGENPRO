"""
LeadGen Pro Feature Tests - Iteration 5
Testing: Admin Lead Visibility, Quick Call Dialer, Call Disposition API, Bulk Lead Operations
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://sales-automation-22.preview.emergentagent.com')

# Test credentials
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "admin123"

class TestAuthAndSetup:
    """Authentication and setup tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
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
    
    def test_admin_login(self, admin_token):
        """Test admin can login successfully"""
        assert admin_token is not None
        assert len(admin_token) > 0
        print(f"✓ Admin login successful, token length: {len(admin_token)}")
    
    def test_admin_user_info(self, admin_user):
        """Test admin user info is correct"""
        assert admin_user["email"] == ADMIN_EMAIL
        print(f"✓ Admin user: {admin_user['email']}, role: {admin_user.get('role')}")


class TestAdminLeadVisibility:
    """Test that admin can see ALL leads regardless of who created them"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_admin_can_get_all_leads(self, admin_token):
        """Admin should see ALL leads - no filtering by created_by or assigned_to"""
        response = requests.get(f"{BASE_URL}/api/leads", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Failed to get leads: {response.text}"
        leads = response.json()
        print(f"✓ Admin can see {len(leads)} leads")
        # Admin should see leads (could be 0 if no leads exist, but endpoint works)
        assert isinstance(leads, list)
    
    def test_admin_create_lead(self, admin_token):
        """Admin can create a lead"""
        unique_id = str(uuid.uuid4())[:8]
        lead_data = {
            "first_name": f"TEST_Admin_{unique_id}",
            "last_name": "Created",
            "email": f"test_admin_{unique_id}@example.com",
            "company": "Test Company",
            "phone": "555-0100"
        }
        response = requests.post(f"{BASE_URL}/api/leads", json=lead_data, headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Failed to create lead: {response.text}"
        created_lead = response.json()
        assert created_lead["first_name"] == lead_data["first_name"]
        print(f"✓ Admin created lead: {created_lead['id']}")
        return created_lead["id"]
    
    def test_admin_can_see_created_lead(self, admin_token):
        """Admin can see the lead they just created"""
        # First create a lead
        unique_id = str(uuid.uuid4())[:8]
        lead_data = {
            "first_name": f"TEST_Visible_{unique_id}",
            "last_name": "Lead",
            "email": f"test_visible_{unique_id}@example.com",
            "company": "Visible Corp"
        }
        create_response = requests.post(f"{BASE_URL}/api/leads", json=lead_data, headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert create_response.status_code == 200
        created_lead = create_response.json()
        lead_id = created_lead["id"]
        
        # Now get all leads and verify the created lead is visible
        response = requests.get(f"{BASE_URL}/api/leads", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        leads = response.json()
        lead_ids = [l["id"] for l in leads]
        assert lead_id in lead_ids, f"Created lead {lead_id} not visible to admin"
        print(f"✓ Admin can see created lead {lead_id} in leads list")


class TestCallDispositionAPI:
    """Test the call disposition endpoint POST /api/calls/{call_id}/disposition"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_get_disposition_options(self, admin_token):
        """Test getting available disposition options"""
        response = requests.get(f"{BASE_URL}/api/calls/dispositions", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Failed to get dispositions: {response.text}"
        dispositions = response.json()
        assert isinstance(dispositions, list)
        assert len(dispositions) > 0
        expected_dispositions = ["No Answer", "Left Voicemail", "Set Meeting", "Not Interested"]
        for expected in expected_dispositions:
            assert expected in dispositions, f"Missing disposition: {expected}"
        print(f"✓ Got {len(dispositions)} disposition options: {dispositions[:5]}...")
    
    def test_update_disposition_nonexistent_call(self, admin_token):
        """Test updating disposition for non-existent call returns 404"""
        fake_call_id = "nonexistent-call-id-12345"
        response = requests.put(
            f"{BASE_URL}/api/calls/{fake_call_id}/disposition",
            params={"disposition": "No Answer"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Should return 404 for non-existent call
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print(f"✓ Non-existent call returns 404 as expected")
    
    def test_create_call_log_and_update_disposition(self, admin_token):
        """Test creating a call log and then updating its disposition"""
        # First create a call log
        call_log_data = {
            "phone_number": "+15550001234",
            "outcome": "connected",
            "duration": 120,
            "notes": "Test call for disposition"
        }
        create_response = requests.post(
            f"{BASE_URL}/api/calls/log",
            json=call_log_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert create_response.status_code == 200, f"Failed to create call log: {create_response.text}"
        call_log = create_response.json()
        call_id = call_log["id"]
        print(f"✓ Created call log: {call_id}")
        
        # Now update the disposition
        disposition_response = requests.put(
            f"{BASE_URL}/api/calls/{call_id}/disposition",
            params={"disposition": "Set Meeting", "notes": "Scheduled follow-up meeting"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert disposition_response.status_code == 200, f"Failed to update disposition: {disposition_response.text}"
        result = disposition_response.json()
        assert result["disposition"] == "Set Meeting"
        print(f"✓ Updated disposition to 'Set Meeting' for call {call_id}")


class TestBulkLeadOperations:
    """Test bulk lead assignment and sequence operations"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def test_leads(self, admin_token):
        """Create test leads for bulk operations"""
        lead_ids = []
        for i in range(3):
            unique_id = str(uuid.uuid4())[:8]
            lead_data = {
                "first_name": f"TEST_Bulk_{unique_id}",
                "last_name": f"Lead{i}",
                "email": f"test_bulk_{unique_id}@example.com",
                "company": "Bulk Test Corp"
            }
            response = requests.post(f"{BASE_URL}/api/leads", json=lead_data, headers={
                "Authorization": f"Bearer {admin_token}"
            })
            if response.status_code == 200:
                lead_ids.append(response.json()["id"])
        return lead_ids
    
    @pytest.fixture(scope="class")
    def admin_user_id(self, admin_token):
        """Get admin user ID for assignment"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200
        return response.json()["id"]
    
    def test_bulk_assign_leads(self, admin_token, test_leads, admin_user_id):
        """Test POST /api/leads/bulk-assign - assign multiple leads to a user"""
        if len(test_leads) == 0:
            pytest.skip("No test leads created")
        
        response = requests.post(
            f"{BASE_URL}/api/leads/bulk-assign",
            json={
                "lead_ids": test_leads,
                "user_id": admin_user_id
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Bulk assign failed: {response.text}"
        result = response.json()
        assert "success" in result
        assert result["success"] > 0
        print(f"✓ Bulk assigned {result['success']} leads to user {admin_user_id}")
    
    def test_bulk_assign_invalid_user(self, admin_token, test_leads):
        """Test bulk assign with invalid user ID returns 404"""
        if len(test_leads) == 0:
            pytest.skip("No test leads created")
        
        response = requests.post(
            f"{BASE_URL}/api/leads/bulk-assign",
            json={
                "lead_ids": test_leads[:1],
                "user_id": "nonexistent-user-id"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Bulk assign with invalid user returns 404")
    
    def test_get_sequences(self, admin_token):
        """Test getting available sequences"""
        response = requests.get(f"{BASE_URL}/api/sequences", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Failed to get sequences: {response.text}"
        sequences = response.json()
        print(f"✓ Got {len(sequences)} sequences")
        return sequences
    
    def test_create_sequence_and_bulk_add(self, admin_token, test_leads):
        """Test creating a sequence and adding leads to it"""
        if len(test_leads) == 0:
            pytest.skip("No test leads created")
        
        # Create a test sequence
        unique_id = str(uuid.uuid4())[:8]
        sequence_data = {
            "name": f"TEST_Sequence_{unique_id}",
            "description": "Test sequence for bulk operations",
            "steps": [
                {"type": "email", "delay_days": 0, "subject": "Welcome", "body": "Hello!"},
                {"type": "email", "delay_days": 3, "subject": "Follow up", "body": "Following up..."}
            ]
        }
        create_response = requests.post(
            f"{BASE_URL}/api/sequences",
            json=sequence_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert create_response.status_code == 200, f"Failed to create sequence: {create_response.text}"
        sequence = create_response.json()
        sequence_id = sequence["id"]
        print(f"✓ Created sequence: {sequence_id}")
        
        # Now bulk add leads to sequence
        bulk_response = requests.post(
            f"{BASE_URL}/api/leads/bulk-sequence",
            json={
                "lead_ids": test_leads,
                "sequence_id": sequence_id
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert bulk_response.status_code == 200, f"Bulk sequence add failed: {bulk_response.text}"
        result = bulk_response.json()
        assert "success" in result
        print(f"✓ Added {result['success']} leads to sequence {sequence_id}")
    
    def test_bulk_sequence_invalid_sequence(self, admin_token, test_leads):
        """Test bulk sequence add with invalid sequence ID returns 404"""
        if len(test_leads) == 0:
            pytest.skip("No test leads created")
        
        response = requests.post(
            f"{BASE_URL}/api/leads/bulk-sequence",
            json={
                "lead_ids": test_leads[:1],
                "sequence_id": "nonexistent-sequence-id"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Bulk sequence with invalid sequence returns 404")


class TestUsersEndpoint:
    """Test users endpoint for admin"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_admin_can_get_users(self, admin_token):
        """Admin should be able to get list of users"""
        response = requests.get(f"{BASE_URL}/api/users", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert response.status_code == 200, f"Failed to get users: {response.text}"
        users = response.json()
        assert isinstance(users, list)
        print(f"✓ Admin can see {len(users)} users")
        # Verify admin user is in the list
        admin_emails = [u["email"] for u in users]
        assert ADMIN_EMAIL in admin_emails, "Admin user not in users list"


class TestCleanup:
    """Cleanup test data"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_cleanup_test_leads(self, admin_token):
        """Clean up TEST_ prefixed leads"""
        response = requests.get(f"{BASE_URL}/api/leads", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        if response.status_code == 200:
            leads = response.json()
            deleted = 0
            for lead in leads:
                if lead.get("first_name", "").startswith("TEST_"):
                    del_response = requests.delete(
                        f"{BASE_URL}/api/leads/{lead['id']}",
                        headers={"Authorization": f"Bearer {admin_token}"}
                    )
                    if del_response.status_code == 200:
                        deleted += 1
            print(f"✓ Cleaned up {deleted} test leads")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
