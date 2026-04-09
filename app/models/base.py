"""
Base SQLAlchemy model with common fields and methods.
"""
from datetime import datetime
from typing import Any
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.sql import func

Base = declarative_base()


class BaseModel(Base):
    """
    Base model with common fields and methods.
    
    All models should inherit from this class to get:
    - Automatic table naming (pluralized, lowercase)
    - id, created_at, updated_at fields
    - Common methods for serialization
    """
    
    __abstract__ = True
    
    @declared_attr
    def __tablename__(cls) -> str:
        """
        Generate table name from class name.
        
        Converts CamelCase to snake_case and pluralizes.
        Example: UserModel -> user_models
        """
        # Convert CamelCase to snake_case
        import re
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', cls.__name__).lower()
        
        # Pluralize (simple rule - add 's' or 'es')
        if name.endswith('y'):
            name = name[:-1] + 'ies'
        elif name.endswith(('s', 'x', 'z', 'ch', 'sh')):
            name = name + 'es'
        else:
            name = name + 's'
        
        return name
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    def to_dict(self, exclude: list = None) -> dict:
        """
        Convert model instance to dictionary.
        
        Args:
            exclude: List of field names to exclude
            
        Returns:
            Dictionary representation of the model
        """
        if exclude is None:
            exclude = []
        
        result = {}
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                
                # Convert datetime to ISO format string
                if isinstance(value, datetime):
                    value = value.isoformat()
                
                result[column.name] = value
        
        return result
    
    def update(self, **kwargs) -> None:
        """
        Update model attributes.
        
        Args:
            **kwargs: Attributes to update
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @classmethod
    def get_field_names(cls) -> list:
        """
        Get all field names for the model.
        
        Returns:
            List of field names
        """
        return [column.name for column in cls.__table__.columns]
    
    def __repr__(self) -> str:
        """
        String representation of the model.
        """
        return f"<{self.__class__.__name__}(id={self.id})>"