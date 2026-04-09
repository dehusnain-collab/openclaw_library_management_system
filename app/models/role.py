"""
Role and permission models for Role-Based Access Control (RBAC).
"""
from sqlalchemy import Column, String, Text, ForeignKey, Table
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


# Association table for user-roles many-to-many relationship
user_roles = Table(
    "user_roles",
    BaseModel.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

# Association table for role-permissions many-to-many relationship
role_permissions = Table(
    "role_permissions",
    BaseModel.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Role(BaseModel):
    """
    Role model for RBAC system.
    
    Attributes:
        name: Role name (unique)
        description: Role description
        is_default: Whether this is a default role for new users
    """
    
    __tablename__ = "roles"
    
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    
    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name})>"
    
    def has_permission(self, permission_name: str) -> bool:
        """Check if role has specific permission."""
        return any(perm.name == permission_name for perm in self.permissions)


class Permission(BaseModel):
    """
    Permission model for RBAC system.
    
    Attributes:
        name: Permission name (unique)
        description: Permission description
        module: Module/feature this permission belongs to
    """
    
    __tablename__ = "permissions"
    
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    module = Column(String(100), nullable=False, index=True)
    
    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
    
    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name={self.name}, module={self.module})>"