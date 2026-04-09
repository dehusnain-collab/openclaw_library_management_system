"""
API routers for the Library Management System.
"""
from fastapi import APIRouter

# Create main router
router = APIRouter()

# Import and include all route modules here
# These will be added as we implement features

# Health check is already in main.py
# Authentication routes will be added in auth.py
# User routes will be added in users.py
# Book routes will be added in books.py
# Borrowing routes will be added in borrowing.py

# Example of how routes will be included:
# from app.controllers.auth import router as auth_router
# from app.controllers.users import router as users_router
# from app.controllers.books import router as books_router

# router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
# router.include_router(users_router, prefix="/users", tags=["Users"])
# router.include_router(books_router, prefix="/books", tags=["Books"])

# Temporary root endpoint
@router.get("/")
async def root():
    return {
        "message": "Welcome to OpenClaw Library Management System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }