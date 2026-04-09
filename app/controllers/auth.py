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
