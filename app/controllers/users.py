"""
User management endpoints for regular users (non-admin).
"""
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.user import UserResponse, UserUpdate, PasswordChange, MessageResponse
from app.middleware.auth import get_current_user, require_self_or_user_management
from app.repositories.user import UserRepository
from app.services.auth_service import AuthService
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["users"])


@router.get("/users/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get current user's profile.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Current user's profile
    """
    logger.info(f"User {current_user['id']} getting their profile")
    
    try:
        user_repo = UserRepository(db)
        user = await user_repo.get(current_user["id"])
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse.from_orm(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user profile: {str(e)}"
        )


@router.put("/users/me", response_model=UserResponse)
async def update_current_user_profile(
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Update current user's profile.
    
    Args:
        user_data: User data to update
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Updated user profile
    """
    logger.info(f"User {current_user['id']} updating their profile")
    
    try:
        user_repo = UserRepository(db)
        
        # Update user
        update_data = user_data.dict(exclude_unset=True)
        updated_user = await user_repo.update(current_user["id"], **update_data)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user profile"
            )
        
        logger.info(f"User {current_user['id']} updated their profile successfully")
        
        return UserResponse.from_orm(updated_user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user profile: {str(e)}"
        )


@router.post("/users/me/password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Change current user's password.
    
    Args:
        password_data: Password change data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Success message
    """
    logger.info(f"User {current_user['id']} changing password")
    
    try:
        user_repo = UserRepository(db)
        user = await user_repo.get(current_user["id"])
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not AuthService.verify_password(password_data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Hash new password
        new_password_hash = AuthService.get_password_hash(password_data.new_password)
        
        # Update password
        user.password_hash = new_password_hash
        await db.commit()
        
        logger.info(f"User {current_user['id']} changed password successfully")
        
        return MessageResponse(
            message="Password changed successfully",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to change password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to change password: {str(e)}"
        )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_profile(
    user_id: int,
    current_user: dict = Depends(require_self_or_user_management),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get a user's profile.
    
    Users can view their own profile, or profiles of others if they have
    the 'users:read' permission.
    
    Args:
        user_id: ID of user to retrieve
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        User profile
    """
    logger.info(f"User {current_user['id']} getting profile for user {user_id}")
    
    try:
        user_repo = UserRepository(db)
        user = await user_repo.get(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User not found: {user_id}"
            )
        
        # Users can only see active profiles (unless they're viewing their own)
        if not user.is_active and user.id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse.from_orm(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user profile: {str(e)}"
        )


@router.get("/users", response_model=list[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get users (requires 'users:read' permission).
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        search: Search term for email or name
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of users
    """
    logger.info(f"User {current_user['id']} getting users (skip={skip}, limit={limit})")
    
    try:
        # Check if user has permission to view other users
        from app.services.rbac_service import RBACService
        has_permission = await RBACService.user_has_permission(
            user_id=current_user["id"],
            permission_name="users:read",
            db=db
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: users:read"
            )
        
        user_repo = UserRepository(db)
        
        # Build query - only show active users to non-admins
        from sqlalchemy import select
        from app.models.user import User
        
        query = select(User).where(User.is_active == True)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                (User.email.ilike(search_term)) |
                (User.first_name.ilike(search_term)) |
                (User.last_name.ilike(search_term))
            )
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        users = result.scalars().all()
        
        return users
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get users: {str(e)}"
        )


@router.post("/users/me/deactivate", response_model=MessageResponse)
async def deactivate_own_account(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Deactivate current user's own account.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Success message
    """
    logger.info(f"User {current_user['id']} deactivating their account")
    
    try:
        user_repo = UserRepository(db)
        user = await user_repo.get(current_user["id"])
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Deactivate user
        user.is_active = False
        await db.commit()
        
        logger.info(f"User {current_user['id']} deactivated their account")
        
        return MessageResponse(
            message="Account deactivated successfully",
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deactivate account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate account: {str(e)}"
        )


@router.get("/users/me/permissions", response_model=list[str])
async def get_my_permissions(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get current user's permissions.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of permission names
    """
    logger.info(f"User {current_user['id']} getting their permissions")
    
    try:
        from app.services.rbac_service import RBACService
        
        permissions = await RBACService.get_user_permissions(current_user["id"], db)
        return list(permissions)
    except Exception as e:
        logger.error(f"Failed to get user permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user permissions: {str(e)}"
        )


@router.get("/users/me/roles", response_model=list[str])
async def get_my_roles(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get current user's roles.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of role names
    """
    logger.info(f"User {current_user['id']} getting their roles")
    
    try:
        from app.services.rbac_service import RBACService
        
        roles = await RBACService.get_user_roles(current_user["id"], db)
        return [role.name for role in roles]
    except Exception as e:
        logger.error(f"Failed to get user roles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user roles: {str(e)}"
        )


@router.get("/users/search", response_model=list[UserResponse])
async def search_users(
    query: str = Query(..., min_length=1, max_length=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Search for users by email or name.
    
    Requires 'users:read' permission to search other users.
    Users can always search for themselves.
    
    Args:
        query: Search query
        skip: Number of records to skip
        limit: Maximum number of records to return
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of matching users
    """
    logger.info(f"User {current_user['id']} searching users with query: {query}")
    
    try:
        from sqlalchemy import select, or_
        from app.models.user import User
        
        search_term = f"%{query}%"
        
        # Build base query
        base_query = select(User).where(
            or_(
                User.email.ilike(search_term),
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                (User.first_name + " " + User.last_name).ilike(search_term)
            )
        )
        
        # Check if user has permission to view other users
        from app.services.rbac_service import RBACService
        has_permission = await RBACService.user_has_permission(
            user_id=current_user["id"],
            permission_name="users:read",
            db=db
        )
        
        if not has_permission:
            # Users without permission can only see themselves
            base_query = base_query.where(User.id == current_user["id"])
        else:
            # Users with permission can only see active users
            base_query = base_query.where(User.is_active == True)
        
        # Apply pagination
        base_query = base_query.offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(base_query)
        users = result.scalars().all()
        
        return users
    except Exception as e:
        logger.error(f"Failed to search users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search users: {str(e)}"
        )