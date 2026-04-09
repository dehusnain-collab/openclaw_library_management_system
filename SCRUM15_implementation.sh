#!/bin/bash

# Implementation script for SCRUM-15: User Registration & Login

echo "============================================================"
echo "Implementing SCRUM-15: User Registration & Login"
echo "============================================================"

# Create feature branch
echo ""
echo "🌿 Creating feature branch..."
git checkout -b feature/SCRUM-15-user-registration-login

echo "✅ Created branch: feature/SCRUM-15-user-registration-login"

# Create auth service
echo ""
echo "🔧 Creating authentication service..."
mkdir -p app/services

cat > app/services/auth_service.py << 'EOF'
"""
Authentication service for user registration and login.
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from email_validator import validate_email, EmailNotValidError

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def validate_email_address(email: str) -> Tuple[bool, str]:
    """Validate email address format."""
    try:
        validate_email(email)
        return True, ""
    except EmailNotValidError as e:
        return False, str(e)

def validate_password_strength(password: str) -> Tuple[bool, str]:
    """Validate password strength."""
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters"
    
    if len(password) > settings.PASSWORD_MAX_LENGTH:
        return False, f"Password must be at most {settings.PASSWORD_MAX_LENGTH} characters"
    
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one digit"
    
    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(char.islower() for char in password):
        return False, "Password must contain at least one lowercase letter"
    
    return True, ""

class AuthService:
    """Authentication service."""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: Dict[str, Any]) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        try:
            return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        except JWTError as e:
            logger.error(f"Token decoding failed: {e}")
            return None
    
    @staticmethod
    def create_tokens_for_user(user_id: int, email: str) -> Dict[str, str]:
        token_data = {"sub": str(user_id), "email": email}
        return {
            "access_token": AuthService.create_access_token(token_data),
            "refresh_token": AuthService.create_refresh_token(token_data),
            "token_type": "bearer"
        }
EOF

echo "✅ Created app/services/auth_service.py"

# Create user schemas
echo ""
echo "📝 Creating user schemas..."
mkdir -p app/schemas

cat > app/schemas/user.py << 'EOF'
"""
User schemas for API requests and responses.
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime

from app.services.auth_service import validate_email_address, validate_password_strength

class UserBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    
    @validator('email')
    def validate_email_format(cls, v):
        is_valid, error_message = validate_email_address(v)
        if not is_valid:
            raise ValueError(f'Invalid email: {error_message}')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        is_valid, error_message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_message)
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    email_verified: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class MessageResponse(BaseModel):
    message: str
    success: bool = True
EOF

echo "✅ Created app/schemas/user.py"

# Create user repository
echo ""
echo "🗄️ Creating user repository..."
mkdir -p app/repositories

cat > app/repositories/user.py << 'EOF'
"""
User repository for data access.
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.repositories.base import BaseRepository
from app.models.user import User

class UserRepository(BaseRepository[User]):
    """User repository with user-specific queries."""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(User, db_session)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        query = select(User).where(User.email == email)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()
    
    async def email_exists(self, email: str) -> bool:
        """Check if email already exists."""
        query = select(User).where(User.email == email)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def get_active_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get active users with pagination."""
        query = select(User).where(User.is_active == True).offset(skip).limit(limit)
        result = await self.db_session.execute(query)
        return result.scalars().all()
EOF

echo "✅ Created app/repositories/user.py"

# Create auth controller
echo ""
echo "🚀 Creating authentication controller..."

cat > app/controllers/auth.py << 'EOF'
"""
Authentication endpoints.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.user import UserCreate, UserResponse, UserLogin, Token, MessageResponse
from app.services.auth_service import AuthService
from app.repositories.user import UserRepository

router = APIRouter(tags=["authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    # Check if email exists
    user_repo = UserRepository(db)
    if await user_repo.email_exists(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password and create user
    hashed_password = AuthService.get_password_hash(user_data.password)
    user = await user_repo.create(
        email=user_data.email,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        is_active=True,
        email_verified=False
    )
    
    return UserResponse.from_orm(user)

@router.post("/login", response_model=Token)
async def login_user(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login user and return JWT tokens."""
    # Get user
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(login_data.email)
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Verify password
    if not AuthService.verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()
    
    # Create tokens
    return AuthService.create_tokens_for_user(user.id, user.email)

@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    """Refresh access token."""
    payload = AuthService.decode_token(refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    email = payload.get("email")
    
    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    return AuthService.create_tokens_for_user(int(user_id), email)

@router.post("/logout", response_model=MessageResponse)
async def logout_user():
    """Logout user."""
    return MessageResponse(message="Logged out successfully")
EOF

echo "✅ Created app/controllers/auth.py"

# Update main router to include auth
echo ""
echo "🔗 Updating main router..."

cat > app/controllers/__init__.py << 'EOF'
"""
API routers for the Library Management System.
"""
from fastapi import APIRouter

# Create main router
router = APIRouter()

# Import and include all route modules
from app.controllers.health import router as health_router
from app.controllers.auth import router as auth_router

# Include routers
router.include_router(health_router)
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])

# Root endpoint
@router.get("/")
async def root():
    return {
        "message": "Welcome to OpenClaw Library Management System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "auth": {
            "register": "/api/v1/auth/register",
            "login": "/api/v1/auth/login",
            "refresh": "/api/v1/auth/refresh",
            "logout": "/api/v1/auth/logout"
        }
    }
EOF

echo "✅ Updated app/controllers/__init__.py"

# Update requirements.txt with auth dependencies
echo ""
echo "📦 Updating dependencies..."

cat >> requirements.txt << 'EOF'

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
email-validator==2.1.0
EOF

echo "✅ Updated requirements.txt"

# Create tests
echo ""
echo "🧪 Creating tests..."
mkdir -p tests

cat > tests/test_auth.py << 'EOF'
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
EOF

echo "✅ Created tests/test_auth.py"

# Update README with auth documentation
echo ""
echo "📚 Updating documentation..."

cat >> README.md << 'EOF'

## 🔐 Authentication API

### Registration
```bash
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

### Login
```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!"
}

# Response
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

### Refresh Token
```bash
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Logout
```bash
POST /api/v1/auth/logout
```

## Password Requirements
- Minimum 8 characters
- Maximum 128 characters
- At least one digit (0-9)
- At least one uppercase letter (A-Z)
- At least one lowercase letter (a-z)

## JWT Configuration
- Access token: 30 minutes expiration
- Refresh token: 7 days expiration
- Algorithm: