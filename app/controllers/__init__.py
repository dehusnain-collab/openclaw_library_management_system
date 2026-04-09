"""
API routers for the Library Management System.
"""
from fastapi import APIRouter

# Create main router
router = APIRouter()

# Import and include all route modules here
from app.controllers.health import router as health_router

# Include routers
router.include_router(health_router)

# Temporary root endpoint
@router.get("/")
async def root():
    return {
        "message": "Welcome to OpenClaw Library Management System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "database_health": "/health/database"
    }
