#!/bin/bash

# Comprehensive implementation script for remaining Library Management System tickets

echo "============================================================"
echo "🚀 IMPLEMENTING REMAINING LIBRARY MANAGEMENT SYSTEM TICKETS"
echo "============================================================"

echo ""
echo "📊 CURRENT STATUS:"
echo "• Sprint 1: ✅ COMPLETE (4/4 tickets)"
echo "• Sprint 2: 🔄 66% COMPLETE (4/6 tickets)"
echo "• Sprint 3: ❌ NOT STARTED (0/11 tickets)"
echo "• Sprint 4: ❌ NOT STARTED (0/9 tickets)"
echo "• Total Remaining: 29 tickets"
echo ""

# Create a new branch for comprehensive implementation
echo "🌿 Creating implementation branch..."
git checkout main
git pull origin main
git checkout -b comprehensive-implementation

echo ""
echo "============================================================"
echo "📚 IMPLEMENTING BOOK MANAGEMENT SYSTEM (Sprint 3)"
echo "============================================================"

echo ""
echo "📖 Creating book models, services, and endpoints..."

# Create book schemas
echo "📝 Creating book schemas..."
mkdir -p app/schemas

cat > app/schemas/book.py << 'EOF'
"""
Book schemas for API requests and responses.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


class BookStatus(str, Enum):
    """Book status enumeration."""
    AVAILABLE = "available"
    BORROWED = "borrowed"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"
    LOST = "lost"


class BookBase(BaseModel):
    """Base book schema."""
    title: str = Field(..., min_length=1, max_length=500)
    author: str = Field(..., min_length=1, max_length=200)
    isbn: str = Field(..., min_length=10, max_length=20)
    description: Optional[str] = Field(None, max_length=2000)
    publisher: Optional[str] = Field(None, max_length=200)
    publication_year: Optional[int] = Field(None, ge=1000, le=2100)
    genre: Optional[str] = Field(None, max_length=100)
    language: str = Field(default="English", max_length=50)
    page_count: Optional[int] = Field(None, ge=1)
    cover_image_url: Optional[str] = Field(None, max_length=500)
    
    @validator('isbn')
    def validate_isbn(cls, v):
        """Basic ISBN validation."""
        # Remove hyphens and spaces
        clean_isbn = v.replace('-', '').replace(' ', '')
        
        # Check length
        if len(clean_isbn) not in [10, 13]:
            raise ValueError('ISBN must be 10 or 13 digits')
        
        # Check if all characters are digits (except possibly last which can be 'X' for ISBN-10)
        if not clean_isbn[:-1].isdigit():
            raise ValueError('ISBN must contain only digits (except possibly last character)')
        
        return v


class BookCreate(BookBase):
    """Schema for creating a book."""
    total_copies: int = Field(default=1, ge=1)
    available_copies: int = Field(default=1, ge=0)


class BookUpdate(BaseModel):
    """Schema for updating a book."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    author: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    publisher: Optional[str] = Field(None, max_length=200)
    publication_year: Optional[int] = Field(None, ge=1000, le=2100)
    genre: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field(None, max_length=50)
    page_count: Optional[int] = Field(None, ge=1)
    cover_image_url: Optional[str] = Field(None, max_length=500)
    status: Optional[BookStatus] = None
    total_copies: Optional[int] = Field(None, ge=1)
    available_copies: Optional[int] = Field(None, ge=0)


class BookResponse(BookBase):
    """Schema for book API response."""
    id: int
    status: BookStatus
    total_copies: int
    available_copies: int
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[int]
    
    class Config:
        from_attributes = True


class BookSearchParams(BaseModel):
    """Schema for book search parameters."""
    query: Optional[str] = Field(None, min_length=1, max_length=100)
    author: Optional[str] = Field(None, min_length=1, max_length=100)
    genre: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[BookStatus] = None
    min_year: Optional[int] = Field(None, ge=1000, le=2100)
    max_year: Optional[int] = Field(None, ge=1000, le=2100)
    language: Optional[str] = Field(None, min_length=1, max_length=50)
    available_only: bool = Field(default=False)
    
    class Config:
        use_enum_values = True


class BookBulkCreate(BaseModel):
    """Schema for bulk book creation."""
    books: List[BookCreate] = Field(..., min_items=1, max_items=100)


class BookBulkUpdate(BaseModel):
    """Schema for bulk book update."""
    book_ids: List[int] = Field(..., min_items=1, max_items=100)
    update_data: BookUpdate


class BookStatsResponse(BaseModel):
    """Schema for book statistics response."""
    total_books: int
    available_books: int
    borrowed_books: int
    books_by_genre: dict
    books_by_status: dict
    books_by_language: dict
    average_copies_per_book: float
EOF

echo "✅ Created book schemas"

# Create book service
echo "🔧 Creating book service..."
cat > app/services/book_service.py << 'EOF'
"""
Book service for business logic.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime

from app.models.book import Book, BookStatus
from app.schemas.book import BookCreate, BookUpdate, BookSearchParams
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BookService:
    """Service for book operations."""
    
    @staticmethod
    async def create_book(book_data: BookCreate, created_by_id: int, db: AsyncSession) -> Book:
        """Create a new book."""
        logger.info(f"Creating book: {book_data.title}")
        
        # Check if ISBN already exists
        query = select(Book).where(Book.isbn == book_data.isbn)
        result = await db.execute(query)
        existing_book = result.scalar_one_or_none()
        
        if existing_book:
            logger.warning(f"Book with ISBN {book_data.isbn} already exists")
            # In a real system, you might update existing book or throw error
            # For now, we'll update the existing book's copies
            existing_book.total_copies += book_data.total_copies
            existing_book.available_copies += book_data.available_copies
            await db.commit()
            await db.refresh(existing_book)
            return existing_book
        
        # Create new book
        book = Book(
            **book_data.dict(),
            status=BookStatus.AVAILABLE if book_data.available_copies > 0 else BookStatus.MAINTENANCE,
            created_by_id=created_by_id
        )
        
        db.add(book)
        await db.commit()
        await db.refresh(book)
        
        logger.info(f"Book created: {book.id} - {book.title}")
        return book
    
    @staticmethod
    async def get_book(book_id: int, db: AsyncSession) -> Optional[Book]:
        """Get a book by ID."""
        query = select(Book).where(Book.id == book_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_book(book_id: int, update_data: BookUpdate, db: AsyncSession) -> Optional[Book]:
        """Update a book."""
        logger.info(f"Updating book: {book_id}")
        
        book = await BookService.get_book(book_id, db)
        if not book:
            logger.warning(f"Book not found: {book_id}")
            return None
        
        # Update fields
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(book, field, value)
        
        # Update status based on available copies
        if 'available_copies' in update_dict:
            if update_dict['available_copies'] > 0:
                book.status = BookStatus.AVAILABLE
            else:
                book.status = BookStatus.BORROWED
        
        book.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(book)
        
        logger.info(f"Book updated: {book_id}")
        return book
    
    @staticmethod
    async def delete_book(book_id: int, db: AsyncSession) -> bool:
        """Delete a book."""
        logger.info(f"Deleting book: {book_id}")
        
        book = await BookService.get_book(book_id, db)
        if not book:
            logger.warning(f"Book not found: {book_id}")
            return False
        
        # Check if book has active borrowings
        if book.borrowed_copies > 0:
            logger.warning(f"Cannot delete book {book_id} - has active borrowings")
            return False
        
        await db.delete(book)
        await db.commit()
        
        logger.info(f"Book deleted: {book_id}")
        return True
    
    @staticmethod
    async def search_books(
        search_params: BookSearchParams,
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = None
    ) -> List[Book]:
        """Search books with filters."""
        logger.info(f"Searching books with params: {search_params.dict()}")
        
        query = select(Book)
        
        # Apply filters
        filters = []
        
        if search_params.query:
            search_term = f"%{search_params.query}%"
            filters.append(
                or_(
                    Book.title.ilike(search_term),
                    Book.author.ilike(search_term),
                    Book.description.ilike(search_term),
                    Book.isbn.ilike(search_term)
                )
            )
        
        if search_params.author:
            author_term = f"%{search_params.author}%"
            filters.append(Book.author.ilike(author_term))
        
        if search_params.genre:
            filters.append(Book.genre == search_params.genre)
        
        if search_params.status:
            filters.append(Book.status == search_params.status)
        
        if search_params.min_year:
            filters.append(Book.publication_year >= search_params.min_year)
        
        if search_params.max_year:
            filters.append(Book.publication_year <= search_params.max_year)
        
        if search_params.language:
            filters.append(Book.language == search_params.language)
        
        if search_params.available_only:
            filters.append(Book.available_copies > 0)
            filters.append(Book.status == BookStatus.AVAILABLE)
        
        # Apply all filters
        if filters:
            query = query.where(and_(*filters))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        books = result.scalars().all()
        
        logger.info(f"Found {len(books)} books")
        return books
    
    @staticmethod
    async def get_book_stats(db: AsyncSession) -> Dict[str, Any]:
        """Get book statistics."""
        logger.info("Getting book statistics")
        
        # Total books
        total_query = select(func.count(Book.id))
        total_result = await db.execute(total_query)
        total_books = total_result.scalar()
        
        # Available books
        available_query = select(func.count(Book.id)).where(
            Book.available_copies > 0,
            Book.status == BookStatus.AVAILABLE
        )
        available_result = await db.execute(available_query)
        available_books = available_result.scalar()
        
        # Borrowed books
        borrowed_query = select(func.count(Book.id)).where(
            Book.status == BookStatus.BORROWED
        )
        borrowed_result = await db.execute(borrowed_query)
        borrowed_books = borrowed_result.scalar()
        
        # Books by genre
        genre_query = select(Book.genre, func.count(Book.id)).group_by(Book.genre)
        genre_result = await db.execute(genre_query)
        books_by_genre = {row[0] or "Unknown": row[1] for row in genre_result.all()}
        
        # Books by status
        status_query = select(Book.status, func.count(Book.id)).group_by(Book.status)
        status_result = await db.execute(status_query)
        books_by_status = {row[0].value: row[1] for row in status_result.all()}
        
        # Books by language
        language_query = select(Book.language, func.count(Book.id)).group_by(Book.language)
        language_result = await db.execute(language_query)
        books_by_language = {row[0]: row[1] for row in language_result.all()}
        
        # Average copies per book
        avg_query = select(func.avg(Book.total_copies))
        avg_result = await db.execute(avg_query)
        average_copies = avg_result.scalar() or 0
        
        return {
            "total_books": total_books,
            "available_books": available_books,
            "borrowed_books": borrowed_books,
            "books_by_genre": books_by_genre,
            "books_by_status": books_by_status,
            "books_by_language": books_by_language,
            "average_copies_per_book": float(average_copies)
        }
    
    @staticmethod
    async def bulk_create_books(books_data: List[BookCreate], created_by_id: int, db: AsyncSession) -> List[Book]:
        """Create multiple books at once."""
        logger.info(f"Creating {len(books_data)} books in bulk")
        
        created_books = []
        for book_data in books_data:
            book = await BookService.create_book(book_data, created_by_id, db)
            created_books.append(book)
        
        logger.info(f"Created {len(created_books)} books in bulk")
        return created_books
    
    @staticmethod
    async def bulk_update_books(book_ids: List[int], update_data: BookUpdate, db: AsyncSession) -> int:
        """Update multiple books at once."""
        logger.info(f"Updating {len(book_ids)} books in bulk")
        
        updated_count = 0
        for book_id in book_ids:
            book = await BookService.get_book(book_id, db)
            if book:
                update_dict = update_data.dict(exclude_unset=True)
                for field, value in update_dict.items():
                    setattr(book, field, value)
                book.updated_at = datetime.utcnow()
                updated_count += 1
        
        if updated_count > 0:
            await db.commit()
        
        logger.info(f"Updated {updated_count} books in bulk")
        return updated_count
    
    @staticmethod
    async def get_recent_books(limit: int = 10, db: AsyncSession = None) -> List[Book]:
        """Get recently added books."""
        query = select(Book).order_by(Book.created_at.desc()).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_popular_books(limit: int = 10, db: AsyncSession = None) -> List[Book]:
        """Get popular books (based on borrow count)."""
        # This would need borrowing tracking
        # For now, return recent books
        return await BookService.get_recent_books(limit, db)
EOF

echo "✅ Created book service"

echo ""
echo "🚀 Creating book controller..."
cat > app/controllers/books.py << 'EOF'
"""
Book management endpoints.
"""
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.book import (
    BookCreate, BookResponse, BookUpdate, BookSearchParams,
    BookBulkCreate, BookBulkUpdate, BookStatsResponse
)
from app.middleware.auth import get_current_user, require_admin, require_librarian
from app.services.book_service import BookService
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["books"])


@router.get("/books", response_model=List[BookResponse])
async def get_books(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(N