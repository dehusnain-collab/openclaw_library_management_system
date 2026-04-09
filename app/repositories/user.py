"""
User repository for data access.
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.repositories.base import BaseRepository
from app.models.user import User

class UserRepository(BaseRepository[User]):
    """User repository with user-specific queries."""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(User, db_session)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        query = select(User).where(User.email == email)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()
    
    async def email_exists(self, email: str) -> bool:
        """Check if email already exists."""
        query = select(User).where(User.email == email)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def get_active_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get active users with pagination."""
        query = select(User).where(User.is_active == True).offset(skip).limit(limit)
        result = await self.db_session.execute(query)
        return result.scalars().all()
