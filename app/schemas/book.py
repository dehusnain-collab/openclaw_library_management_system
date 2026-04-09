"""
Book schemas for API requests and responses.
Covers: SCRUM-18, SCRUM-19, SCRUM-27
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
    """Base book schema with common fields."""
    title: str = Field(..., min_length=1, max_length=500, description="Book title")
    author: str = Field(..., min_length=1, max_length=200, description="Book author")
    isbn: str = Field(..., min_length=10, max_length=20, description="ISBN number")
    description: Optional[str] = Field(None, max_length=2000, description="Book description")
    publisher: Optional[str] = Field(None, max_length=200, description="Publisher name")
    publication_year: Optional[int] = Field(None, ge=1000, le=2100, description="Year of publication")
    genre: Optional[str] = Field(None, max_length=100, description="Book genre")
    language: str = Field(default="English", max_length=50, description="Book language")
    page_count: Optional[int] = Field(None, ge=1, description="Number of pages")
    cover_image_url: Optional[str] = Field(None, max_length=500, description="Cover image URL")
    
    @validator('isbn')
    def validate_isbn(cls, v):
        """Validate ISBN format."""
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
    """Schema for creating a new book."""
    total_copies: int = Field(default=1, ge=1, description="Total number of copies")
    available_copies: int = Field(default=1, ge=0, description="Number of available copies")
    
    @validator('available_copies')
    def validate_available_copies(cls, v, values):
        """Validate available copies don't exceed total copies."""
        if 'total_copies' in values and v > values['total_copies']:
            raise ValueError('Available copies cannot exceed total copies')
        return v


class BookUpdate(BaseModel):
    """Schema for updating an existing book."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    author: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    publisher: Optional[str] = Field(None, max_length=200)
    publication_year: Optional[int] = Field(None, ge=1000, le=2100)
    genre: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field(None, max_length=50)
    page_count: Optional[int] = Field(None, ge=1)
    cover_image_url: Optional[str] = Field(None, max_length=500)
    status: Optional[BookStatus] = Field(None, description="Book status")
    total_copies: Optional[int] = Field(None, ge=1)
    available_copies: Optional[int] = Field(None, ge=0)


class BookResponse(BookBase):
    """Schema for book API response."""
    id: int = Field(..., description="Book ID")
    status: BookStatus = Field(..., description="Current book status")
    total_copies: int = Field(..., ge=1, description="Total number of copies")
    available_copies: int = Field(..., ge=0, description="Number of available copies")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by_id: Optional[int] = Field(None, description="ID of user who created the book")
    
    class Config:
        from_attributes = True


class BookSearchParams(BaseModel):
    """Schema for book search parameters."""
    query: Optional[str] = Field(None, min_length=1, max_length=100, description="Search query")
    author: Optional[str] = Field(None, min_length=1, max_length=100, description="Filter by author")
    genre: Optional[str] = Field(None, min_length=1, max_length=100, description="Filter by genre")
    status: Optional[BookStatus] = Field(None, description="Filter by status")
    min_year: Optional[int] = Field(None, ge=1000, le=2100, description="Minimum publication year")
    max_year: Optional[int] = Field(None, ge=1000, le=2100, description="Maximum publication year")
    language: Optional[str] = Field(None, min_length=1, max_length=50, description="Filter by language")
    available_only: bool = Field(default=False, description="Only show available books")
    
    class Config:
        use_enum_values = True


class BookBulkCreate(BaseModel):
    """Schema for bulk book creation."""
    books: List[BookCreate] = Field(..., min_items=1, max_items=100, description="List of books to create")


class BookBulkUpdate(BaseModel):
    """Schema for bulk book update."""
    book_ids: List[int] = Field(..., min_items=1, max_items=100, description="List of book IDs to update")
    update_data: BookUpdate = Field(..., description="Update data to apply to all books")


class BookStatsResponse(BaseModel):
    """Schema for book statistics response."""
    total_books: int = Field(..., description="Total number of books")
    available_books: int = Field(..., description="Number of available books")
    borrowed_books: int = Field(..., description="Number of borrowed books")
    books_by_genre: dict = Field(..., description="Books count by genre")
    books_by_status: dict = Field(..., description="Books count by status")
    books_by_language: dict = Field(..., description="Books count by language")
    average_copies_per_book: float = Field(..., description="Average copies per book")


class BookSimpleResponse(BaseModel):
    """Simplified book response for lists."""
    id: int
    title: str
    author: str
    isbn: str
    status: BookStatus
    available_copies: int
    total_copies: int
    
    class Config:
        from_attributes = True