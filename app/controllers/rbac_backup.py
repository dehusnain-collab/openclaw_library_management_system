"""
RBAC endpoints for role and permission management.
"""
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.schemas.rbac import (
    RoleCreate, RoleResponse, RoleUpdate, RoleWithUsersResponse,
    PermissionCreate, PermissionResponse, PermissionUpdate,
    UserRoleAssignment, RolePermissionAssignment,
    UserPermissionsResponse, RBACStatsResponse,
    PermissionCheckRequest, PermissionCheckResponse,
    BulkPermissionCheckRequest, BulkPermissionCheckResponse
)
from app.services.rbac_service import RBACService
from app.utils.logging import get_logger
from app.models.role import Role, Permission
from app.models.user import User

logger = get_logger(__name__)
router = APIRouter(tags=["rbac"])


@router.post("/rbac/initialize", status_code=status.HTTP_200_OK)
async def initialize_rbac(db: AsyncSession = Depends(get_db)) -> Any:
    """
    Initialize RBAC system with predefined roles and permissions.
    
    This endpoint creates the default roles (admin, librarian, member)
    and their associated permissions.
    """
    logger.info("Initializing RBAC system...")
    
    try:
        await RBACService.initialize_roles_and_permissions(db)
        return {"message": "RBAC system initialized successfully"}
    except Exception as e:
        logger.error(f"Failed to initialize RBAC: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize RBAC: {str(e)}"
        )


@router.get("/rbac/stats", response_model=RBACStatsResponse)
async def get_rbac_stats(db: AsyncSession = Depends(get_db)) -> Any:
    """Get RBAC system statistics."""
    logger.info("Getting RBAC statistics...")
    
    try:
        roles = await RBACService.get_all_roles(db)
        permissions = await RBACService.get_all_permissions(db)
        
        # Count users with roles (simplified - would need actual count in production)
        total_users_with_roles = 0
        
        return RBACStatsResponse(
            total_roles=len(roles),
            total_permissions=len(permissions),
            total_users_with_roles=total_users_with_roles,
            predefined_roles=list(RBACService.PREDEFINED_ROLES.keys())
        )
    except Exception as e:
        logger.error(f"Failed to get RBAC stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get RBAC stats: {str(e)}"
        )


# Role endpoints
@router.get("/roles", response_model=List[RoleResponse])
async def get_roles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get all roles with pagination."""
    logger.info(f"Getting roles (skip={skip}, limit={limit})...")
    
    try:
        roles = await RBACService.get_all_roles(db, skip=skip, limit=limit)
        return roles
    except Exception as e:
        logger.error(f"Failed to get roles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get roles: {str(e)}"
        )


@router.get("/roles/{role_id}", response_model=RoleWithUsersResponse)
async def get_role(role_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    """Get a specific role by ID."""
    logger.info(f"Getting role: {role_id}")
    
    try:
        query = select(Role).where(Role.id == role_id)
        result = await db.execute(query)
        role = result.scalar_one_or_none()
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role not found: {role_id}"
            )
        
        return RoleWithUsersResponse.from_orm(role)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get role: {str(e)}"
        )


@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(role_data: RoleCreate, db: AsyncSession = Depends(get_db)) -> Any:
    """Create a new role."""
    logger.info(f"Creating role: {role_data.name}")
    
    try:
        role = await RBACService.create_role(
            name=role_data.name,
            description=role_data.description,
            is_default=role_data.is_default,
            db=db
        )
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role already exists: {role_data.name}"
            )
        
        # Assign permissions if provided
        if role_data.permission_names:
            for perm_name in role_data.permission_names:
                await RBACService.assign_permission_to_role(role.id, perm_name, db)
        
        await db.refresh(role)
        return RoleResponse.from_orm(role)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create role: {str(e)}"
        )


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Update an existing role."""
    logger.info(f"Updating role: {role_id}")
    
    try:
        role = await RBACService.update_role(
            role_id=role_id,
            name=role_data.name,
            description=role_data.description,
            is_default=role_data.is_default,
            db=db
        )
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role not found or name conflict: {role_id}"
            )
        
        return RoleResponse.from_orm(role)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update role: {str(e)}"
        )


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(role_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """Delete a role."""
    logger.info(f"Deleting role: {role_id}")
    
    try:
        success = await RBACService.delete_role(role_id, db)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete role {role_id} - it may be assigned to users or not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete role: {str(e)}"
        )


# Permission endpoints
@router.get("/permissions", response_model=List[PermissionResponse])
async def get_permissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    module: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Get all permissions with pagination and optional module filter."""
    logger.info(f"Getting permissions (skip={skip}, limit={limit}, module={module})...")
    
    try:
        from sqlalchemy import select
        
        query = select(Permission)
        if module:
            query = query.where(Permission.module == module)
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        permissions = result.scalars().all()
        
        return permissions
    except Exception as e:
        logger.error(f"Failed to get permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get permissions: {str(e)}"
        )


@router.get("/permissions/{permission_id}", response_model=PermissionResponse)
async def get_permission(permission_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    """Get a specific permission by ID."""
    logger.info(f"Getting permission: {permission_id}")
    
    try:
        from sqlalchemy import select
        from app.models.permission import Permission
        
        query = select(Permission).where(Permission.id == permission_id)
        result = await db.execute(query)
        permission = result.scalar_one_or_none()
        
        if not permission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Permission not found: {permission_id}"
            )
        
        return PermissionResponse.from_orm(permission)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get permission: {str(e)}"
        )


# User-role management endpoints
@router.post("/users/assign-role", status_code=status.HTTP_200_OK)
async def assign_role_to_user(
    assignment: UserRoleAssignment,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Assign a role to a user."""
    logger.info(f"Assigning role '{assignment.role_name}' to user {assignment.user_id}")
    
    try:
        success = await RBACService.assign_role_to_user(
            user_id=assignment.user_id,
            role_name=assignment.role_name,
            db=db
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to assign role '{assignment.role_name}' to user {assignment.user_id}"
            )
        
        return {"message": f"Role '{assignment.role_name}' assigned to user {assignment.user_id}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign role: {str(e)}"
        )


@router.post("/users/remove-role", status_code=status.HTTP_200_OK)
async def remove_role_from_user(
    assignment: UserRoleAssignment,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Remove a role from a user."""
    logger.info(f"Removing role '{assignment.role_name}' from user {assignment.user_id}")
    
    try:
        success = await RBACService.remove_role_from_user(
            user_id=assignment.user_id,
            role_name=assignment.role_name,
            db=db
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to remove role '{assignment.role_name}' from user {assignment.user_id}"
            )
        
        return {"message": f"Role '{assignment.role_name}' removed from user {assignment.user_id}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove role: {str(e)}"
        )


@router.get("/users/{user_id}/permissions", response_model=UserPermissionsResponse)
async def get_user_permissions(user_id: int, db: AsyncSession = Depends(get_db)) -> Any:
    """Get all permissions for a specific user."""
    logger.info(f"Getting permissions for user: {user_id}")
    
    try:
        from sqlalchemy import select
        from app.models.user import User
        
        # Get user
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {user_id}"
            )
        
        # Get user permissions
        permissions = await RBACService.get_user_permissions(user_id, db)
        roles = [role.name for role in user.roles]
        
        return UserPermissionsResponse(
            user_id=user_id,
            email=user.email,
            roles=roles,
            permissions=list(permissions)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user permissions: {str(e)}"
        )


# Permission check endpoints
@router.post("/permissions/check", response_model=PermissionCheckResponse)
async def check_permission(
    request: PermissionCheckRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Check if a user has a specific permission."""
    logger.info(f"Checking permission '{request.permission_name}' for user {request.user_id}")
    
    try:
        has_permission = await RBACService.user_has_permission(
            user_id=request.user_id,
            permission_name=request.permission_name,
            db=db
        )
        
        # Get roles that have this permission
        roles_with_permission = []
        if has_permission:
            from sqlalchemy import select
            from app.models.role import Role, Permission
            
            query = (
                select(Role)
                .join(Role.permissions)
                .where(Permission.name == request.permission_name)
            )
            result = await db.execute(query)
            roles = result.scalars().all()
            
            # Check which roles the user has
            user_roles = await RBACService.get_user_roles(request.user_id, db)
            user_role_names = [role.name for role in user_roles]
            
            for role in roles:
                if role.name in user_role_names:
                    roles_with_permission.append(role.name)
        
        return PermissionCheckResponse(
            user_id=request.user_id,
            permission_name=request.permission_name,
            has_permission=has_permission,
            roles_with_permission=roles_with_permission
        )
    except Exception as e:
        logger.error(f"Failed to check permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check permission: {str(e)}"
        )


@router.post("/permissions/check-bulk", response_model=BulkPermissionCheckResponse)
async def check_bulk_permissions(
    request: BulkPermissionCheckRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Check if a user has multiple permissions."""
    logger.info(f"Checking {len(request.permission_names)} permissions for user {request.user_id}")
    
    try:
        user_permissions = await RBACService.get_user_permissions(request.user_id, db)
        
        present_permissions = []
        missing_permissions = []
        
        for perm_name in request.permission_names:
            if perm_name in user_permissions:
                present_permissions.append(perm_name)
            else:
                missing_permissions.append(perm_name)
        
        has_all = len(missing_permissions) == 0
        has_any = len(present_permissions) > 0
        
        return BulkPermissionCheckResponse(
            user_id=request.user_id,
            has_all_permissions=has_all,
            has_any_permission=has_any,
            missing_permissions=missing_permissions,
            present_permissions=present_permissions
        )
    except Exception as e:
        logger.error(f"Failed to check bulk permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check bulk permissions: {str(e)}"
        )


# Role-permission management endpoints
@router.post("/roles/assign-permission", status_code=status.HTTP_200_OK)
async def assign_permission_to_role(
    assignment: RolePermissionAssignment,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Assign a permission to a role."""
    logger.info(f"Assigning permission '{assignment.permission_name}' to role {assignment.role_id}")
    
    try:
        success = await RBACService.assign_permission_to_role(
            role_id=assignment.role_id,
            permission_name=assignment.permission_name,
            db=db
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to assign permission '{assignment.permission_name}' to role {assignment.role_id}"
            )
        
        return {"message": f"Permission '{assignment.permission_name}' assigned to role {assignment.role_id}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign permission: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign permission: {str(e)}"
        )


@router.post("/roles/remove-permission", status_code=status.HTTP_200_OK)
async def remove_permission_from_role(
    assignment: RolePermissionAssignment,
    db: AsyncSession = Dep