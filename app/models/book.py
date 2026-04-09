"""
Book model for the Library Management System.
Covers: SCRUM-18, SCRUM-19, SCRUM-27
"""
from sqlalchemy import Column, String, Integer, Text, Numeric, Boolean, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.models.base import BaseModel


class BookStatus(enum.Enum):
    """Book status enumeration."""
    AVAILABLE = "available"
    BORROWED = "borrowed"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"
    LOST = "lost"


class Book(BaseModel):
    """
    Book model representing books in the library.
    
    Attributes:
        title: Book title
        author: Book author
        isbn: International Standard Book Number (unique)
        description: Book description
        genre: Book genre/category
        publisher: Publisher name
        publication_year: Year of publication
        total_copies: Total number of copies owned
        available_copies: Number of copies currently available
        cover_image_url: URL to book cover image
        language: Book language
        page_count: Number of pages
        status: Current book status
        created_by_id: ID of user who created the book
    """
    
    __tablename__ = "books"
    
    title = Column(String(500), nullable=False, index=True)
    author = Column(String(200), nullable=False, index=True)
    isbn = Column(String(20), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    genre = Column(String(100), nullable=True, index=True)
    publisher = Column(String(200), nullable=True)
    publication_year = Column(Integer, nullable=True)
    total_copies = Column(Integer, default=1, nullable=False)
    available_copies = Column(Integer, default=1, nullable=False)
    cover_image_url = Column(String(500), nullable=True)
    language = Column(String(50), default="English", nullable=False)
    page_count = Column(Integer, nullable=True)
    status = Column(Enum(BookStatus), default=BookStatus.AVAILABLE, nullable=False)
    
    # Foreign key to user who created the book
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    borrowing_records = relationship("BorrowingRecord", back_populates="book")
    created_by = relationship("User", back_populates="created_books")
    
    def __repr__(self) -> str:
        return f"<Book(id={self.id}, title={self.title}, author={self.author}, status={self.status})>"
    
    @property
    def is_borrowable(self) -> bool:
        """Check if book can be borrowed."""
        return self.status == BookStatus.AVAILABLE and self.available_copies > 0
    
    @property
    def borrowed_copies(self) -> int:
        """Get number of borrowed copies."""
        return self.total_copies - self.available_copies
    
    def borrow_copy(self) -> bool:
        """Borrow one copy of the book."""
        if not self.is_borrowable:
            return False
        
        self.available_copies -= 1
        if self.available_copies == 0:
            self.status = BookStatus.BORROWED
        self.updated_at = datetime.utcnow()
        return True
    
    def return_copy(self) -> bool:
        """Return one copy of the book."""
        if self.available_copies >= self.total_copies:
            return False
        
        self.available_copies += 1
        if self.status == BookStatus.BORROWED and self.available_copies > 0:
            self.status = BookStatus.AVAILABLE
        self.updated_at = datetime.utcnow()
        return True
    
    def update_status(self) -> None:
        """Update status based on available copies."""
        if self.available_copies > 0:
            self.status = BookStatus.AVAILABLE
        else:
            self.status = BookStatus.BORROWED
    
    def to_dict(self, exclude: list = None) -> dict:
        """Convert book to dictionary with additional computed fields."""
        data = super().to_dict(exclude=exclude)
        data["is_borrowable"] = self.is_borrowable
        data["borrowed_copies"] = self.borrowed_copies
        data["status"] = self.status.value
        return data