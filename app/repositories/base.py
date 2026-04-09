"""
Base repository pattern implementation for data access.
"""
from typing import Generic, TypeVar, Type, Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.sql import func

from app.models.base import BaseModel

ModelType = TypeVar("ModelType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations.
    
    This implements the repository pattern to abstract data access
    and provide a consistent interface for all repositories.
    """
    
    def __init__(self, model: Type[ModelType], db_session: AsyncSession):
        """
        Initialize repository.
        
        Args:
            model: SQLAlchemy model class
            db_session: Async database session
        """
        self.model = model
        self.db_session = db_session
    
    async def create(self, **kwargs) -> ModelType:
        """
        Create a new record.
        
        Args:
            **kwargs: Model attributes
            
        Returns:
            Created model instance
        """
        instance = self.model(**kwargs)
        self.db_session.add(instance)
        await self.db_session.flush()
        await self.db_session.refresh(instance)
        return instance
    
    async def get(self, id: Any) -> Optional[ModelType]:
        """
        Get a record by ID.
        
        Args:
            id: Record ID
            
        Returns:
            Model instance or None if not found
        """
        query = select(self.model).where(self.model.id == id)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by(self, **filters) -> Optional[ModelType]:
        """
        Get a single record by filters.
        
        Args:
            **filters: Filter conditions
            
        Returns:
            Model instance or None if not found
        """
        query = select(self.model).filter_by(**filters)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        **filters
    ) -> List[ModelType]:
        """
        Get multiple records with pagination and filtering.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            **filters: Filter conditions
            
        Returns:
            List of model instances
        """
        query = select(self.model).filter_by(**filters).offset(skip).limit(limit)
        result = await self.db_session.execute(query)
        return result.scalars().all()
    
    async def update(self, id: Any, **kwargs) -> Optional[ModelType]:
        """
        Update a record.
        
        Args:
            id: Record ID
            **kwargs: Attributes to update
            
        Returns:
            Updated model instance or None if not found
        """
        # Get the instance first
        instance = await self.get(id)
        if not instance:
            return None
        
        # Update attributes
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        
        await self.db_session.flush()
        await self.db_session.refresh(instance)
        return instance
    
    async def delete(self, id: Any) -> bool:
        """
        Delete a record.
        
        Args:
            id: Record ID
            
        Returns:
            True if deleted, False if not found
        """
        instance = await self.get(id)
        if not instance:
            return False
        
        await self.db_session.delete(instance)
        await self.db_session.flush()
        return True
    
    async def count(self, **filters) -> int:
        """
        Count records matching filters.
        
        Args:
            **filters: Filter conditions
            
        Returns:
            Count of matching records
        """
        query = select(func.count()).select_from(self.model).filter_by(**filters)
        result = await self.db_session.execute(query)
        return result.scalar()
    
    async def exists(self, **filters) -> bool:
        """
        Check if a record exists matching filters.
        
        Args:
            **filters: Filter conditions
            
        Returns:
            True if exists, False otherwise
        """
        count = await self.count(**filters)
        return count > 0
    
    async def bulk_create(self, instances: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records in bulk.
        
        Args:
            instances: List of dictionaries with model attributes
            
        Returns:
            List of created model instances
        """
        created_instances = []
        for data in instances:
            instance = self.model(**data)
            self.db_session.add(instance)
            created_instances.append(instance)
        
        await self.db_session.flush()
        
        # Refresh all instances
        for instance in created_instances:
            await self.db_session.refresh(instance)
        
        return created_instances
    
    async def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """
        Update multiple records in bulk.
        
        Args:
            updates: List of dictionaries with 'id' and attributes to update
            
        Returns:
            Number of records updated
        """
        updated_count = 0
        for update_data in updates:
            id = update_data.pop('id', None)
            if id:
                instance = await self.get(id)
                if instance:
                    for key, value in update_data.items():
                        if hasattr(instance, key):
                            setattr(instance, key, value)
                    updated_count += 1
        
        if updated_count > 0:
            await self.db_session.flush()
        
        return updated_count