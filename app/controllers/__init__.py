"""
API routers for the Library Management System.
"""
from fastapi import APIRouter

# Create main router
router = APIRouter()

# Import and include all route modules
from app.controllers.health import router as health_router
from app.controllers.auth import router as auth_router
from app.controllers.rbac import router as rbac_router
from app.controllers.admin import router as admin_router
from app.controllers.users import router as users_router

# Include routers
router.include_router(health_router)
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
router.include_router(rbac_router, prefix="/api/v1", tags=["RBAC"])
router.include_router(admin_router, prefix="/api/v1", tags=["Admin"])
router.include_router(users_router, prefix="/api/v1", tags=["Users"])

# Root endpoint
@router.get("/")
async def root():
    return {
        "message": "Welcome to OpenClaw Library Management System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "auth": {
            "register": "/api/v1/auth/register",
            "login": "/api/v1/auth/login",
            "refresh": "/api/v1/auth/refresh",
            "logout": "/api/v1/auth/logout"
        },
        "rbac": {
            "initialize": "/api/v1/rbac/initialize",
            "stats": "/api/v1/rbac/stats",
            "roles": "/api/v1/roles",
            "permissions": "/api/v1/permissions",
            "user_permissions": "/api/v1/users/{user_id}/permissions"
        },
        "admin": {
            "users": "/api/v1/admin/users",
            "user_stats": "/api/v1/admin/users/stats",
            "system_health": "/api/v1/admin/system/health",
            "audit_logs": "/api/v1/admin/audit/logs"
        },
        "users": {
            "my_profile": "/api/v1/users/me",
            "update_profile": "/api/v1/users/me",
            "change_password": "/api/v1/users/me/password",
            "get_user": "/api/v1/users/{user_id}",
            "search_users": "/api/v1/users/search",
            "my_permissions": "/api/v1/users/me/permissions",
            "my_roles": "/api/v1/users/me/roles",
            "deactivate_account": "/api/v1/users/me/deactivate"
        }
    }
