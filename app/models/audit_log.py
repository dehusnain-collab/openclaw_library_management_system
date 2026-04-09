"""
Audit log model for tracking user actions.
"""
from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import json

from app.models.base import Base


class AuditAction(enum.Enum):
    """Audit action enumeration."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    ACCESS = "access"
    PERMISSION_CHANGE = "permission_change"
    CONFIGURATION_CHANGE = "configuration_change"


class AuditResource(enum.Enum):
    """Audit resource type enumeration."""
    USER = "user"
    BOOK = "book"
    BORROWING = "borrowing"
    ROLE = "role"
    PERMISSION = "permission"
    SYSTEM = "system"
    CONFIGURATION = "configuration"
    AUDIT_LOG = "audit_log"


class AuditLog(Base):
    """Audit log model for tracking user actions."""
    
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User who performed the action (null for system actions)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # Action details
    action = Column(Enum(AuditAction), nullable=False, index=True)
    resource_type = Column(Enum(AuditResource), nullable=False, index=True)
    resource_id = Column(Integer, nullable=True, index=True)  # ID of the resource acted upon
    
    # Additional details
    details = Column(Text, nullable=True)  # JSON string with additional details
    
    # Request information
    ip_address = Column(String(45), nullable=True)  # Supports IPv6
    user_agent = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', user_id={self.user_id})>"
    
    @property
    def details_dict(self):
        """Get details as dictionary."""
        if self.details:
            try:
                return json.loads(self.details)
            except:
                return {"raw": self.details}
        return {}
    
    @details_dict.setter
    def details_dict(self, value):
        """Set details from dictionary."""
        if value:
            self.details = json.dumps(value)
        else:
            self.details = None
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action.value,
            "resource_type": self.resource_type.value,
            "resource_id": self.resource_id,
            "details": self.details_dict,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat()
        }