#!/bin/bash

# Setup GitHub repository and complete workflow for Library Management System

echo "============================================================"
echo "OpenClaw Library Management System - GitHub Setup"
echo "============================================================"

# Check git status
echo ""
echo "📊 Checking git status..."
if ! git status &> /dev/null; then
    echo "❌ Not in a git repository or git not available"
    exit 1
fi
echo "✅ Git repository ready"

# Create GitHub setup instructions
echo ""
echo "📋 Creating GitHub setup instructions..."
cat > GITHUB_SETUP_INSTRUCTIONS.md << 'EOF'
# GitHub Repository Setup Instructions

## Step 1: Create Repository on GitHub.com

1. Go to: https://github.com/new
2. Fill in:
   - Owner: dehusnain-collab
   - Repository name: openclaw_library_management_system
   - Description: A production-grade Library Management System backend built with FastAPI, PostgreSQL, Redis, and Celery.
   - Visibility: Public
   - UNCHECK: Initialize with README (we already have one)
   - Add .gitignore: Python
   - Choose a license: MIT License
3. Click "Create repository"

## Step 2: Push Code to GitHub

After creating the repository, run:

```bash
# Add remote origin
git remote add origin https://github.com/dehusnain-collab/openclaw_library_management_system.git

# Rename branch to main
git branch -M main

# Push code
git push -u origin main
```

## Step 3: Verify

Visit: https://github.com/dehusnain-collab/openclaw_library_management_system
You should see all project files.
EOF

echo "✅ Created GITHUB_SETUP_INSTRUCTIONS.md"

# Create push script
echo ""
echo "🚀 Creating push script..."
cat > push_to_github.sh << 'EOF'
#!/bin/bash
# Script to push code after creating GitHub repository

echo "Adding remote origin..."
git remote add origin https://github.com/dehusnain-collab/openclaw_library_management_system.git

echo "Renaming branch to main..."
git branch -M main

echo "Pushing code to GitHub..."
git push -u origin main

echo ""
echo "✅ Code pushed successfully!"
echo "🔗 Repository: https://github.com/dehusnain-collab/openclaw_library_management_system"
EOF

chmod +x push_to_github.sh
echo "✅ Created push_to_github.sh"

# Create branch structure for Jira tickets
echo ""
echo "🌿 Creating branch structure for Jira tickets..."
cat > create_feature_branches.sh << 'EOF'
#!/bin/bash
# Script to create feature branches for Jira tickets

echo "Creating feature branches..."

# Make sure we're on main branch
git checkout main

# Sprint 1 - Completed
echo "# Sprint 1: Foundation & Core Authentication"
echo "# ✅ SCRUM-11: Project Structure & Core Setup - COMPLETED"
echo "# ✅ SCRUM-12: Create project folder structure - COMPLETED"
echo "# ✅ SCRUM-13: Database Layer & Migrations - COMPLETED"

# Sprint 1 - Next
echo ""
echo "# 🔄 SCRUM-15: User Registration & Login - NEXT"
git checkout -b feature/SCRUM-15-user-registration-login
git checkout main

echo ""
echo "# ⏳ SCRUM-22: Password Management"
echo "# git checkout -b feature/SCRUM-22-password-management"

echo ""
echo "# ⏳ SCRUM-14: Authentication & Security Module (Epic)"
echo "# git checkout -b feature/SCRUM-14-authentication-security-module"

# Sprint 2
echo ""
echo "# Sprint 2: RBAC & Core Management"
echo "# ⏳ SCRUM-16: Role-Based Access Control"
echo "# git checkout -b feature/SCRUM-16-role-based-access-control"

echo ""
echo "# ⏳ SCRUM-17: Role & Permission System"
echo "# git checkout -b feature/SCRUM-17-role-permission-system"

echo ""
echo "# ⏳ SCRUM-23: Admin Role Management"
echo "# git checkout -b feature/SCRUM-23-admin-role-management"

echo ""
echo "# ⏳ SCRUM-24: User Management"
echo "# git checkout -b feature/SCRUM-24-user-management"

echo ""
echo "# ⏳ SCRUM-25: User Profile Management"
echo "# git checkout -b feature/SCRUM-25-user-profile-management"

echo ""
echo "# ⏳ SCRUM-26: User Deactivation"
echo "# git checkout -b feature/SCRUM-26-user-deactivation"

echo ""
echo "✅ Branch creation script ready!"
echo "First, work on: feature/SCRUM-15-user-registration-login"
EOF

chmod +x create_feature_branches.sh
echo "✅ Created create_feature_branches.sh"

# Create GitHub workflows
echo ""
echo "⚙️ Creating GitHub workflows..."
mkdir -p .github/workflows

# CI/CD workflow
cat > .github/workflows/ci.yml << 'EOF'
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_library_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        pytest tests/ -v
  
  lint:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install linting tools
      run: |
        pip install black isort flake8
    
    - name: Check code formatting
      run: |
        black --check app/
    
    - name: Check import sorting
      run: |
        isort --check-only app/
    
    - name: Lint with flake8
      run: |
        flake8 app/
EOF

echo "✅ Created CI/CD workflow"

# Create PR template
mkdir -p .github/PULL_REQUEST_TEMPLATE

cat > .github/PULL_REQUEST_TEMPLATE.md << 'EOF'
## Description
Implements [Jira Ticket Number]: [Ticket Title]

## Type of Change
- [ ] 🎉 New feature
- [ ] 🐛 Bug fix
- [ ] ♻️ Refactor
- [ ] 📚 Documentation
- [ ] 🧪 Test
- [ ] 🚀 Performance
- [ ] 🔧 CI/CD

## Changes Made
- [ ] Change 1
- [ ] Change 2
- [ ] Change 3

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Documentation updated
- [ ] Tests pass
- [ ] No breaking changes
EOF

echo "✅ Created PR template"

# Create implementation plan for next ticket
echo ""
echo "📋 Creating implementation plan for SCRUM-15..."
cat > IMPLEMENT_SCRUM15.md << 'EOF'
# Implementation Plan: SCRUM-15 - User Registration & Login

## Acceptance Criteria
- [ ] User can register with email and password
- [ ] Password hashed with bcrypt before storage
- [ ] JWT access and refresh tokens generated on login
- [ ] Login endpoint validates credentials
- [ ] Registration includes email validation
- [ ] Password strength validation enforced

## Tasks to Implement

### 1. Create Authentication Service
```python
# app/services/auth_service.py
- Password hashing with bcrypt
- JWT token generation
- Token validation
- Refresh token logic
```

### 2. Create User Schemas
```python
# app/schemas/user.py
- UserCreate schema (registration)
- UserLogin schema (login)
- UserResponse schema (API response)
- Token schemas (access/refresh)
```

### 3. Create Authentication Endpoints
```python
# app/controllers/auth.py
- POST /auth/register
- POST /auth/login
- POST /auth/refresh
- POST /auth/logout
```

### 4. Implement Validation
- Email format validation
- Password strength validation
- Unique email validation

### 5. Create Tests
- Unit tests for auth service
- Integration tests for endpoints
- Test password hashing
- Test token generation

## Files to Create/Modify
1. `app/services/auth_service.py` - Authentication service
2. `app/schemas/user.py` - User schemas
3. `app/controllers/auth.py` - Auth endpoints
4. `app/middleware/auth.py` - Authentication middleware
5. `tests/test_auth.py` - Authentication tests

## Steps
1. Create auth service with bcrypt and JWT
2. Create user schemas with validation
3. Implement registration endpoint
4. Implement login endpoint
5. Add token refresh endpoint
6. Add authentication middleware
7. Write comprehensive tests
8. Update documentation

## Dependencies
- python-jose[cryptography] for JWT
- passlib[bcrypt] for password hashing
- email-validator for email validation
EOF

echo "✅ Created IMPLEMENT_SCRUM15.md"

# Create first implementation script
echo ""
echo "🔧 Creating implementation script for SCRUM-15..."
cat > implement_auth.py << 'EOF'
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