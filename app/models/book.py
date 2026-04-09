"""
Book model for the Library Management System.
"""
from sqlalchemy import Column, String, Integer, Text, Numeric, Date, Boolean
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Book(BaseModel):
    """
    Book model representing books in the library.
    
    Attributes:
        title: Book title
        author: Book author
        isbn: International Standard Book Number (unique)
        description: Book description
        category: Book category/genre
        publisher: Publisher name
        publication_year: Year of publication
        total_copies: Total number of copies owned
        available_copies: Number of copies currently available
        cover_image_url: URL to book cover image
        language: Book language
        pages: Number of pages
        price: Book price (optional)
        is_available: Whether book is available for borrowing
    """
    
    __tablename__ = "books"
    
    title = Column(String(255), nullable=False, index=True)
    author = Column(String(255), nullable=False, index=True)
    isbn = Column(String(20), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, index=True)
    publisher = Column(String(255), nullable=True)
    publication_year = Column(Integer, nullable=True)
    total_copies = Column(Integer, default=1, nullable=False)
    available_copies = Column(Integer, default=1, nullable=False)
    cover_image_url = Column(String(500), nullable=True)
    language = Column(String(50), default="English", nullable=False)
    pages = Column(Integer, nullable=True)
    price = Column(Numeric(10, 2), nullable=True)
    is_available = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    borrowing_records = relationship("BorrowingRecord", back_populates="book")
    
    def __repr__(self) -> str:
        return f"<Book(id={self.id}, title={self.title}, author={self.author})>"
    
    @property
    def is_borrowable(self) -> bool:
        """Check if book can be borrowed."""
        return self.is_available and self.available_copies > 0
    
    def update_availability(self) -> None:
        """Update availability status based on available copies."""
        self.is_available = self.available_copies > 0
    
    def to_dict(self, exclude: list = None) -> dict:
        """Convert book to dictionary with additional computed fields."""
        data = super().to_dict(exclude=exclude)
        data["is_borrowable"] = self.is_borrowable
        return data