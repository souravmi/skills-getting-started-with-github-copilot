"""
Comprehensive test suite for Mergington High School Activities API
Tests for GET activities, POST signup, and DELETE unregister endpoints
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all available activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data

    def test_get_activities_structure(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)

    def test_get_activities_participant_count(self, client):
        """Test that initial participant counts are correct"""
        response = client.get("/activities")
        data = response.json()
        
        assert len(data["Chess Club"]["participants"]) == 2
        assert len(data["Programming Class"]["participants"]) == 2
        assert len(data["Gym Class"]["participants"]) == 2


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_successful(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        assert "newstudent@mergington.edu" in data["message"]

    def test_signup_adds_participant_to_activity(self, client):
        """Test that signup actually adds the participant"""
        client.post("/activities/Chess Club/signup?email=alice@mergington.edu")
        
        response = client.get("/activities")
        data = response.json()
        assert "alice@mergington.edu" in data["Chess Club"]["participants"]

    def test_signup_duplicate_email_rejected(self, client):
        """Test that duplicate signup is rejected"""
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"].lower()

    def test_signup_nonexistent_activity(self, client):
        """Test signup fails for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_signup_activity_full(self, client):
        """Test that signup fails when activity is at capacity"""
        # Chess Club has max_participants=12, currently 2, so add 10 more
        for i in range(10):
            client.post(
                f"/activities/Chess Club/signup?email=student{i}@mergington.edu"
            )
        
        # 11th signup should fail (12 total capacity reached)
        response = client.post(
            "/activities/Chess Club/signup?email=student11@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "full" in data["detail"].lower()

    def test_signup_email_encoding(self, client):
        """Test signup with URL-encoded email"""
        response = client.post(
            "/activities/Programming%20Class/signup?email=bob%40mergington.edu"
        )
        assert response.status_code == 200
        
        response = client.get("/activities")
        data = response.json()
        assert "bob@mergington.edu" in data["Programming Class"]["participants"]


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/signup/{email} endpoint"""

    def test_unregister_successful(self, client):
        """Test successful unregister from an activity"""
        response = client.delete(
            "/activities/Chess Club/signup/michael@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]

    def test_unregister_removes_participant(self, client):
        """Test that unregister actually removes the participant"""
        client.delete("/activities/Chess Club/signup/michael@mergington.edu")
        
        response = client.get("/activities")
        data = response.json()
        assert "michael@mergington.edu" not in data["Chess Club"]["participants"]

    def test_unregister_nonexistent_activity(self, client):
        """Test unregister fails for non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent Club/signup/student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_unregister_student_not_registered(self, client):
        """Test unregister fails if student is not registered"""
        response = client.delete(
            "/activities/Chess Club/signup/unregistered@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"].lower()

    def test_unregister_email_encoding(self, client):
        """Test unregister with URL-encoded email"""
        response = client.delete(
            "/activities/Programming%20Class/signup/emma%40mergington.edu"
        )
        assert response.status_code == 200
        
        response = client.get("/activities")
        data = response.json()
        assert "emma@mergington.edu" not in data["Programming Class"]["participants"]


class TestIntegrationWorkflows:
    """Integration tests for complete workflows"""

    def test_signup_and_unregister_workflow(self, client):
        """Test complete workflow: signup then unregister"""
        # Sign up
        response = client.post(
            "/activities/Chess Club/signup?email=workflow@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify added
        response = client.get("/activities")
        assert "workflow@mergington.edu" in response.json()["Chess Club"]["participants"]
        
        # Unregister
        response = client.delete(
            "/activities/Chess Club/signup/workflow@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify removed
        response = client.get("/activities")
        assert "workflow@mergington.edu" not in response.json()["Chess Club"]["participants"]

    def test_multiple_signups_and_capacity(self, client):
        """Test multiple signups respecting capacity limits"""
        activity = "Programming Class"
        max_participants = 20
        
        # Get current participants
        response = client.get("/activities")
        current = len(response.json()[activity]["participants"])
        
        # Sign up students to fill the activity
        for i in range(max_participants - current):
            response = client.post(
                f"/activities/{activity}/signup?email=prog{i}@mergington.edu"
            )
            assert response.status_code == 200
        
        # Verify at capacity
        response = client.get("/activities")
        assert len(response.json()[activity]["participants"]) == max_participants
        
        # Verify next signup fails
        response = client.post(
            f"/activities/{activity}/signup?email=overflow@mergington.edu"
        )
        assert response.status_code == 400
        assert "full" in response.json()["detail"].lower()

    def test_signup_after_unregister_frees_spot(self, client):
        """Test that unregistering frees up a spot for new signup"""
        activity = "Chess Club"
        
        # Fill to capacity
        for i in range(10):
            client.post(
                f"/activities/{activity}/signup?email=fill{i}@mergington.edu"
            )
        
        # Verify full
        response = client.post(
            f"/activities/{activity}/signup?email=overflow@mergington.edu"
        )
        assert response.status_code == 400
        
        # Unregister someone
        client.delete(f"/activities/{activity}/signup/fill0@mergington.edu")
        
        # Verify new signup succeeds
        response = client.post(
            f"/activities/{activity}/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
