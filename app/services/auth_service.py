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
