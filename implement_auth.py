#!/usr/bin/env python3
"""
Script to implement authentication (SCRUM-15).
"""
import os
import sys
from pathlib import Path

def create_auth_service():
    """Create authentication service."""
    print("Creating authentication service...")
    
    content = '''"""
Authentication service for user registration and login.
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
from email_validator import validate_email, EmailNotValidError

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Email validation
def validate_email_address(email: str) -> bool:
    """Validate email address format."""
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False

# Password validation
def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password strength.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters"
    
    if len(password) > settings.PASSWORD_MAX_LENGTH:
        return False, f"Password must be at most {settings.PASSWORD_MAX_LENGTH} characters"
    
    # Check for at least one digit
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one digit"
    
    # Check for at least one uppercase letter
    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter"
    
    # Check for at least one lowercase letter
    if not any(char.islower() for char in password):
        return False, "Password must contain at least one lowercase letter"
    
    return True, ""

class AuthService:
    """Authentication service for user management."""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.JWT_SECRET_KEY, 
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """Create JWT refresh token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """Decode and validate JWT token."""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError as e:
            logger.error(f"Token decoding failed: {e}")
            return None
    
    @staticmethod
    def validate_user_credentials(email: str, password: str, user) -> bool:
        """
        Validate user credentials.
        
        Args:
            email: User email
            password: Plain text password
            user: User object from database
            
        Returns:
            True if credentials are valid, False otherwise
        """
        if not user:
            return False
        
        if not user.is_active:
            return False
        
        if not AuthService.verify_password(password, user.password_hash):
            return False
        
        return True
'''
    
    file_path = Path("app/services/auth_service.py")
    file_path.parent.mkdir(exist_ok=True)
    file_path.write_text(content)
    print(f"✅ Created auth service: {file_path}")
    return True

def create_user_schemas():
    """Create user schemas."""
    print("Creating user schemas...")
    
    content = '''"""
User schemas for API requests and responses.
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime

from app.services.auth_service import validate_email_address, validate_password_strength


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, max_length=128)
    
    @validator('email')
    def validate_email_format(cls, v):
        """Validate email format."""
        if not validate_email_address(v):
            raise ValueError('Invalid email format')
        return v.lower()  # Normalize email to lowercase
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        is_valid, error_message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_message)
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)


class UserResponse(UserBase):
    """Schema for user API response."""
    id: int
    is_active: bool
    email_verified: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for authentication tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for token payload data."""
    user_id: Optional[int] = None
    email: Optional[str] = None


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""
    email: EmailStr


class PasswordReset(BaseModel):
    """Schema for password reset."""
    token: str
    new_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength."""
        is_valid, error_message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_message)
        return v


class PasswordChange(BaseModel):
    """Schema for changing password."""
    current_password: str
    new_password: str
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength."""
        is_valid, error_message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(error_message)
        return v
'''
    
    file_path =
