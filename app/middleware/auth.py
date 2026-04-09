"""
Authentication and authorization middleware for RBAC.
"""
from typing import Optional, List
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth_service import AuthService
from app.services.rbac_service import RBACService
from app.utils.logging import get_logger

logger = get_logger(__name__)
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        db: Database session
        
    Returns:
        User payload from JWT token
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    
    # Decode token
    payload = AuthService.decode_token(token)
    if not payload:
        logger.warning("Invalid token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check token type
    token_type = payload.get("type")
    if token_type != "access":
        logger.warning(f"Invalid token type: {token_type}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract user info
    user_id = payload.get("sub")
    email = payload.get("email")
    
    if not user_id or not email:
        logger.warning("Token missing required fields")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "id": int(user_id),
        "email": email,
        "token": token
    }


class PermissionChecker:
    """Dependency to check user permissions."""
    
    def __init__(self, required_permissions: Optional[List[str]] = None, require_all: bool = True):
        """
        Initialize permission checker.
        
        Args:
            required_permissions: List of permission names required
            require_all: If True, user must have ALL permissions; if False, user must have ANY permission
        """
        self.required_permissions = required_permissions or []
        self.require_all = require_all
    
    async def __call__(
        self,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> dict:
        """
        Check if current user has required permissions.
        
        Args:
            current_user: Current authenticated user
            db: Database session
            
        Returns:
            Current user if permissions are satisfied
            
        Raises:
            HTTPException: If user lacks required permissions
        """
        user_id = current_user["id"]
        
        # If no permissions required, just return user
        if not self.required_permissions:
            return current_user
        
        # Check permissions
        if self.require_all:
            # User must have ALL required permissions
            has_permission = await RBACService.user_has_all_permissions(
                user_id=user_id,
                permission_names=self.required_permissions,
                db=db
            )
            error_detail = f"User lacks required permissions: {', '.join(self.required_permissions)}"
        else:
            # User must have ANY of the required permissions
            has_permission = await RBACService.user_has_any_permission(
                user_id=user_id,
                permission_names=self.required_permissions,
                db=db
            )
            error_detail = f"User lacks any of the required permissions: {', '.join(self.required_permissions)}"
        
        if not has_permission:
            logger.warning(f"Permission denied for user {user_id}: {error_detail}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_detail
            )
        
        return current_user


class RoleChecker:
    """Dependency to check user roles."""
    
    def __init__(self, required_roles: List[str], require_all: bool = False):
        """
        Initialize role checker.
        
        Args:
            required_roles: List of role names required
            require_all: If True, user must have ALL roles; if False, user must have ANY role
        """
        self.required_roles = required_roles
        self.require_all = require_all
    
    async def __call__(
        self,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> dict:
        """
        Check if current user has required roles.
        
        Args:
            current_user: Current authenticated user
            db: Database session
            
        Returns:
            Current user if roles are satisfied
            
        Raises:
            HTTPException: If user lacks required roles
        """
        user_id = current_user["id"]
        
        # Get user roles
        user_roles = await RBACService.get_user_roles(user_id, db)
        user_role_names = [role.name for role in user_roles]
        
        # Check roles
        if self.require_all:
            # User must have ALL required roles
            has_role = all(role_name in user_role_names for role_name in self.required_roles)
            error_detail = f"User lacks required roles: {', '.join(self.required_roles)}"
        else:
            # User must have ANY of the required roles
            has_role = any(role_name in user_role_names for role_name in self.required_roles)
            error_detail = f"User lacks any of the required roles: {', '.join(self.required_roles)}"
        
        if not has_role:
            logger.warning(f"Role denied for user {user_id}: {error_detail}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_detail
            )
        
        return current_user


# Common permission checkers
require_admin = PermissionChecker(
    required_permissions=["system:manage"],
    require_all=True
)

require_librarian = RoleChecker(
    required_roles=["librarian", "admin"],
    require_all=False
)

require_member = RoleChecker(
    required_roles=["member", "librarian", "admin"],
    require_all=False
)

# Common permission sets
user_management_permissions = PermissionChecker(
    required_permissions=["users:create", "users:read", "users:update", "users:delete"],
    require_all=False
)

book_management_permissions = PermissionChecker(
    required_permissions=["books:create", "books:read", "books:update", "books:delete"],
    require_all=False
)

borrowing_management_permissions = PermissionChecker(
    required_permissions=["borrowing:create", "borrowing:read", "borrowing:update", "borrowing:delete"],
    require_all=False
)

# Self-only permissions (users can only access their own data)
def require_self_or_permission(user_id_field: str = "user_id", permission: str = None):
    """
    Create a dependency that checks if user is accessing their own data or has permission.
    
    Args:
        user_id_field: Name of the field containing user ID in request
        permission: Permission required to access other users' data
        
    Returns:
        Dependency function
    """
    async def dependency(
        request: Request,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> dict:
        # Try to get user ID from request
        user_id_to_access = None
        
        # Check path parameters
        if user_id_field in request.path_params:
            user_id_to_access = int(request.path_params[user_id_field])
        
        # Check query parameters
        elif user_id_field in request.query_params:
            user_id_to_access = int(request.query_params[user_id_field])
        
        # If we can't determine which user is being accessed, require permission
        if user_id_to_access is None:
            if permission:
                has_perm = await RBACService.user_has_permission(
                    user_id=current_user["id"],
                    permission_name=permission,
                    db=db
                )
                if not has_perm:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission denied: {permission}"
                    )
            return current_user
        
        # Check if user is accessing their own data
        if user_id_to_access == current_user["id"]:
            return current_user
        
        # User is accessing someone else's data - check permission
        if permission:
            has_perm = await RBACService.user_has_permission(
                user_id=current_user["id"],
                permission_name=permission,
                db=db
            )
            if not has_perm:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Cannot access other users' data without permission: {permission}"
                )
            return current_user
        
        # No permission specified and user is not accessing their own data
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access other users' data"
        )
    
    return dependency


# Convenience functions for common self-access patterns
require_self_or_user_management = require_self_or_permission(
    user_id_field="user_id",
    permission="users:read"
)

require_self_or_book_management = require_self_or_permission(
    user_id_field="user_id",
    permission="books:read"
)

require_self_or_borrowing_management = require_self_or_permission(
    user_id_field="user_id",
    permission="borrowing:read"
)