"""
Borrowing schemas for API requests and responses.
Covers: SCRUM-28, SCRUM-29, SCRUM-30
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


class BorrowingStatus(str, Enum):
    """Borrowing status enumeration."""
    ACTIVE = "active"
    RETURNED = "returned"
    OVERDUE = "overdue"
    LOST = "lost"
    CANCELLED = "cancelled"


class BorrowCreate(BaseModel):
    """Schema for borrowing a book."""
    book_id: int = Field(..., gt=0, description="ID of book to borrow")
    user_id: Optional[int] = Field(None, gt=0, description="ID of user borrowing the book")
    due_date: Optional[date] = Field(None, description="Due date for return")
    
    @validator('due_date')
    def validate_due_date(cls, v):
        """Validate due date is in the future."""
        if v and v <= date.today():
            raise ValueError('Due date must be in the future')
        return v


class BorrowReturn(BaseModel):
    """Schema for returning a borrowed book."""
    borrowing_id: int = Field(..., gt=0, description="ID of borrowing record")
    condition_notes: Optional[str] = Field(None, max_length=500, description="Notes on book condition")
    fine_paid: bool = Field(default=False, description="Whether fine has been paid")


class BorrowingResponse(BaseModel):
    """Schema for borrowing API response."""
    id: int = Field(..., description="Borrowing record ID")
    book_id: int = Field(..., description="Book ID")
    user_id: int = Field(..., description="User ID")
    borrowed_date: datetime = Field(..., description="Date book was borrowed")
    due_date: datetime = Field(..., description="Due date for return")
    returned_date: Optional[datetime] = Field(None, description="Date book was returned")
    status: BorrowingStatus = Field(..., description="Current borrowing status")
    fine_amount: float = Field(..., ge=0, description="Fine amount (if any)")
    fine_paid: bool = Field(..., description="Whether fine has been paid")
    notes: Optional[str] = Field(None, description="Additional notes")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class BorrowingSearchParams(BaseModel):
    """Schema for borrowing search parameters."""
    user_id: Optional[int] = Field(None, gt=0, description="Filter by user ID")
    book_id: Optional[int] = Field(None, gt=0, description="Filter by book ID")
    status: Optional[BorrowingStatus] = Field(None, description="Filter by status")
    overdue_only: bool = Field(default=False, description="Only show overdue borrowings")
    start_date: Optional[date] = Field(None, description="Start date for filtering")
    end_date: Optional[date] = Field(None, description="End date for filtering")


class FinePayment(BaseModel):
    """Schema for fine payment."""
    amount: float = Field(..., gt=0, description="Payment amount")
    payment_method: str = Field(..., min_length=1, max_length=50, description="Payment method")
    transaction_id: Optional[str] = Field(None, max_length=100, description="Transaction ID")


class BorrowingStatsResponse(BaseModel):
    """Schema for borrowing statistics response."""
    total_borrowings: int = Field(..., description="Total number of borrowings")
    active_borrowings: int = Field(..., description="Number of active borrowings")
    overdue_borrowings: int = Field(..., description="Number of overdue borrowings")
    total_fines: float = Field(..., description="Total fines amount")
    unpaid_fines: float = Field(..., description="Unpaid fines amount")
    borrowings_by_month: dict = Field(..., description="Borrowings count by month")
    popular_books: List[dict] = Field(..., description="Most borrowed books")


class BorrowingSimpleResponse(BaseModel):
    """Simplified borrowing response for lists."""
    id: int
    book_id: int
    user_id: int
    borrowed_date: datetime
    due_date: datetime
    status: BorrowingStatus
    fine_amount: float
    fine_paid: bool
    
    class Config:
        from_attributes = True


class BorrowingUpdate(BaseModel):
    """Schema for updating a borrowing record."""
    due_date: Optional[datetime] = Field(None, description="New due date")
    status: Optional[BorrowingStatus] = Field(None, description="New status")
    fine_amount: Optional[float] = Field(None, ge=0, description="Updated fine amount")
    fine_paid: Optional[bool] = Field(None, description="Fine payment status")
    notes: Optional[str] = Field(None, max_length=500, description="Additional notes")


class BorrowingBulkUpdate(BaseModel):
    """Schema for bulk borrowing update."""
    borrowing_ids: List[int] = Field(..., min_items=1, max_items=100, description="List of borrowing IDs")
    update_data: BorrowingUpdate = Field(..., description="Update data to apply")