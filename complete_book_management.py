#!/usr/bin/env python3
"""
Complete book management system implementation.
Covers: SCRUM-18, SCRUM-19, SCRUM-27
"""

import os
import sys
from pathlib import Path

def create_book_models():
    """Create complete book model."""
    print("Creating book models...")
    
    # Update the existing book model
    book_model = '''"""
Book model for library management system.
"""
from sqlalchemy import Column, Integer, String, Text, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.models.base import Base


class BookStatus(enum.Enum):
    """Book status enumeration."""
    AVAILABLE = "available"
    BORROWED = "borrowed"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"
    LOST = "lost"


class Book(Base):
    """Book model representing a book in the library."""
    
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    author = Column(String(200), nullable=False, index=True)
    isbn = Column(String(20), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    publisher = Column(String(200), nullable=True)
    publication_year = Column(Integer, nullable=True)
    genre = Column(String(100), nullable=True, index=True)
    language = Column(String(50), nullable=False, default="English")
    page_count = Column(Integer, nullable=True)
    cover_image_url = Column(String(500), nullable=True)
    
    # Inventory management
    status = Column(Enum(BookStatus), nullable=False, default=BookStatus.AVAILABLE)
    total_copies = Column(Integer, nullable=False, default=1)
    available_copies = Column(Integer, nullable=False, default=1)
    
    # Metadata
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    created_by = relationship("User", back_populates="created_books")
    borrowings = relationship("BorrowingRecord", back_populates="book")
    
    def __repr__(self):
        return f"<Book(id={self.id}, title='{self.title}', isbn='{self.isbn}')>"
    
    @property
    def borrowed_copies(self):
        """Get number of borrowed copies."""
        return self.total_copies - self.available_copies
    
    def can_be_borrowed(self):
        """Check if book can be borrowed."""
        return (
            self.status == BookStatus.AVAILABLE and
            self.available_copies > 0
        )
    
    def borrow(self):
        """Borrow a copy of the book."""
        if not self.can_be_borrowed():
            return False
        
        self.available_copies -= 1
        if self.available_copies == 0:
            self.status = BookStatus.BORROWED
        return True
    
    def return_copy(self):
        """Return a copy of the book."""
        if self.available_copies >= self.total_copies:
            return False
        
        self.available_copies += 1
        if self.status == BookStatus.BORROWED and self.available_copies > 0:
            self.status = BookStatus.AVAILABLE
        return True
'''
    
    # Write book model
    book_path = Path("app/models/book.py")
    book_path.write_text(book_model)
    print(f"✅ Created book model: {book_path}")
    
    # Create borrowing model
    borrowing_model = '''"""
Borrowing model for book borrowing records.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.models.base import Base


class BorrowingStatus(enum.Enum):
    """Borrowing status enumeration."""
    ACTIVE = "active"
    RETURNED = "returned"
    OVERDUE = "overdue"
    LOST = "lost"
    CANCELLED = "cancelled"


class BorrowingRecord(Base):
    """Borrowing record model."""
    
    __tablename__ = "borrowing_records"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Foreign keys
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Borrowing details
    borrowed_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    returned_date = Column(DateTime, nullable=True)
    
    # Status and fines
    status = Column(Enum(BorrowingStatus), nullable=False, default=BorrowingStatus.ACTIVE)
    fine_amount = Column(Numeric(10, 2), nullable=False, default=0.00)
    fine_paid = Column(Boolean, nullable=False, default=False)
    
    # Notes
    notes = Column(String(500), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    book = relationship("Book", back_populates="borrowings")
    user = relationship("User", back_populates="borrowings")
    
    def __repr__(self):
        return f"<BorrowingRecord(id={self.id}, book_id={self.book_id}, user_id={self.user_id})>"
    
    @property
    def is_overdue(self):
        """Check if borrowing is overdue."""
        if self.status == BorrowingStatus.RETURNED:
            return False
        return datetime.utcnow() > self.due_date
    
    @property
    def days_overdue(self):
        """Get number of days overdue."""
        if not self.is_overdue:
            return 0
        return (datetime.utcnow() - self.due_date).days
    
    def calculate_fine(self, daily_fine_rate=0.50):
        """Calculate fine for overdue borrowing."""
        if not self.is_overdue:
            return 0.00
        
        days_overdue = self.days_overdue
        return round(days_overdue * daily_fine_rate, 2)
'''
    
    borrowing_path = Path("app/models/borrowing.py")
    borrowing_path.write_text(borrowing_model)
    print(f"✅ Created borrowing model: {borrowing_path}")
    
    # Update user model to include borrowing relationship
    user_model_path = Path("app/models/user.py")
    user_content = user_model_path.read_text()
    
    # Add borrowing relationship if not already there
    if "borrowings = relationship" not in user_content:
        # Find the right place to add the relationship
        lines = user_content.split('\n')
        for i, line in enumerate(lines):
            if 'class User' in line:
                # Add after the class definition
                insert_index = i + 1
                while insert_index < len(lines) and lines[insert_index].strip().startswith('"""'):
                    insert_index += 1
                lines.insert(insert_index, '    borrowings = relationship("BorrowingRecord", back_populates="user")')
                break
        
        user_model_path.write_text('\n'.join(lines))
        print("✅ Updated user model with borrowing relationship")
    
    return True

def create_book_service():
    """Create complete book service."""
    print("Creating book service...")
    
    book_service = '''"""
Complete book service for business logic.
Covers: SCRUM-18, SCRUM-19, SCRUM-27
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from datetime import datetime, timedelta
import logging

from app.models.book import Book, BookStatus
from app.models.borrowing import BorrowingRecord, BorrowingStatus
from app.schemas.book import BookCreate, BookUpdate, BookSearchParams
from app.schemas.borrowing import BorrowCreate, BorrowReturn
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BookService:
    """Service for book operations."""
    
    # Borrowing configuration
    BORROWING_PERIOD_DAYS = 14
    DAILY_FINE_RATE = 0.50  # $0.50 per day
    MAX_BORROWINGS_PER_USER = 5
    
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
            # Update existing book's copies
            existing_book.total_copies += book_data.total_copies
            existing_book.available_copies += book_data.available_copies
            existing_book.updated_at = datetime.utcnow()
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
    async def delete_book(book_id: int, db: AsyncSession) -> Tuple[bool, str]:
        """Delete a book."""
        logger.info(f"Deleting book: {book_id}")
        
        book = await BookService.get_book(book_id, db)
        if not book:
            logger.warning(f"Book not found: {book_id}")
            return False, "Book not found"
        
        # Check if book has active borrowings
        query = select(BorrowingRecord).where(
            BorrowingRecord.book_id == book_id,
            BorrowingRecord.status == BorrowingStatus.ACTIVE
        )
        result = await db.execute(query)
        active_borrowings = result.scalars().all()
        
        if active_borrowings:
            logger.warning(f"Cannot delete book {book_id} - has {len(active_borrowings)} active borrowings")
            return False, f"Cannot delete book with {len(active_borrowings)} active borrowings"
        
        await db.delete(book)
        await db.commit()
        
        logger.info(f"Book deleted: {book_id}")
        return True, "Book deleted successfully"
    
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
        
        # Apply pagination and ordering
        query = query.order_by(desc(Book.created_at)).offset(skip).limit(limit)
        
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
        
        # Total copies
        total_copies_query = select(func.sum(Book.total_copies))
        total_copies_result = await db.execute(total_copies_query)
        total_copies = total_copies_result.scalar() or 0
        
        return {
            "total_books": total_books,
            "total_copies": total_copies,
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
                update_dict = update_data.dict(exclude