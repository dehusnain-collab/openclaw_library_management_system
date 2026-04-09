"""
User model for the Library Management System.
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import BaseModel


class User(BaseModel):
    """
    User model representing library system users.
    
    Attributes:
        email: User's email address (unique)
        password_hash: Hashed password
        first_name: User's first name
        last_name: User's last name
        is_active: Whether the user account is active
        last_login: Timestamp of last login
        email_verified: Whether email has been verified
    """
    
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)
    email_verified = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    roles = relationship("Role", secondary="user_roles", back_populates="users")
    borrowing_records = relationship("BorrowingRecord", back_populates="user")
    created_books = relationship("Book", back_populates="created_by")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, is_active={self.is_active})>"
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.email.split('@')[0]
    
    def to_dict(self, exclude: list = None) -> dict:
        """Convert user to dictionary, excluding sensitive data by default."""
        if exclude is None:
            exclude = ["password_hash"]
        
        data = super().to_dict(exclude=exclude)
        data["full_name"] = self.full_name
        return data