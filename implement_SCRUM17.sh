#!/bin/bash

# Implementation script for SCRUM-17: Role & Permission System

echo "============================================================"
echo "Implementing SCRUM-17: Role & Permission System"
echo "============================================================"

echo ""
echo "📋 Creating RBAC implementation..."

# Create RBAC service
echo "🔧 Creating RBAC service..."
cat > app/services/rbac_service.py << 'EOF'
"""
Role-Based Access Control (RBAC) service for authorization management.
"""
from typing import List, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.role import Role, Permission
from app.models.user import User
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RBACService:
    """Service for Role-Based Access Control operations."""
    
    # Predefined roles and permissions
    PREDEFINED_ROLES = {
        "admin": {
            "description": "System administrator with full access",
            "is_default": False,
            "permissions": [
                "users:create", "users:read", "users:update", "users:delete",
                "roles:create", "roles:read", "roles:update", "roles:delete",
                "permissions:create", "permissions:read", "permissions:update", "permissions:delete",
                "books:create", "books:read", "books:update", "books:delete",
                "borrowing:create", "borrowing:read", "borrowing:update", "borrowing:delete",
                "reports:read", "system:manage"
            ]
        },
        "librarian": {
            "description": "Library staff with management permissions",
            "is_default": False,
            "permissions": [
                "users:read", "users:update",
                "books:create", "books:read", "books:update", "books:delete",
                "borrowing:create", "borrowing:read", "borrowing:update", "borrowing:delete",
                "reports:read"
            ]
        },
        "member": {
            "description": "Library member with basic access",
            "is_default": True,
            "permissions": [
                "users:read:self", "users:update:self",
                "books:read",
                "borrowing:create:self", "borrowing:read:self", "borrowing:update:self"
            ]
        }
    }
    
    @staticmethod
    async def initialize_roles_and_permissions(db: AsyncSession) -> None:
        """Initialize predefined roles and permissions in the database."""
        logger.info("Initializing RBAC roles and permissions...")
        
        # Create permissions
        all_permissions = set()
        for role_data in RBACService.PREDEFINED_ROLES.values():
            all_permissions.update(role_data["permissions"])
        
        permission_map = {}
        for perm_name in all_permissions:
            # Extract module from permission name (e.g., "users:create" -> module="users")
            module = perm_name.split(":")[0] if ":" in perm_name else "system"
            
            # Check if permission exists
            query = select(Permission).where(Permission.name == perm_name)
            result = await db.execute(query)
            permission = result.scalar_one_or_none()
            
            if not permission:
                permission = Permission(
                    name=perm_name,
                    description=f"Permission to {perm_name.replace(':', ' ')}",
                    module=module
                )
                db.add(permission)
                logger.debug(f"Created permission: {perm_name}")
            
            permission_map[perm_name] = permission
        
        await db.flush()
        
        # Create roles and assign permissions
        for role_name, role_data in RBACService.PREDEFINED_ROLES.items():
            # Check if role exists
            query = select(Role).where(Role.name == role_name)
            result = await db.execute(query)
            role = result.scalar_one_or_none()
            
            if not role:
                role = Role(
                    name=role_name,
                    description=role_data["description"],
                    is_default=role_data["is_default"]
                )
                db.add(role)
                logger.debug(f"Created role: {role_name}")
            
            # Clear existing permissions and assign new ones
            role.permissions.clear()
            for perm_name in role_data["permissions"]:
                if perm_name in permission_map:
                    role.permissions.append(permission_map[perm_name])
            
            logger.debug(f"Assigned {len(role_data['permissions'])} permissions to role: {role_name}")
        
        await db.commit()
        logger.info("RBAC initialization completed successfully")
    
    @staticmethod
    async def get_user_roles(user_id: int, db: AsyncSession) -> List[Role]:
        """Get all roles assigned to a user."""
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            return []
        
        return user.roles
    
    @staticmethod
    async def get_user_permissions(user_id: int, db: AsyncSession) -> Set[str]:
        """Get all permissions assigned to a user (through roles)."""
        roles = await RBACService.get_user_roles(user_id, db)
        
        permissions = set()
        for role in roles:
            for permission in role.permissions:
                permissions.add(permission.name)
        
        return permissions
    
    @staticmethod
    async def user_has_permission(user_id: int, permission_name: str, db: AsyncSession) -> bool:
        """Check if user has a specific permission."""
        user_permissions = await RBACService.get_user_permissions(user_id, db)
        return permission_name in user_permissions
    
    @staticmethod
    async def user_has_any_permission(user_id: int, permission_names: List[str], db: AsyncSession) -> bool:
        """Check if user has any of the specified permissions."""
        user_permissions = await RBACService.get_user_permissions(user_id, db)
        return any(perm in user_permissions for perm in permission_names)
    
    @staticmethod
    async def user_has_all_permissions(user_id: int, permission_names: List[str], db: AsyncSession) -> bool:
        """Check if user has all of the specified permissions."""
        user_permissions = await RBACService.get_user_permissions(user_id, db)
        return all(perm in user_permissions for perm in permission_names)
    
    @staticmethod
    async def assign_role_to_user(user_id: int, role_name: str, db: AsyncSession) -> bool:
        """Assign a role to a user."""
        # Get user
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User not found: {user_id}")
            return False
        
        # Get role
        query = select(Role).where(Role.name == role_name)
        result = await db.execute(query)
        role = result.scalar_one_or_none()
        
        if not role:
            logger.warning(f"Role not found: {role_name}")
            return False
        
        # Check if user already has this role
        if role in user.roles:
            logger.debug(f"User {user_id} already has role: {role_name}")
            return True
        
        # Assign role
        user.roles.append(role)
        await db.commit()
        
        logger.info(f"Assigned role '{role_name}' to user {user_id}")
        return True
    
    @staticmethod
    async def remove_role_from_user(user_id: int, role_name: str, db: AsyncSession) -> bool:
        """Remove a role from a user."""
        # Get user
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User not found: {user_id}")
            return False
        
        # Get role
        query = select(Role).where(Role.name == role_name)
        result = await db.execute(query)
        role = result.scalar_one_or_none()
        
        if not role:
            logger.warning(f"Role not found: {role_name}")
            return False
        
        # Check if user has this role
        if role not in user.roles:
            logger.debug(f"User {user_id} doesn't have role: {role_name}")
            return True
        
        # Remove role
        user.roles.remove(role)
        await db.commit()
        
        logger.info(f"Removed role '{role_name}' from user {user_id}")
        return True
    
    @staticmethod
    async def get_all_roles(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Role]:
        """Get all roles with pagination."""
        query = select(Role).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_all_permissions(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Permission]:
        """Get all permissions with pagination."""
        query = select(Permission).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def create_role(name: str, description: str, is_default: bool, db: AsyncSession) -> Optional[Role]:
        """Create a new role."""
        # Check if role already exists
        query = select(Role).where(Role.name == name)
        result = await db.execute(query)
        existing_role = result.scalar_one_or_none()
        
        if existing_role:
            logger.warning(f"Role already exists: {name}")
            return None
        
        role = Role(
            name=name,
            description=description,
            is_default=is_default
        )
        
        db.add(role)
        await db.commit()
        await db.refresh(role)
        
        logger.info(f"Created new role: {name}")
        return role
    
    @staticmethod
    async def update_role(role_id: int, name: str, description: str, is_default: bool, db: AsyncSession) -> Optional[Role]:
        """Update an existing role."""
        query = select(Role).where(Role.id == role_id)
        result = await db.execute(query)
        role = result.scalar_one_or_none()
        
        if not role:
            logger.warning(f"Role not found: {role_id}")
            return None
        
        # Check if new name conflicts with existing role
        if name != role.name:
            query = select(Role).where(Role.name == name)
            result = await db.execute(query)
            existing_role = result.scalar_one_or_none()
            
            if existing_role:
                logger.warning(f"Role name already exists: {name}")
                return None
        
        role.name = name
        role.description = description
        role.is_default = is_default
        
        await db.commit()
        await db.refresh(role)
        
        logger.info(f"Updated role: {name}")
        return role
    
    @staticmethod
    async def delete_role(role_id: int, db: AsyncSession) -> bool:
        """Delete a role."""
        query = select(Role).where(Role.id == role_id)
        result = await db.execute(query)
        role = result.scalar_one_or_none()
        
        if not role:
            logger.warning(f"Role not found: {role_id}")
            return False
        
        # Check if role is assigned to any users
        if role.users:
            logger.warning(f"Cannot delete role '{role.name}' - it is assigned to {len(role.users)} users")
            return False
        
        await db.delete(role)
        await db.commit()
        
        logger.info(f"Deleted role: {role.name}")
        return True
    
    @staticmethod
    async def assign_permission_to_role(role_id: int, permission_name: str, db: AsyncSession) -> bool:
        """Assign a permission to a role."""
        # Get role
        query = select(Role).where(Role.id == role_id)
        result = await db.execute(query)
        role = result.scalar_one_or_none()
        
        if not role:
            logger.warning(f"Role not found: {role_id}")
            return False
        
        # Get permission
        query = select(Permission).where(Permission.name == permission_name)
        result = await db.execute(query)
        permission = result.scalar_one_or_none()
        
        if not permission:
            logger.warning(f"Permission not found: {permission_name}")
            return False
        
        # Check if role already has this permission
        if permission in role.permissions:
            logger.debug(f"Role '{role.name}' already has permission: {permission_name}")
            return True
        
        # Assign permission
        role.permissions.append(permission)
        await db.commit()
        
        logger.info(f"Assigned permission '{permission_name}' to role '{role.name}'")
        return True
    
    @staticmethod
    async def remove_permission_from_role(role_id: int, permission_name: str, db: AsyncSession) -> bool:
        """Remove a permission from a role."""
        # Get role
        query = select(Role).where(Role.id == role_id)
        result = await db.execute(query)
        role = result.scalar_one_or_none()
        
        if not role:
            logger.warning(f"Role not found: {role_id}")
            return False
        
        # Get permission
        query = select(Permission).where(Permission.name == permission_name)
        result = await db.execute(query)
        permission = result.scalar_one_or_none()
        
        if not permission:
            logger.warning(f"Permission not found: {permission_name}")
            return False
        
        # Check if role has this permission
        if permission not in role.permissions:
            logger.debug(f"Role '{role.name}' doesn't have permission: {permission_name}")
            return True
        
        # Remove permission
        role.permissions.remove(permission)
        await db.commit()
        
        logger.info(f"Removed permission '{permission_name}' from role '{role.name}'")
        return True
EOF

echo "✅ Created RBAC service"

echo ""
echo "📝 Creating RBAC schemas..."
cat > app/schemas/rbac.py << 'EOF'
"""
RBAC schemas for roles and permissions.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class PermissionBase(BaseModel):
    """Base permission schema."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    module: str = Field(..., min_length=1, max_length=100)


class PermissionCreate(PermissionBase):
    """Schema for creating a permission."""
    pass


class PermissionUpdate(BaseModel):
    """Schema for updating a permission."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    module: Optional[str] = Field(None, min_length=1, max_length=100)


class PermissionResponse(PermissionBase):
    """Schema for permission API response."""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    """Base role schema."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_default: bool = Field(default=False)


class RoleCreate(RoleBase):
    """Schema for creating a role."""
    permission_names: Optional[List[str]] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    """Schema for updating a role."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_default: Optional[bool] = None


class RoleResponse(RoleBase):
    """Schema for role API response."""
    id: int
    created_at: datetime
    updated_at: datetime
    permissions: List[PermissionResponse] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


class RoleWithUsersResponse(RoleResponse):
    """Schema for role API response with users."""
    user_count: int = 0
    
    class Config:
        from_attributes = True


class UserRoleAssignment(BaseModel):
    """Schema for assigning/removing roles from users."""
    user_id: int
    role_name: str


class RolePermissionAssignment(BaseModel):
    """Schema for assigning/removing permissions from roles."""
    role_id: int
    permission_name: str


class UserPermissionsResponse(BaseModel):
    """Schema for user permissions response."""
    user_id: int
    email: str
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)


class RBACStatsResponse(BaseModel):
    """Schema for RBAC statistics response."""
    total_roles: int
    total_permissions: int
    total_users_with_roles: int
    predefined_roles: List[str] = Field(default_factory=list)


class PermissionCheckRequest(BaseModel):
    """Schema for checking user permissions."""
    user_id: int
    permission_name: str


class PermissionCheckResponse(BaseModel):
    """Schema for permission check response."""
    user_id: int
    permission_name: str
    has_permission: bool
    roles_with_permission: List[str] = Field(default_factory=list)


class BulkPermissionCheckRequest(BaseModel):
    """Schema for checking multiple user permissions."""
    user_id: int
    permission_names: List[str]


class BulkPermissionCheckResponse(BaseModel):
    """Schema for bulk permission check response."""
    user_id: int
    has_all_permissions: bool
    has_any_permission: bool
    missing_permissions: List[str] = Field(default_factory=list)
    present_permissions: List[str] = Field(default_factory=list)
EOF

echo "✅ Created RBAC schemas"

echo ""
echo "🚀 Creating RBAC controller..."
cat > app/controllers/rbac.py << 'EOF'
"""
RBAC