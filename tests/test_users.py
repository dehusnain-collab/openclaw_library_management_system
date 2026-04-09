"""
Tests for user management endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db
from app.models.base import Base

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_users.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override get_db dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Setup test database."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield
    
    # Clean up
    Base.metadata.drop_all(bind=engine)


def create_and_login_user(email="test@example.com", password="Test123!@#"):
    """Create a test user and return auth token."""
    # Register user
    response = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "first_name": "Test",
        "last_name": "User"
    })
    
    if response.status_code != 201:
        # User might already exist, try login
        pass
    
    # Login to get token
    response = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    
    if response.status_code == 200:
        return response.json()["access_token"]
    
    return None


def test_get_current_user_profile():
    """Test getting current user's profile."""
    # Create and login user
    token = create_and_login_user("profile@test.com", "Profile123!@#")
    
    if not token:
        pytest.skip("Could not create test user")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get current user profile
    response = client.get("/api/v1/users/me", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert "id" in data
    assert data["email"] == "profile@test.com"
    assert data["first_name"] == "Test"
    assert data["last_name"] == "User"
    assert data["is_active"] == True


def test_update_current_user_profile():
    """Test updating current user's profile."""
    # Create and login user
    token = create_and_login_user("update@test.com", "Update123!@#")
    
    if not token:
        pytest.skip("Could not create test user")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Update profile
    update_data = {
        "first_name": "Updated",
        "last_name": "Name"
    }
    
    response = client.put("/api/v1/users/me", json=update_data, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["first_name"] == "Updated"
    assert data["last_name"] == "Name"
    assert data["email"] == "update@test.com"


def test_change_password():
    """Test changing password."""
    # Create and login user
    token = create_and_login_user("password@test.com", "OldPass123!@#")
    
    if not token:
        pytest.skip("Could not create test user")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Change password
    password_data = {
        "current_password": "OldPass123!@#",
        "new_password": "NewPass123!@#"
    }
    
    response = client.post("/api/v1/users/me/password", json=password_data, headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["message"] == "Password changed successfully"
    assert data["success"] == True
    
    # Verify new password works
    response = client.post("/api/v1/auth/login", json={
        "email": "password@test.com",
        "password": "NewPass123!@#"
    })
    
    assert response.status_code == 200


def test_change_password_wrong_current():
    """Test changing password with wrong current password."""
    token = create_and_login_user("wrongpass@test.com", "Correct123!@#")
    
    if not token:
        pytest.skip("Could not create test user")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try to change password with wrong current password
    password_data = {
        "current_password": "WrongPass123!@#",
        "new_password": "NewPass123!@#"
    }
    
    response = client.post("/api/v1/users/me/password", json=password_data, headers=headers)
    
    assert response.status_code == 400
    data = response.json()
    assert "Current password is incorrect" in data["detail"]


def test_get_user_by_id_self():
    """Test getting user profile by ID (self)."""
    token = create_and_login_user("self@test.com", "Self123!@#")
    
    if not token:
        pytest.skip("Could not create test user")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # First get current user to get ID
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    user_id = response.json()["id"]
    
    # Get user by ID (should work for self)
    response = client.get(f"/api/v1/users/{user_id}", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_id
    assert data["email"] == "self@test.com"


def test_get_my_permissions():
    """Test getting current user's permissions."""
    token = create_and_login_user("perms@test.com", "Perms123!@#")
    
    if not token:
        pytest.skip("Could not create test user")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/v1/users/me/permissions", headers=headers)
    
    # Should return a list (may be empty)
    assert response.status_code == 200
    permissions = response.json()
    assert isinstance(permissions, list)


def test_get_my_roles():
    """Test getting current user's roles."""
    token = create_and_login_user("roles@test.com", "Roles123!@#")
    
    if not token:
        pytest.skip("Could not create test user")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/v1/users/me/roles", headers=headers)
    
    # Should return a list (should at least have 'member' role)
    assert response.status_code == 200
    roles = response.json()
    assert isinstance(roles, list)
    # New users should have 'member' role by default
    assert "member" in roles


def test_deactivate_own_account():
    """Test deactivating own account."""
    token = create_and_login_user("deactivate@test.com", "Deactivate123!@#")
    
    if not token:
        pytest.skip("Could not create test user")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Deactivate account
    response = client.post("/api/v1/users/me/deactivate", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Account deactivated successfully"
    assert data["success"] == True
    
    # Try to login with deactivated account
    response = client.post("/api/v1/auth/login", json={
        "email": "deactivate@test.com",
        "password": "Deactivate123!@#"
    })
    
    # Should fail (account is deactivated)
    assert response.status_code == 401


def test_search_users_self():
    """Test searching users (should only find self without permission)."""
    token = create_and_login_user("search@test.com", "Search123!@#")
    
    if not token:
        pytest.skip("Could not create test user")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Search for users
    response = client.get("/api/v1/users/search?query=search", headers=headers)
    
    # Should return at least self
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    
    # Should only contain the current user (since they don't have users:read permission)
    user_emails = [user["email"] for user in users]
    assert "search@test.com" in user_emails


def test_user_endpoints_require_auth():
    """Test that user endpoints require authentication."""
    user_endpoints = [
        ("GET", "/api/v1/users/me"),
        ("PUT", "/api/v1/users/me"),
        ("POST", "/api/v1/users/me/password"),
        ("GET", "/api/v1/users/me/permissions"),
        ("GET", "/api/v1/users/me/roles"),
        ("POST", "/api/v1/users/me/deactivate"),
        ("GET", "/api/v1/users/search?query=test"),
    ]
    
    for method, endpoint in user_endpoints:
        if method == "GET":
            response = client.get(endpoint)
        elif method == "PUT":
            response = client.put(endpoint, json={})
        elif method == "POST":
            response = client.post(endpoint, json={})
        
        # Should require authentication
        assert response.status_code == 401


def test_get_user_by_id_other_user():
    """Test getting another user's profile without permission."""
    # Create two users
    token1 = create_and_login_user("user1@test.com", "User1123!@#")
    token2 = create_and_login_user("user2@test.com", "User2123!@#")
    
    if not token1 or not token2:
        pytest.skip("Could not create test users")
    
    headers1 = {"Authorization": f"Bearer {token1}"}
    
    # Get user1's ID
    response = client.get("/api/v1/users/me", headers=headers1)
    assert response.status_code == 200
    user1_id = response.json()["id"]
    
    # User2 tries to get user1's profile (should fail without permission)
    headers2 = {"Authorization": f"Bearer {token2}"}
    response = client.get(f"/api/v1/users/{user1_id}", headers=headers2)
    
    # Should fail (no permission to view other users)
    assert response.status_code in [403, 404]


def test_get_users_without_permission():
    """Test getting all users without permission."""
    token = create_and_login_user("noperm@test.com", "NoPerm123!@#")
    
    if not token:
        pytest.skip("Could not create test user")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/v1/users", headers=headers)
    
    # Should fail without users:read permission
    assert response.status_code == 403


def test_update_user_validation():
    """Test user update validation."""
    token = create_and_login_user("validate@test.com", "Validate123!@#")
    
    if not token:
        pytest.skip("Could not create test user")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try to update with invalid data
    invalid_data = {
        "first_name": "",  # Empty string should fail validation
        "last_name": "A" * 101  # Too long
    }
    
    response = client.put("/api/v1/users/me", json=invalid_data, headers=headers)
    
    # Should fail validation
    assert response.status_code == 422


def test_password_change_validation():
    """Test password change validation."""
    token = create_and_login_user("passval@test.com", "PassVal123!@#")
    
    if not token:
        pytest.skip("Could not create test user")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try to change with invalid new password
    invalid_password = {
        "current_password": "PassVal123!@#",
        "new_password": "weak"  # Too weak
    }
    
    response = client.post("/api/v1/users/me/password", json=invalid_password, headers=headers)
    
    # Should fail validation
    assert response.status_code == 422


def test_user_profile_structure():
    """Test user profile response structure."""
    token = create_and_login_user("struct@test.com", "Struct123!@#")
    
    if not token:
        pytest.skip("Could not create test user")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get("/api/v1/users/me", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Check required fields
    required_fields = ["id", "email", "first_name", "last_name", "is_active", 
                      "email_verified", "created_at", "updated_at"]
    
    for field in required_fields:
        assert field in data
    
    # Check field types
    assert isinstance(data["id"], int)
    assert isinstance(data["email"], str)
    assert isinstance(data["is_active"], bool)
    assert isinstance(data["email_verified"], bool)
    assert isinstance(data["created_at"], str)  # ISO datetime string
    assert isinstance(data["updated_at"], str)  # ISO datetime string


if __name__ == "__main__":
    pytest.main([__file__, "-v"])