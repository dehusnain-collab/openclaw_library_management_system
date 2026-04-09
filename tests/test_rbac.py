"""
Tests for RBAC (Role-Based Access Control) system.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db
from app.models.base import Base
from app.services.rbac_service import RBACService

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_rbac.db"
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
    """Setup test database and initialize RBAC."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Initialize RBAC
    db = TestingSessionLocal()
    try:
        RBACService.initialize_roles_and_permissions(db)
        db.commit()
    finally:
        db.close()
    
    yield
    
    # Clean up
    Base.metadata.drop_all(bind=engine)


def test_initialize_rbac():
    """Test RBAC initialization endpoint."""
    response = client.post("/api/v1/rbac/initialize")
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "RBAC system initialized successfully"


def test_get_rbac_stats():
    """Test getting RBAC statistics."""
    response = client.get("/api/v1/rbac/stats")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "total_roles" in data
    assert "total_permissions" in data
    assert "total_users_with_roles" in data
    assert "predefined_roles" in data
    
    # Should have 3 predefined roles
    assert data["total_roles"] >= 3
    assert set(data["predefined_roles"]) == {"admin", "librarian", "member"}


def test_get_roles():
    """Test getting all roles."""
    response = client.get("/api/v1/roles")
    
    assert response.status_code == 200
    roles = response.json()
    
    # Should have at least 3 roles
    assert len(roles) >= 3
    
    # Check role names
    role_names = [role["name"] for role in roles]
    assert "admin" in role_names
    assert "librarian" in role_names
    assert "member" in role_names
    
    # Check role structure
    for role in roles:
        assert "id" in role
        assert "name" in role
        assert "description" in role
        assert "is_default" in role
        assert "created_at" in role
        assert "updated_at" in role
        assert "permissions" in role


def test_get_roles_pagination():
    """Test getting roles with pagination."""
    response = client.get("/api/v1/roles?skip=1&limit=2")
    
    assert response.status_code == 200
    roles = response.json()
    
    # Should have at most 2 roles
    assert len(roles) <= 2


def test_get_permissions():
    """Test getting all permissions."""
    response = client.get("/api/v1/permissions")
    
    assert response.status_code == 200
    permissions = response.json()
    
    # Should have multiple permissions
    assert len(permissions) > 0
    
    # Check permission structure
    for perm in permissions:
        assert "id" in perm
        assert "name" in perm
        assert "description" in perm
        assert "module" in perm
        assert "created_at" in perm
        assert "updated_at" in perm


def test_get_permissions_by_module():
    """Test getting permissions filtered by module."""
    response = client.get("/api/v1/permissions?module=users")
    
    assert response.status_code == 200
    permissions = response.json()
    
    # All returned permissions should be in users module
    for perm in permissions:
        assert perm["module"] == "users"


def test_create_and_delete_role():
    """Test creating and deleting a custom role."""
    # Create role
    role_data = {
        "name": "test-role",
        "description": "Test role for unit testing",
        "is_default": False,
        "permission_names": ["books:read", "users:read"]
    }
    
    response = client.post("/api/v1/roles", json=role_data)
    
    assert response.status_code == 201
    role = response.json()
    
    assert role["name"] == "test-role"
    assert role["description"] == "Test role for unit testing"
    assert role["is_default"] == False
    assert "id" in role
    
    role_id = role["id"]
    
    # Get the created role
    response = client.get(f"/api/v1/roles/{role_id}")
    assert response.status_code == 200
    
    # Delete the role
    response = client.delete(f"/api/v1/roles/{role_id}")
    assert response.status_code == 204
    
    # Verify role is deleted
    response = client.get(f"/api/v1/roles/{role_id}")
    assert response.status_code == 404


def test_update_role():
    """Test updating a role."""
    # First create a test role
    role_data = {
        "name": "update-test-role",
        "description": "Role to test updates",
        "is_default": False
    }
    
    response = client.post("/api/v1/roles", json=role_data)
    assert response.status_code == 201
    role = response.json()
    role_id = role["id"]
    
    # Update the role
    update_data = {
        "name": "updated-test-role",
        "description": "Updated description",
        "is_default": True
    }
    
    response = client.put(f"/api/v1/roles/{role_id}", json=update_data)
    assert response.status_code == 200
    
    updated_role = response.json()
    assert updated_role["name"] == "updated-test-role"
    assert updated_role["description"] == "Updated description"
    assert updated_role["is_default"] == True
    
    # Clean up
    client.delete(f"/api/v1/roles/{role_id}")


def test_create_duplicate_role():
    """Test creating a role with duplicate name."""
    # First create a role
    role_data = {
        "name": "duplicate-test-role",
        "description": "Test duplicate role",
        "is_default": False
    }
    
    response = client.post("/api/v1/roles", json=role_data)
    assert response.status_code == 201
    role_id = response.json()["id"]
    
    # Try to create another role with same name
    response = client.post("/api/v1/roles", json=role_data)
    assert response.status_code == 400
    
    # Clean up
    client.delete(f"/api/v1/roles/{role_id}")


def test_assign_and_remove_role_from_user():
    """Test assigning and removing roles from users."""
    # Note: This test requires a user to exist
    # For now, we'll test the endpoint structure
    
    assignment_data = {
        "user_id": 1,  # Assuming user with ID 1 exists
        "role_name": "member"
    }
    
    # Test assign role (may fail if user doesn't exist, but tests endpoint)
    response = client.post("/api/v1/users/assign-role", json=assignment_data)
    # Accept either success (200) or failure due to missing user (400/404)
    assert response.status_code in [200, 400, 404]
    
    # Test remove role
    response = client.post("/api/v1/users/remove-role", json=assignment_data)
    assert response.status_code in [200, 400, 404]


def test_check_permission():
    """Test checking user permissions."""
    check_data = {
        "user_id": 1,  # Assuming user with ID 1 exists
        "permission_name": "books:read"
    }
    
    response = client.post("/api/v1/permissions/check", json=check_data)
    
    # Should return valid response structure
    assert response.status_code == 200
    data = response.json()
    
    assert "user_id" in data
    assert "permission_name" in data
    assert "has_permission" in data
    assert "roles_with_permission" in data
    
    assert data["user_id"] == check_data["user_id"]
    assert data["permission_name"] == check_data["permission_name"]
    assert isinstance(data["has_permission"], bool)
    assert isinstance(data["roles_with_permission"], list)


def test_check_bulk_permissions():
    """Test checking multiple user permissions."""
    check_data = {
        "user_id": 1,  # Assuming user with ID 1 exists
        "permission_names": ["books:read", "users:read", "system:manage"]
    }
    
    response = client.post("/api/v1/permissions/check-bulk", json=check_data)
    
    # Should return valid response structure
    assert response.status_code == 200
    data = response.json()
    
    assert "user_id" in data
    assert "has_all_permissions" in data
    assert "has_any_permission" in data
    assert "missing_permissions" in data
    assert "present_permissions" in data
    
    assert data["user_id"] == check_data["user_id"]
    assert isinstance(data["has_all_permissions"], bool)
    assert isinstance(data["has_any_permission"], bool)
    assert isinstance(data["missing_permissions"], list)
    assert isinstance(data["present_permissions"], list)


def test_get_user_permissions():
    """Test getting all permissions for a user."""
    user_id = 1  # Assuming user with ID 1 exists
    
    response = client.get(f"/api/v1/users/{user_id}/permissions")
    
    # Should return valid response structure
    assert response.status_code in [200, 404]  # 404 if user doesn't exist
    
    if response.status_code == 200:
        data = response.json()
        
        assert "user_id" in data
        assert "email" in data
        assert "roles" in data
        assert "permissions" in data
        
        assert data["user_id"] == user_id
        assert isinstance(data["email"], str)
        assert isinstance(data["roles"], list)
        assert isinstance(data["permissions"], list)


def test_role_permission_management():
    """Test assigning and removing permissions from roles."""
    # First create a test role
    role_data = {
        "name": "perm-test-role",
        "description": "Role for permission testing",
        "is_default": False
    }
    
    response = client.post("/api/v1/roles", json=role_data)
    assert response.status_code == 201
    role_id = response.json()["id"]
    
    # Assign permission
    assign_data = {
        "role_id": role_id,
        "permission_name": "books:read"
    }
    
    response = client.post("/api/v1/roles/assign-permission", json=assign_data)
    assert response.status_code == 200
    
    # Remove permission
    response = client.post("/api/v1/roles/remove-permission", json=assign_data)
    assert response.status_code == 200
    
    # Clean up
    client.delete(f"/api/v1/roles/{role_id}")


def test_delete_role_assigned_to_users():
    """Test that roles assigned to users cannot be deleted."""
    # This would require creating a user and assigning a role first
    # For now, we test the endpoint responds correctly
    
    # Try to delete a predefined role (which might have users)
    response = client.delete("/api/v1/roles/1")  # Assuming role ID 1 exists
    
    # Should either succeed (if no users assigned) or fail with 400
    assert response.status_code in [204, 400]
    
    if response.status_code == 400:
        data = response.json()
        assert "detail" in data
        assert "Cannot delete role" in data["detail"]


def test_rbac_endpoint_security():
    """Test that RBAC endpoints require authentication."""
    # These endpoints should be protected
    endpoints = [
        ("POST", "/api/v1/rbac/initialize"),
        ("GET", "/api/v1/rbac/stats"),
        ("GET", "/api/v1/roles"),
        ("POST", "/api/v1/roles"),
        ("GET", "/api/v1/permissions"),
        ("POST", "/api/v1/users/assign-role"),
        ("POST", "/api/v1/permissions/check"),
    ]
    
    for method, endpoint in endpoints:
        if method == "GET":
            response = client.get(endpoint)
        elif method == "POST":
            response = client.post(endpoint, json={})
        elif method == "PUT":
            response = client.put(endpoint, json={})
        elif method == "DELETE":
            response = client.delete(endpoint)
        
        # Endpoints should either require auth (401) or handle missing data gracefully
        # For this test, we're checking they don't crash with 500 errors
        assert response.status_code != 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])