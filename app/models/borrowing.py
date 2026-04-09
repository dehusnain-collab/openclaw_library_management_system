"""
Borrowing model for tracking book borrowings.
Covers: SCRUM-28, SCRUM-29, SCRUM-30
"""
from sqlalchemy import Column, Integer, DateTime, Numeric, Boolean, String, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.models.base import BaseModel


class BorrowingStatus(enum.Enum):
    """Borrowing status enumeration."""
    ACTIVE = "active"
    RETURNED = "returned"
    OVERDUE = "overdue"
    LOST = "lost"
    CANCELLED = "cancelled"


class BorrowingRecord(BaseModel):
    """
    Borrowing record model for tracking book borrowings.
    
    Attributes:
        book_id: ID of borrowed book
        user_id: ID of user who borrowed the book
        borrowed_date: Date book was borrowed
        due_date: Due date for return
        returned_date: Date book was returned
        status: Current borrowing status
        fine_amount: Fine amount (if overdue)
        fine_paid: Whether fine has been paid
        notes: Additional notes
    """
    
    __tablename__ = "borrowing_records"
    
    # Foreign keys
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Borrowing details
    borrowed_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    due_date = Column(DateTime, nullable=False)
    returned_date = Column(DateTime, nullable=True)
    
    # Status and fines
    status = Column(Enum(BorrowingStatus), default=BorrowingStatus.ACTIVE, nullable=False)
    fine_amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    fine_paid = Column(Boolean, default=False, nullable=False)
    
    # Notes
    notes = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    book = relationship("Book", back_populates="borrowing_records")
    user = relationship("User", back_populates="borrowing_records")
    
    def __repr__(self) -> str:
        return f"<BorrowingRecord(id={self.id}, book_id={self.book_id}, user_id={self.user_id}, status={self.status})>"
    
    @property
    def is_overdue(self) -> bool:
        """Check if borrowing is overdue."""
        if self.status != BorrowingStatus.ACTIVE:
            return False
        return datetime.utcnow() > self.due_date
    
    @property
    def days_overdue(self) -> int:
        """Get number of days overdue."""
        if not self.is_overdue:
            return 0
        return (datetime.utcnow() - self.due_date).days
    
    def calculate_fine(self, daily_fine_rate: float = 0.50) -> float:
        """
        Calculate fine for overdue borrowing.
        
        Args:
            daily_fine_rate: Fine per day (default: $0.50)
            
        Returns:
            Calculated fine amount
        """
        if not self.is_overdue:
            return 0.00
        
        days_overdue = self.days_overdue
        return round(days_overdue * daily_fine_rate, 2)
    
    def mark_as_returned(self, fine_amount: float = 0.0) -> None:
        """
        Mark borrowing as returned.
        
        Args:
            fine_amount: Fine amount (if any)
        """
        self.returned_date = datetime.utcnow()
        self.status = BorrowingStatus.RETURNED
        self.fine_amount = fine_amount
        self.updated_at = datetime.utcnow()
    
    def mark_as_overdue(self) -> None:
        """Mark borrowing as overdue."""
        self.status = BorrowingStatus.OVERDUE
        self.fine_amount = self.calculate_fine()
        self.updated_at = datetime.utcnow()
    
    def pay_fine(self, amount: float) -> bool:
        """
        Pay fine for borrowing.
        
        Args:
            amount: Payment amount
            
        Returns:
            True if payment successful, False otherwise
        """
        if amount <= 0:
            return False
        
        if amount >= self.fine_amount:
            self.fine_paid = True
            self.updated_at = datetime.utcnow()
            return True
        
        # Partial payment
        self.fine_amount -= amount
        self.updated_at = datetime.utcnow()
        return True
    
    def to_dict(self, exclude: list = None) -> dict:
        """Convert borrowing record to dictionary with additional computed fields."""
        data = super().to_dict(exclude=exclude)
        data["is_overdue"] = self.is_overdue
        data["days_overdue"] = self.days_overdue
        data["status"] = self.status.value
        return data