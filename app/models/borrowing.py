"""
Borrowing record model for the Library Management System.
"""
from sqlalchemy import Column, Integer, DateTime, Numeric, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import BaseModel


class BorrowingRecord(BaseModel):
    """
    Borrowing record model tracking book borrowings.
    
    Attributes:
        user_id: ID of user who borrowed the book
        book_id: ID of borrowed book
        borrow_date: Date when book was borrowed
        due_date: Date when book is due for return
        return_date: Date when book was returned (null if not returned)
        fine_amount: Fine amount if returned late
        is_overdue: Whether the book is overdue
        status: Borrowing status (borrowed, returned, overdue)
    """
    
    __tablename__ = "borrowing_records"
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    borrow_date = Column(DateTime, default=func.now(), nullable=False)
    due_date = Column(DateTime, nullable=False)
    return_date = Column(DateTime, nullable=True)
    fine_amount = Column(Numeric(10, 2), default=0.0, nullable=False)
    is_overdue = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="borrowing_records")
    book = relationship("Book", back_populates="borrowing_records")
    
    def __repr__(self) -> str:
        return f"<BorrowingRecord(id={self.id}, user_id={self.user_id}, book_id={self.book_id})>"
    
    @property
    def status(self) -> str:
        """Get borrowing status."""
        if self.return_date:
            return "returned"
        elif self.is_overdue:
            return "overdue"
        else:
            return "borrowed"
    
    @property
    def days_overdue(self) -> int:
        """Calculate number of days overdue."""
        from datetime import datetime
        
        if self.return_date:
            # Book has been returned
            if self.return_date > self.due_date:
                overdue_days = (self.return_date - self.due_date).days
                return max(0, overdue_days)
            return 0
        else:
            # Book not returned yet
            now = datetime.utcnow()
            if now > self.due_date:
                overdue_days = (now - self.due_date).days
                return max(0, overdue_days)
            return 0
    
    def calculate_fine(self, daily_fine_rate: float = 1.0) -> float:
        """
        Calculate fine based on overdue days.
        
        Args:
            daily_fine_rate: Fine amount per overdue day
            
        Returns:
            Calculated fine amount
        """
        overdue_days = self.days_overdue
        return float(overdue_days * daily_fine_rate)
    
    def update_overdue_status(self) -> None:
        """Update overdue status based on current date."""
        from datetime import datetime
        
        if not self.return_date:
            now = datetime.utcnow()
            self.is_overdue = now > self.due_date
    
    def to_dict(self, exclude: list = None) -> dict:
        """Convert borrowing record to dictionary with additional fields."""
        data = super().to_dict(exclude=exclude)
        data["status"] = self.status
        data["days_overdue"] = self.days_overdue
        return data