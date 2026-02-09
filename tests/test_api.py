"""
Tests for Mergington High School API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    activities.clear()
    activities.update({
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        }
    })


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_index(self, client):
        """Test that root path redirects to index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_all_activities(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
        
    def test_activity_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_successful_signup(self, client):
        """Test successfully signing up for an activity"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        assert "Signed up newstudent@mergington.edu for Chess Club" in response.json()["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        data = activities_response.json()
        assert "newstudent@mergington.edu" in data["Chess Club"]["participants"]
    
    def test_duplicate_signup(self, client):
        """Test that duplicate signups are prevented"""
        # First signup
        client.post("/activities/Chess%20Club/signup?email=test@mergington.edu")
        
        # Try to signup again
        response = client.post("/activities/Chess%20Club/signup?email=test@mergington.edu")
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"].lower()
    
    def test_signup_nonexistent_activity(self, client):
        """Test signing up for an activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent%20Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_multiple_different_signups(self, client):
        """Test multiple different students can sign up"""
        client.post("/activities/Chess%20Club/signup?email=student1@mergington.edu")
        client.post("/activities/Chess%20Club/signup?email=student2@mergington.edu")
        client.post("/activities/Chess%20Club/signup?email=student3@mergington.edu")
        
        activities_response = client.get("/activities")
        data = activities_response.json()
        participants = data["Chess Club"]["participants"]
        
        assert "student1@mergington.edu" in participants
        assert "student2@mergington.edu" in participants
        assert "student3@mergington.edu" in participants


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/signup endpoint"""
    
    def test_successful_unregister(self, client):
        """Test successfully unregistering from an activity"""
        # First, verify the participant exists
        initial_response = client.get("/activities")
        assert "michael@mergington.edu" in initial_response.json()["Chess Club"]["participants"]
        
        # Unregister
        response = client.delete(
            "/activities/Chess%20Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        assert "Unregistered michael@mergington.edu from Chess Club" in response.json()["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        data = activities_response.json()
        assert "michael@mergington.edu" not in data["Chess Club"]["participants"]
    
    def test_unregister_nonexistent_participant(self, client):
        """Test unregistering a participant who isn't signed up"""
        response = client.delete(
            "/activities/Chess%20Club/signup?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"].lower()
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregistering from an activity that doesn't exist"""
        response = client.delete(
            "/activities/Nonexistent%20Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_then_unregister_then_signup_again(self, client):
        """Test that a student can re-register after unregistering"""
        email = "cycling@mergington.edu"
        
        # Signup
        client.post(f"/activities/Chess%20Club/signup?email={email}")
        
        # Unregister
        client.delete(f"/activities/Chess%20Club/signup?email={email}")
        
        # Signup again
        response = client.post(f"/activities/Chess%20Club/signup?email={email}")
        assert response.status_code == 200
        
        # Verify participant is in the list
        activities_response = client.get("/activities")
        data = activities_response.json()
        assert email in data["Chess Club"]["participants"]


class TestActivityCapacity:
    """Tests for activity capacity management"""
    
    def test_participants_count(self, client):
        """Test that participant count is accurate"""
        activities_response = client.get("/activities")
        data = activities_response.json()
        
        chess_club = data["Chess Club"]
        assert len(chess_club["participants"]) <= chess_club["max_participants"]
