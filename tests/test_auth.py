"""
Tests for authentication endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db
from app.models.base import Base

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
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

@pytest.fixture(scope="module")
def setup_database():
    """Setup test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_register_user(setup_database):
    """Test user registration."""
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "Test123!@#",
        "first_name": "Test",
        "last_name": "User"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["first_name"] == "Test"
    assert data["last_name"] == "User"
    assert "id" in data

def test_register_duplicate_email(setup_database):
    """Test duplicate email registration."""
    # First registration
    client.post("/api/v1/auth/register", json={
        "email": "duplicate@example.com",
        "password": "Test123!@#"
    })
    
    # Second registration with same email
    response = client.post("/api/v1/auth/register", json={
        "email": "duplicate@example.com",
        "password": "Test123!@#"
    })
    
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]

def test_login_success(setup_database):
    """Test successful login."""
    # Register user
    client.post("/api/v1/auth/register", json={
        "email": "login@example.com",
        "password": "Test123!@#"
    })
    
    # Login
    response = client.post("/api/v1/auth/login", json={
        "email": "login@example.com",
        "password": "Test123!@#"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(setup_database):
    """Test login with invalid credentials."""
    response = client.post("/api/v1/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "WrongPassword123!"
    })
    
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]

def test_refresh_token(setup_database):
    """Test token refresh."""
    # Register and login
    client.post("/api/v1/auth/register", json={
        "email": "refresh@example.com",
        "password": "Test123!@#"
    })
    
    login_response = client.post("/api/v1/auth/login", json={
        "email": "refresh@example.com",
        "password": "Test123!@#"
    })
    
    refresh_token = login_response.json()["refresh_token"]
    
    # Refresh token
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

def test_logout(setup_database):
    """Test logout."""
    response = client.post("/api/v1/auth/logout")
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Logged out successfully"
    assert data["success"] == True
