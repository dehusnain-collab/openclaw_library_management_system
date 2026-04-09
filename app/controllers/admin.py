"""
Admin-specific endpoints for system management.
"""
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.schemas.user import UserResponse, UserUpdate, MessageResponse
from app.schemas.rbac import UserRoleAssignment, RoleResponse
from app.middleware.auth import require_admin, get_current_user
from app.services.rbac_service import RBACService
from app.repositories.user import UserRepository
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["admin"])


@router.get("/admin/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
) -> Any:
    """
    Get all users (admin only).
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        active_only: Only return active users
        search: Search term for email or name
        db: Database session
        current_user: Current authenticated admin user
        
    Returns:
        List of users
    """
    logger.info(f"Admin {current_user['id']} getting users (skip={skip}, limit={limit})")
    
    try:
        user_repo = UserRepository(db)
        
        # Build query
        query = select(UserRepository.model)
        
        if active_only:
            query = query.where(UserRepository.model.is_active == True)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                (UserRepository.model.email.ilike(search_term)) |
                (UserRepository.model.first_name.ilike(search_term)) |
                (UserRepository.model.last_name.ilike(search_term))
            )
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        users = result.scalars().all()
        
        return users
    except Exception as e:
        logger.error(f"Failed to get users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get users: {str(e)}"
        )


@router.get("/admin/users/stats", response_model=dict)
async def get_user_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
) -> Any:
    """
    Get user statistics (admin only).
    
    Returns:
        User statistics including counts and role distribution
    """
    logger.info(f"Admin {current_user['id']} getting user stats")
    
    try:
        user_repo = UserRepository(db)
        
        # Get total user count
        total_users = await user_repo.count()
        
        # Get active user count
        active_users = await user_repo.count_by(is_active=True)
        
        # Get users by role (simplified - would need proper aggregation in production)
        from app.models.user import User
        from app.models.role import Role
        
        # Get role distribution
        query = (
            select(Role.name, func.count(User.id))
            .join(User.roles)
            .group_by(Role.name)
        )
        result = await db.execute(query)
        role_distribution = {row[0]: row[1] for row in result.all()}
        
        # Get recent registrations (last 7 days)
        from datetime import datetime, timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        recent_users = await user_repo.count_by(
            created_at__gte=week_ago
        )
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "recent_registrations_7d": recent_users,
            "role_distribution": role_distribution,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get user stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user stats: {str(e)}"
        )


@router.get("/admin/users/{user_id}", response_model=UserResponse)
async def get_user_by_admin(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
) -> Any:
    """
    Get any user by ID (admin only).
    
    Args:
        user_id: ID of user to retrieve
        db: Database session
        current_user: Current authenticated admin user
        
    Returns:
        User details
    """
    logger.info(f"Admin {current_user['id']} getting user {user_id}")
    
    try:
        user_repo = UserRepository(db)
        user = await user_repo.get(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {user_id}"
            )
        
        return UserResponse.from_orm(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}"
        )


@router.put("/admin/users/{user_id}", response_model=UserResponse)
async def update_user_by_admin(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
) -> Any:
    """
    Update any user by ID (admin only).
    
    Args:
        user_id: ID of user to update
        user_data: User data to update
        db: Database session
        current_user: Current authenticated admin user
        
    Returns:
        Updated user details
    """
    logger.info(f"Admin {current_user['id']} updating user {user_id}")
    
    try:
        user_repo = UserRepository(db)
        
        # Get user
        user = await user_repo.get(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {user_id}"
            )
        
        # Update user
        update_data = user_data.dict(exclude_unset=True)
        updated_user = await user_repo.update(user_id, **update_data)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user"
            )
        
        return UserResponse.from_orm(updated_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )


@router.post("/admin/users/{user_id}/activate", response_model=MessageResponse)
async def activate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
) -> Any:
    """
    Activate a user account (admin only).
    
    Args:
        user_id: ID of user to activate
        db: Database session
        current_user: Current authenticated admin user
        
    Returns:
        Success message
    """
    logger.info(f"Admin {current_user['id']} activating user {user_id}")
    
    try:
        user_repo = UserRepository(db)
        
        # Get user
        user = await user_repo.get(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {user_id}"
            )
        
        # Activate user
        user.is_active = True
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"User {user_id} activated by admin {current_user['id']}")
        
        return MessageResponse(
            message=f"User {user_id} activated successfully",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to activate user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate user: {str(e)}"
        )


@router.post("/admin/users/{user_id}/deactivate", response_model=MessageResponse)
async def deactivate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
) -> Any:
    """
    Deactivate a user account (admin only).
    
    Args:
        user_id: ID of user to deactivate
        db: Database session
        current_user: Current authenticated admin user
        
    Returns:
        Success message
    """
    logger.info(f"Admin {current_user['id']} deactivating user {user_id}")
    
    try:
        user_repo = UserRepository(db)
        
        # Get user
        user = await user_repo.get(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {user_id}"
            )
        
        # Cannot deactivate yourself
        if user.id == current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account"
            )
        
        # Deactivate user
        user.is_active = False
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"User {user_id} deactivated by admin {current_user['id']}")
        
        return MessageResponse(
            message=f"User {user_id} deactivated successfully",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deactivate user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate user: {str(e)}"
        )


@router.post("/admin/users/{user_id}/roles", response_model=MessageResponse)
async def assign_role_to_user_admin(
    user_id: int,
    assignment: UserRoleAssignment,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
) -> Any:
    """
    Assign a role to a user (admin only).
    
    Args:
        user_id: ID of user to assign role to
        assignment: Role assignment data
        db: Database session
        current_user: Current authenticated admin user
        
    Returns:
        Success message
    """
    logger.info(f"Admin {current_user['id']} assigning role '{assignment.role_name}' to user {user_id}")
    
    try:
        success = await RBACService.assign_role_to_user(
            user_id=user_id,
            role_name=assignment.role_name,
            db=db
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to assign role '{assignment.role_name}' to user {user_id}"
            )
        
        return MessageResponse(
            message=f"Role '{assignment.role_name}' assigned to user {user_id}",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign role: {str(e)}"
        )


@router.delete("/admin/users/{user_id}/roles/{role_name}", response_model=MessageResponse)
async def remove_role_from_user_admin(
    user_id: int,
    role_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
) -> Any:
    """
    Remove a role from a user (admin only).
    
    Args:
        user_id: ID of user to remove role from
        role_name: Name of role to remove
        db: Database session
        current_user: Current authenticated admin user
        
    Returns:
        Success message
    """
    logger.info(f"Admin {current_user['id']} removing role '{role_name}' from user {user_id}")
    
    try:
        success = await RBACService.remove_role_from_user(
            user_id=user_id,
            role_name=role_name,
            db=db
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to remove role '{role_name}' from user {user_id}"
            )
        
        return MessageResponse(
            message=f"Role '{role_name}' removed from user {user_id}",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove role: {str(e)}"
        )


@router.get("/admin/users/{user_id}/roles", response_model=List[str])
async def get_user_roles_admin(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
) -> Any:
    """
    Get all roles for a user (admin only).
    
    Args:
        user_id: ID of user to get roles for
        db: Database session
        current_user: Current authenticated admin user
        
    Returns:
        List of role names
    """
    logger.info(f"Admin {current_user['id']} getting roles for user {user_id}")
    
    try:
        roles = await RBACService.get_user_roles(user_id, db)
        return [role.name for role in roles]
    except Exception as e:
        logger.error(f"Failed to get user roles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user roles: {str(e)}"
        )


@router.get("/admin/system/health", response_model=dict)
async def get_system_health(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
) -> Any:
    """
    Get system health information (admin only).
    
    Returns:
        System health status including database, cache, and service status
    """
    logger.info(f"Admin {current_user['id']} checking system health")
    
    try:
        from datetime import datetime
        
        # Check database connection
        db_status = "healthy"
        try:
            await db.execute(select(1))
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
        
        # Get system metrics
        user_repo = UserRepository(db)
        total_users = await user_repo.count()
        
        from app.models.role import Role, Permission
        role_count = await db.execute(select(func.count(Role.id)))
        role_count = role_count.scalar()
        
        permission_count = await db.execute(select(func.count(Permission.id)))
        permission_count = permission_count.scalar()
        
        return {
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                "database": db_status,
                "api": "healthy",
                "authentication": "healthy"
            },
            "metrics": {
                "total_users": total_users,
                "total_roles": role_count,
                "total_permissions": permission_count,
                "uptime": "0d 0h 0m"  # Would be calculated from process start time in production
            },
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system health: {str(e)}"
        )


@router.get("/admin/audit/logs", response_model=dict)
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    level: Optional[str] = Query(None, regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
) -> Any:
    """
    Get audit logs (admin only).
    
    Note: In a production system, this would query from a proper logging database.
    This is a simplified implementation.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        level: Filter by log level
        db: Database session
        current_user: Current authenticated admin user
        
    Returns:
        Audit log entries
    """
    logger.info(f"Admin {current_user['id']} getting audit logs")
    
    try:
        # In a real system, this would query from a logs database or file
        # For now, return mock data
        from datetime import datetime, timedelta
        
        mock_logs = []
        for i in range(min(limit, 50)):  # Generate up to 50 mock logs
            levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            log_level = levels[i % len(levels)]
            
            # Apply level filter
            if level and log_level != level:
                continue
            
            mock