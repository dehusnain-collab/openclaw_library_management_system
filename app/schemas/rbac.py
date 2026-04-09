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