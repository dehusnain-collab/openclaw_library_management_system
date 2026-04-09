"""
API routers for the Library Management System.
"""
from fastapi import APIRouter

# Create main router
router = APIRouter()

# Import and include all route modules
from app.controllers.health import router as health_router
from app.controllers.auth import router as auth_router

# Include routers
router.include_router(health_router)
router.include_router(auth_router, prefix="/auth", tags=["Authentication"])

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
        }
    }
