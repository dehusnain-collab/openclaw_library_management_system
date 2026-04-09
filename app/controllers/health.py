"""
Database health check endpoint.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health/database")
async def database_health_check(db: AsyncSession = Depends(get_db)):
    """
    Check database connection health.
    
    Returns:
        Health status with database connection information
    """
    try:
        # Test database connection
        result = await db.execute(text("SELECT 1"))
        test_result = result.scalar()
        
        if test_result == 1:
            return {
                "status": "healthy",
                "database": "connected",
                "message": "Database connection successful"
            }
        else:
            return {
                "status": "unhealthy",
                "database": "error",
                "message": "Database test query failed"
            }
            
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "message": f"Database connection error: {str(e)}"
        }


@router.get("/health/redis")
async def redis_health_check():
    """
    Check Redis connection health.
    
    Note: Redis client implementation needed
    """
    return {
        "status": "not_implemented",
        "redis": "pending",
        "message": "Redis health check not implemented yet"
    }


@router.get("/health/full")
async def full_health_check(db: AsyncSession = Depends(get_db)):
    """
    Comprehensive health check for all services.
    
    Returns:
        Health status of all system components
    """
    components = {}
    
    # Database health
    try:
        result = await db.execute(text("SELECT 1"))
        test_result = result.scalar()
        components["database"] = {
            "status": "healthy" if test_result == 1 else "unhealthy",
            "message": "Connection test successful" if test_result == 1 else "Connection test failed"
        }
    except Exception as e:
        components["database"] = {
            "status": "unhealthy",
            "message": f"Connection error: {str(e)}"
        }
    
    # API health
    components["api"] = {
        "status": "healthy",
        "message": "API is running"
    }
    
    # Determine overall status
    all_healthy = all(comp["status"] == "healthy" for comp in components.values())
    
    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "components": components,
        "timestamp": "2024-01-01T00:00:00Z"  # Would use datetime.utcnow().isoformat()
    }
