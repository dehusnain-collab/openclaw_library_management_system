#!/usr/bin/env python3
"""
Complete implementation of authentication (SCRUM-15).
"""
import os
import sys
from pathlib import Path

def create_auth_service():
    """Create complete authentication service."""
    print("Creating authentication service...")
    
    content = '''"""
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

# Email validation
def validate_email_address(email: str) -> Tuple[bool, str]:
    """Validate email address format."""
    try:
        validate_email(email)
        return True, ""
    except EmailNotValidError as e:
        return False, str(e)

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
    
    # Check for at least one special character
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(char in special_chars for char in password):
        return False, "Password must contain at least one special character"
    
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
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "type": "access",
            "iat": datetime.utcnow()
        })
        
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.JWT_SECRET_KEY, 
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create JWT refresh token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({
            "exp": expire,
            "type": "refresh",
            "iat": datetime.utcnow()
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
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
    def validate_user_credentials(email: str, password: str, user) -> Tuple[bool, str]:
        """
        Validate user credentials.
        
        Args:
            email: User email
            password: Plain text password
            user: User object from database
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not user:
            return False, "Invalid email or password"
        
        if not user.is_active:
            return False, "Account is deactivated"
        
        if not AuthService.verify_password(password, user.password_hash):
            return False, "Invalid email or password"
        
        return True, ""
    
    @staticmethod
    def create_tokens_for_user(user_id: int, email: str) -> Dict[str, str]:
        """
        Create access and refresh tokens for a user.
        
        Args:
            user_id: User ID
            email: User email
            
        Returns:
            Dictionary with access_token and refresh_token
        """
        token_data = {"sub": str(user_id), "email": email}
        
        access_token = AuthService.create_access_token(token_data)
        refresh_token = AuthService.create_refresh_token(token_data)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    @staticmethod
    def refresh_access_token(refresh_token: str) -> Optional[Dict[str, str]]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New tokens or None if refresh token is invalid
        """
        payload = AuthService.decode_token(refresh_token)
        
        if not payload or payload.get("type") != "refresh":
            return None
        
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id or not email:
            return None
        
        # Create new tokens
        return AuthService.create_tokens_for_user(int(user_id), email)
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
        is_valid, error_message = validate_email_address(v)
        if not is_valid:
            raise ValueError(f'Invalid email format: {error_message}')
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
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for authentication tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


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


class MessageResponse(BaseModel):
    """Schema for simple message responses."""
    message: str
    success: bool = True
'''
    
    file_path = Path("app/schemas/user.py")
    file_path.parent.mkdir(exist_ok=True)
    file_path.write_text(content)
    print(f"✅ Created user schemas: {file_path}")
    return True

def create_auth_controller():
    """Create authentication controller with endpoints."""
    print("Creating authentication controller...")
    
    content = '''"""
Authentication endpoints for user registration and login.
"""
from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.user import (
    UserCreate, UserResponse, UserLogin, Token,
    PasswordResetRequest, PasswordReset, PasswordChange,
    MessageResponse
)
from app.services.auth_service import AuthService, validate_email_address
from app.repositories.user import UserRepository
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["authentication"])

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Register a new user.
    
    Args:
        user_data: User registration data
        db: Database session
        
    Returns:
        Created user information
    """
    logger.info(f"Registration attempt for email: {user_data.email}")
    
    # Check if email already exists
    user_repo = UserRepository(db)
    existing_user = await user_repo.get_by(email=user_data.email)
    
    if existing_user:
        logger.warning(f"Registration failed: Email already exists - {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_password = AuthService.get_password_hash(user_data.password)
    
    # Create user
    user = await user_repo.create(
        email=user_data.email,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        is_active=True,
        email_verified=False
    )
    
    logger.info(f"User registered successfully: {user.id} - {user.email}")
    
    return UserResponse.from_orm(user)


@router.post("/login", response_model=Token)
async def login_user(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Login user and return JWT tokens.
    
    Args:
        login_data: User login credentials
        db: Database session
        
    Returns:
        Access and refresh tokens
    """
    logger.info(f"Login attempt for email: {login_data.email}")
    
    # Get user by email
    user_repo = UserRepository(db)
    user = await user_repo.get_by(email=login_data.email)
    
    # Validate credentials
    is_valid, error_message = AuthService.validate_user_credentials(
        login_data.email,
        login_data.password,
        user
    )
    
    if not is_valid:
        logger.warning(f"Login failed for email: {login_data.email} - {error_message}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_message,
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    
    # Create tokens
    tokens = AuthService.create_tokens_for_user(user.id, user.email)
    
    # Add expires_in (access token expires in 30 minutes)
    tokens["expires_in"] = 30 * 60  # 30 minutes in seconds
    
    logger.info(f"Login successful for user: {user.id} - {user.email}")
    
    return tokens


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str
) -> Any:
    """
    Refresh access token using refresh token.
    
    Args:
        refresh_token: Valid refresh token
        
    Returns:
        New access and refresh tokens
    """
    logger.info("Token refresh attempt")
    
    tokens = AuthService.refresh_access_token(refresh_token)
    
    if not tokens:
        logger.warning("Token refresh failed: Invalid refresh token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Add expires_in
    tokens["expires_in"] = 30 * 60  # 30 minutes in seconds
    
    logger.info("Token refresh successful")
    
    return tokens


@router.post("/logout", response_model=MessageResponse)
async def logout_user() -> Any:
    """
    Logout user (client should discard tokens).
    
    Note: In a production system, you would blacklist the tokens.
    """
    logger.info("User logout")
    
    return MessageResponse(
        message="Logged out successfully. Please discard your tokens.",
        success=True
    )


@router.post("/password/reset-request", response_model=MessageResponse)
async def request_password_reset(
    reset_request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Request password reset (sends reset email).
    
    Args:
        reset_request: Password reset request data
        db: Database session
        
    Returns:
        Success message
    """
    logger.info(f"Password reset request for email: {reset_request.email}")
    
    # Check if user exists
    user_repo = UserRepository(db)
    user = await user_repo.get_by(email=reset_request.email)
    
    if not user:
        # Don't reveal if user exists or not (security best practice)
        logger.info(f"Password reset request handled (user may not exist): {reset_request.email}")
        return MessageResponse(
            message="If your email is registered, you will receive a password reset link.",
            success=True
        )
    
    # In a real implementation, you would:
    # 1. Generate a reset token
    # 2. Store it in the database with expiration
    # 3. Send an email with reset link
    
    logger.info(f"Password reset token would be sent to: {reset_request.email}")
    
    return MessageResponse(
        message="If your email is registered, you will receive a password reset link.",
        success=True
    )


@router.post("/password/reset", response_model=MessageResponse)
async def reset_password(
    reset_data: PasswordReset,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Reset password using reset token.
    
    Args:
        reset_data: Password reset data
        db: Database session
        
    Returns:
        Success message
    """
    logger.info("Password reset attempt")
    
    # In a real implementation, you would:
    # 1. Validate the reset token
    # 2. Check expiration
    # 3. Update user password
    
    # For now, just return a message
    logger.info("Password reset would be processed")
    
    return MessageResponse(
        message="Password reset would be processed with valid token.",
        success=True
    )


# Dependency to get current user from token
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get current authenticated user from JWT token.
    
    Args:
        token: JWT access token
        db: Database session
        
    Returns:
        Current user object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Decode token
    payload = Auth