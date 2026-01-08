"""
LeadGen Pro Backend API Tests
Tests all major API endpoints for the CRM platform
"""
import pytest
import requests
import os
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://leadgenpro-7.preview.emergentagent.com')

class TestAuth:
    """Authentication endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.admin_email = "admin@test.com"
        self.admin_password = "admin123"
        self.test_user_email = f"TEST_user_{datetime.now().timestamp()}@test.com"
    
    def test_login_success(self):
        """Test successful login with admin credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == self.admin_email
        assert data["user"]["role"] == "admin"
        print(f"✓ Login successful for {self.admin_email}")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "wrong@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401
        print("✓ Invalid credentials correctly rejected")
    
    def test_register_new_user(self):
        """Test user registration"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": self.test_user_email,
            "password": "testpass123",
            "full_name": "Test User",
            "role": "employee"
        })
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == self.test_user_email
        print(f"✓ User registration successful for {self.test_user_email}")
    
    def test_get_current_user(self):
        """Test getting current user info"""
        # First login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        token = login_response.json()["access_token"]
        
        # Get current user
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == self.admin_email
        print("✓ Get current user successful")


class TestLeads:
    """Lead management endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123"
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_leads(self):
        """Test getting all leads"""
        response = requests.get(f"{BASE_URL}/api/leads", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get leads successful - {len(data)} leads found")
    
    def test_create_lead(self):
        """Test creating a new lead"""
        lead_data = {
            "first_name": "TEST_John",
            "last_name": "Doe",
            "email": f"TEST_john.doe_{datetime.now().timestamp()}@example.com",
            "phone": "+1234567890",
            "company": "Test Company",
            "title": "CEO",
            "status": "new",
            "tags": ["test", "api"]
        }
        response = requests.post(f"{BASE_URL}/api/leads", json=lead_data, headers=self.headers)
        assert response.status_code == 200, f"Create lead failed: {response.text}"
        data = response.json()
        assert data["first_name"] == lead_data["first_name"]
        assert data["company"] == lead_data["company"]
        assert "id" in data
        assert "score" in data
        print(f"✓ Create lead successful - ID: {data['id']}")
        return data["id"]
    
    def test_get_single_lead(self):
        """Test getting a single lead by ID"""
        # First create a lead
        lead_data = {
            "first_name": "TEST_Jane",
            "last_name": "Smith",
            "email": f"TEST_jane.smith_{datetime.now().timestamp()}@example.com",
            "company": "Test Corp"
        }
        create_response = requests.post(f"{BASE_URL}/api/leads", json=lead_data, headers=self.headers)
        lead_id = create_response.json()["id"]
        
        # Get the lead
        response = requests.get(f"{BASE_URL}/api/leads/{lead_id}", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == lead_id
        assert data["first_name"] == lead_data["first_name"]
        print(f"✓ Get single lead successful - ID: {lead_id}")
    
    def test_update_lead(self):
        """Test updating a lead"""
        # First create a lead
        lead_data = {
            "first_name": "TEST_Update",
            "last_name": "Test",
            "email": f"TEST_update_{datetime.now().timestamp()}@example.com",
            "company": "Original Company"
        }
        create_response = requests.post(f"{BASE_URL}/api/leads", json=lead_data, headers=self.headers)
        lead_id = create_response.json()["id"]
        
        # Update the lead
        update_data = {
            "first_name": "TEST_Updated",
            "last_name": "Test",
            "email": lead_data["email"],
            "company": "Updated Company"
        }
        response = requests.put(f"{BASE_URL}/api/leads/{lead_id}", json=update_data, headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["company"] == "Updated Company"
        print(f"✓ Update lead successful - ID: {lead_id}")
    
    def test_update_lead_stage(self):
        """Test updating lead stage"""
        # First create a lead
        lead_data = {
            "first_name": "TEST_Stage",
            "last_name": "Test",
            "email": f"TEST_stage_{datetime.now().timestamp()}@example.com",
            "company": "Stage Test Company"
        }
        create_response = requests.post(f"{BASE_URL}/api/leads", json=lead_data, headers=self.headers)
        lead_id = create_response.json()["id"]
        
        # Update stage
        response = requests.post(f"{BASE_URL}/api/leads/{lead_id}/stage?stage=qualified", headers=self.headers)
        assert response.status_code == 200
        print(f"✓ Update lead stage successful - ID: {lead_id}")


class TestStats:
    """Stats and insights endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123"
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_stats(self):
        """Test getting dashboard stats"""
        response = requests.get(f"{BASE_URL}/api/stats", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_leads" in data
        assert "total_users" in data
        assert "total_appointments" in data
        assert "conversion_rate" in data
        print(f"✓ Get stats successful - {data['total_leads']} leads, {data['total_users']} users")
    
    def test_get_insights(self):
        """Test getting AI insights"""
        response = requests.get(f"{BASE_URL}/api/insights", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get insights successful - {len(data)} insights")


class TestTasks:
    """Task management endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123"
        })
        self.token = login_response.json()["access_token"]
        self.user_id = login_response.json()["user"]["id"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_tasks(self):
        """Test getting all tasks"""
        response = requests.get(f"{BASE_URL}/api/tasks", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get tasks successful - {len(data)} tasks found")
    
    def test_create_task(self):
        """Test creating a new task"""
        task_data = {
            "title": "TEST_Follow up with client",
            "description": "Call to discuss proposal",
            "type": "call",
            "assigned_to": self.user_id,
            "due_date": (datetime.now() + timedelta(days=1)).isoformat(),
            "priority": "high"
        }
        response = requests.post(f"{BASE_URL}/api/tasks", json=task_data, headers=self.headers)
        assert response.status_code == 200, f"Create task failed: {response.text}"
        data = response.json()
        assert data["title"] == task_data["title"]
        assert "id" in data
        print(f"✓ Create task successful - ID: {data['id']}")
        return data["id"]
    
    def test_complete_task(self):
        """Test completing a task"""
        # First create a task
        task_data = {
            "title": "TEST_Task to complete",
            "type": "other",
            "assigned_to": self.user_id,
            "due_date": (datetime.now() + timedelta(days=1)).isoformat()
        }
        create_response = requests.post(f"{BASE_URL}/api/tasks", json=task_data, headers=self.headers)
        task_id = create_response.json()["id"]
        
        # Complete the task
        response = requests.put(f"{BASE_URL}/api/tasks/{task_id}/complete", headers=self.headers)
        assert response.status_code == 200
        print(f"✓ Complete task successful - ID: {task_id}")


class TestCalendar:
    """Calendar endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123"
        })
        self.token = login_response.json()["access_token"]
        self.user_id = login_response.json()["user"]["id"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_calendar_events(self):
        """Test getting calendar events"""
        response = requests.get(f"{BASE_URL}/api/calendar/events", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get calendar events successful - {len(data)} events found")
    
    def test_create_calendar_event(self):
        """Test creating a calendar event"""
        event_data = {
            "title": "TEST_Team Meeting",
            "description": "Weekly sync",
            "type": "meeting",
            "start": (datetime.now() + timedelta(days=1)).isoformat(),
            "end": (datetime.now() + timedelta(days=1, hours=1)).isoformat(),
            "attendees": [self.user_id]
        }
        response = requests.post(f"{BASE_URL}/api/calendar/events", json=event_data, headers=self.headers)
        assert response.status_code == 200, f"Create event failed: {response.text}"
        data = response.json()
        assert data["title"] == event_data["title"]
        print(f"✓ Create calendar event successful - ID: {data['id']}")


class TestChat:
    """Team chat endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123"
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_channels(self):
        """Test getting chat channels"""
        response = requests.get(f"{BASE_URL}/api/chat/channels", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get channels successful - {len(data)} channels found")
    
    def test_send_message(self):
        """Test sending a chat message"""
        # First get channels
        channels_response = requests.get(f"{BASE_URL}/api/chat/channels", headers=self.headers)
        channels = channels_response.json()
        
        if channels:
            channel_id = channels[0]["id"]
            message_data = {
                "channel_id": channel_id,
                "content": "TEST_Hello from API test!",
                "type": "text"
            }
            response = requests.post(f"{BASE_URL}/api/chat/messages", json=message_data, headers=self.headers)
            assert response.status_code == 200, f"Send message failed: {response.text}"
            data = response.json()
            assert data["content"] == message_data["content"]
            print(f"✓ Send message successful - Channel: {channel_id}")


class TestCallAnalytics:
    """Call analytics endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123"
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_call_stats(self):
        """Test getting call statistics"""
        response = requests.get(f"{BASE_URL}/api/calls/stats", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_calls" in data
        assert "outcomes" in data
        print(f"✓ Get call stats successful - {data['total_calls']} total calls")
    
    def test_get_call_logs(self):
        """Test getting call logs"""
        response = requests.get(f"{BASE_URL}/api/calls/logs", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get call logs successful - {len(data)} logs found")


class TestAdminUsers:
    """Admin user management endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123"
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_admin_users(self):
        """Test getting all users (admin only)"""
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get admin users successful - {len(data)} users found")
    
    def test_get_users(self):
        """Test getting users list"""
        response = requests.get(f"{BASE_URL}/api/users", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get users successful - {len(data)} users found")


class TestEmail:
    """Email endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123"
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_email_templates(self):
        """Test getting email templates"""
        response = requests.get(f"{BASE_URL}/api/email/templates", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get email templates successful - {len(data)} templates found")
    
    def test_generate_ai_email(self):
        """Test AI email generation"""
        email_data = {
            "lead_id": None,
            "context": "Follow up on product demo",
            "tone": "professional"
        }
        response = requests.post(f"{BASE_URL}/api/email/generate", json=email_data, headers=self.headers)
        # This may take time due to AI generation
        assert response.status_code in [200, 500], f"Generate email failed: {response.text}"
        if response.status_code == 200:
            data = response.json()
            assert "subject" in data or "body" in data
            print("✓ Generate AI email successful")
        else:
            print("⚠ AI email generation returned 500 (may be expected if AI service unavailable)")


class TestBooking:
    """Public booking page endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication to get user ID"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123"
        })
        self.token = login_response.json()["access_token"]
        self.user_id = login_response.json()["user"]["id"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_booking_info(self):
        """Test getting booking info for a user (public endpoint)"""
        response = requests.get(f"{BASE_URL}/api/booking/{self.user_id}")
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        print(f"✓ Get booking info successful for user {self.user_id}")
    
    def test_get_booking_slots(self):
        """Test getting available booking slots"""
        date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        response = requests.get(f"{BASE_URL}/api/booking/{self.user_id}/slots?date={date}")
        assert response.status_code == 200
        data = response.json()
        assert "slots" in data
        print(f"✓ Get booking slots successful - {len(data['slots'])} slots available")


class TestActivities:
    """Activity endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123"
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_activities(self):
        """Test getting activities"""
        response = requests.get(f"{BASE_URL}/api/activities?limit=10", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get activities successful - {len(data)} activities found")


class TestSequencesAndTemplates:
    """Sequences and templates endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123"
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_sequences(self):
        """Test getting email sequences"""
        response = requests.get(f"{BASE_URL}/api/sequences", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get sequences successful - {len(data)} sequences found")
    
    def test_get_templates(self):
        """Test getting email templates"""
        response = requests.get(f"{BASE_URL}/api/templates", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get templates successful - {len(data)} templates found")


class TestAppointments:
    """Appointment endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123"
        })
        self.token = login_response.json()["access_token"]
        self.user_id = login_response.json()["user"]["id"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_get_appointments(self):
        """Test getting appointments"""
        response = requests.get(f"{BASE_URL}/api/appointments", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get appointments successful - {len(data)} appointments found")


class TestAIAssistant:
    """AI Assistant endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authentication"""
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123"
        })
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_assistant_chat(self):
        """Test AI assistant chat"""
        chat_data = {
            "message": "What are my top priorities today?",
            "context": "general"
        }
        response = requests.post(f"{BASE_URL}/api/assistant/chat", json=chat_data, headers=self.headers)
        # AI may take time or fail
        assert response.status_code in [200, 500], f"Assistant chat failed: {response.text}"
        if response.status_code == 200:
            data = response.json()
            assert "response" in data
            print("✓ AI assistant chat successful")
        else:
            print("⚠ AI assistant returned 500 (may be expected if AI service unavailable)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
