#!/usr/bin/env python3
"""
Complete implementation of Sprint 3 and Sprint 4.
Creates all missing files for book management, borrowing system, caching, background jobs, etc.
"""

import os
import sys
from pathlib import Path

def create_sprint3_files():
    """Create all Sprint 3 files."""
    print("=" * 60)
    print("🚀 CREATING SPRINT 3: CORE FEATURES & PERFORMANCE")
    print("=" * 60)
    
    # Create borrowing schemas
    print("\n📝 Creating borrowing schemas...")
    borrowing_schemas = '''"""
Borrowing schemas for API requests and responses.
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
    book_id: int = Field(..., gt=0)
    user_id: Optional[int] = Field(None, gt=0)
    due_date: Optional[date] = Field(None)
    
    @validator('due_date')
    def validate_due_date(cls, v):
        """Validate due date is in the future."""
        if v and v <= date.today():
            raise ValueError('Due date must be in the future')
        return v


class BorrowReturn(BaseModel):
    """Schema for returning a borrowed book."""
    borrowing_id: int = Field(..., gt=0)
    condition_notes: Optional[str] = Field(None, max_length=500)
    fine_paid: bool = Field(default=False)


class BorrowingResponse(BaseModel):
    """Schema for borrowing API response."""
    id: int
    book_id: int
    user_id: int
    borrowed_date: datetime
    due_date: datetime
    returned_date: Optional[datetime]
    status: BorrowingStatus
    fine_amount: float
    fine_paid: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BorrowingSearchParams(BaseModel):
    """Schema for borrowing search parameters."""
    user_id: Optional[int] = Field(None, gt=0)
    book_id: Optional[int] = Field(None, gt=0)
    status: Optional[BorrowingStatus] = None
    overdue_only: bool = Field(default=False)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class FinePayment(BaseModel):
    """Schema for fine payment."""
    amount: float = Field(..., gt=0)
    payment_method: str = Field(..., min_length=1, max_length=50)
    transaction_id: Optional[str] = Field(None, max_length=100)


class BorrowingStatsResponse(BaseModel):
    """Schema for borrowing statistics response."""
    total_borrowings: int
    active_borrowings: int
    overdue_borrowings: int
    total_fines: float
    unpaid_fines: float
    borrowings_by_month: dict
    popular_books: List[dict]
'''
    
    schemas_path = Path("app/schemas/borrowing.py")
    schemas_path.parent.mkdir(exist_ok=True)
    schemas_path.write_text(borrowing_schemas)
    print(f"✅ Created borrowing schemas: {schemas_path}")
    
    # Create borrowing service
    print("\n🔧 Creating borrowing service...")
    borrowing_service = '''"""
Borrowing service for business logic.
Covers: SCRUM-28, SCRUM-29, SCRUM-30
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from datetime import datetime, date, timedelta
import logging

from app.models.book import Book, BookStatus
from app.models.borrowing import BorrowingRecord, BorrowingStatus
from app.models.user import User
from app.schemas.borrowing import BorrowCreate, BorrowReturn, BorrowingSearchParams
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BorrowingService:
    """Service for borrowing operations."""
    
    # Configuration
    BORROWING_PERIOD_DAYS = 14
    DAILY_FINE_RATE = 0.50  # $0.50 per day
    MAX_BORROWINGS_PER_USER = 5
    
    @staticmethod
    async def borrow_book(borrow_data: BorrowCreate, db: AsyncSession) -> Optional[BorrowingRecord]:
        """Borrow a book."""
        logger.info(f"Borrowing book {borrow_data.book_id} for user {borrow_data.user_id}")
        
        # Get book
        book_query = select(Book).where(Book.id == borrow_data.book_id)
        book_result = await db.execute(book_query)
        book = book_result.scalar_one_or_none()
        
        if not book:
            logger.warning(f"Book not found: {borrow_data.book_id}")
            return None
        
        # Check if book can be borrowed
        if not book.can_be_borrowed():
            logger.warning(f"Book {book.id} cannot be borrowed (status: {book.status}, available: {book.available_copies})")
            return None
        
        # Get user
        user_query = select(User).where(User.id == borrow_data.user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"User not found: {borrow_data.user_id}")
            return None
        
        # Check user's active borrowings
        active_query = select(func.count(BorrowingRecord.id)).where(
            BorrowingRecord.user_id == borrow_data.user_id,
            BorrowingRecord.status == BorrowingStatus.ACTIVE
        )
        active_result = await db.execute(active_query)
        active_count = active_result.scalar()
        
        if active_count >= BorrowingService.MAX_BORROWINGS_PER_USER:
            logger.warning(f"User {borrow_data.user_id} has reached maximum borrowings: {active_count}")
            return None
        
        # Calculate due date
        due_date = borrow_data.due_date or date.today() + timedelta(days=BorrowingService.BORROWING_PERIOD_DAYS)
        
        # Create borrowing record
        borrowing = BorrowingRecord(
            book_id=borrow_data.book_id,
            user_id=borrow_data.user_id,
            due_date=datetime.combine(due_date, datetime.min.time()),
            status=BorrowingStatus.ACTIVE
        )
        
        # Update book availability
        book.borrow()
        
        db.add(borrowing)
        await db.commit()
        await db.refresh(borrowing)
        
        logger.info(f"Book {book.id} borrowed by user {user.id}, borrowing ID: {borrowing.id}")
        return borrowing
    
    @staticmethod
    async def return_book(return_data: BorrowReturn, db: AsyncSession) -> Tuple[bool, str, Optional[float]]:
        """Return a borrowed book."""
        logger.info(f"Returning borrowing: {return_data.borrowing_id}")
        
        # Get borrowing record
        query = select(BorrowingRecord).where(BorrowingRecord.id == return_data.borrowing_id)
        result = await db.execute(query)
        borrowing = result.scalar_one_or_none()
        
        if not borrowing:
            logger.warning(f"Borrowing not found: {return_data.borrowing_id}")
            return False, "Borrowing record not found", None
        
        if borrowing.status != BorrowingStatus.ACTIVE:
            logger.warning(f"Borrowing {borrowing.id} is not active (status: {borrowing.status})")
            return False, f"Book is not currently borrowed (status: {borrowing.status})", None
        
        # Get book
        book_query = select(Book).where(Book.id == borrowing.book_id)
        book_result = await db.execute(book_query)
        book = book_result.scalar_one_or_none()
        
        if not book:
            logger.error(f"Book not found for borrowing {borrowing.id}: {borrowing.book_id}")
            return False, "Associated book not found", None
        
        # Update borrowing record
        borrowing.returned_date = datetime.utcnow()
        borrowing.status = BorrowingStatus.RETURNED
        borrowing.notes = return_data.condition_notes
        
        # Calculate fine if overdue
        fine_amount = 0.0
        if borrowing.is_overdue:
            fine_amount = borrowing.calculate_fine(BorrowingService.DAILY_FINE_RATE)
            borrowing.fine_amount = fine_amount
        
        borrowing.fine_paid = return_data.fine_paid
        borrowing.updated_at = datetime.utcnow()
        
        # Update book availability
        book.return_copy()
        
        await db.commit()
        await db.refresh(borrowing)
        
        logger.info(f"Book {book.id} returned, borrowing ID: {borrowing.id}, fine: ${fine_amount}")
        return True, "Book returned successfully", fine_amount
    
    @staticmethod
    async def get_borrowing(borrowing_id: int, db: AsyncSession) -> Optional[BorrowingRecord]:
        """Get a borrowing record by ID."""
        query = select(BorrowingRecord).where(BorrowingRecord.id == borrowing_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def search_borrowings(
        search_params: BorrowingSearchParams,
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = None
    ) -> List[BorrowingRecord]:
        """Search borrowing records with filters."""
        logger.info(f"Searching borrowings with params: {search_params.dict()}")
        
        query = select(BorrowingRecord)
        
        # Apply filters
        filters = []
        
        if search_params.user_id:
            filters.append(BorrowingRecord.user_id == search_params.user_id)
        
        if search_params.book_id:
            filters.append(BorrowingRecord.book_id == search_params.book_id)
        
        if search_params.status:
            filters.append(BorrowingRecord.status == search_params.status)
        
        if search_params.overdue_only:
            filters.append(BorrowingRecord.status == BorrowingStatus.ACTIVE)
            filters.append(BorrowingRecord.due_date < datetime.utcnow())
        
        if search_params.start_date:
            start_datetime = datetime.combine(search_params.start_date, datetime.min.time())
            filters.append(BorrowingRecord.borrowed_date >= start_datetime)
        
        if search_params.end_date:
            end_datetime = datetime.combine(search_params.end_date, datetime.max.time())
            filters.append(BorrowingRecord.borrowed_date <= end_datetime)
        
        # Apply all filters
        if filters:
            query = query.where(and_(*filters))
        
        # Apply pagination and ordering
        query = query.order_by(desc(BorrowingRecord.borrowed_date)).offset(skip).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        borrowings = result.scalars().all()
        
        logger.info(f"Found {len(borrowings)} borrowings")
        return borrowings
    
    @staticmethod
    async def get_borrowing_stats(db: AsyncSession) -> Dict[str, Any]:
        """Get borrowing statistics."""
        logger.info("Getting borrowing statistics")
        
        # Total borrowings
        total_query = select(func.count(BorrowingRecord.id))
        total_result = await db.execute(total_query)
        total_borrowings = total_result.scalar()
        
        # Active borrowings
        active_query = select(func.count(BorrowingRecord.id)).where(
            BorrowingRecord.status == BorrowingStatus.ACTIVE
        )
        active_result = await db.execute(active_query)
        active_borrowings = active_result.scalar()
        
        # Overdue borrowings
        overdue_query = select(func.count(BorrowingRecord.id)).where(
            BorrowingRecord.status == BorrowingStatus.ACTIVE,
            BorrowingRecord.due_date < datetime.utcnow()
        )
        overdue_result = await db.execute(overdue_query)
        overdue_borrowings = overdue_result.scalar()
        
        # Total fines
        fines_query = select(func.sum(BorrowingRecord.fine_amount))
        fines_result = await db.execute(fines_query)
        total_fines = fines_result.scalar() or 0.0
        
        # Unpaid fines
        unpaid_query = select(func.sum(BorrowingRecord.fine_amount)).where(
            BorrowingRecord.fine_paid == False,
            BorrowingRecord.fine_amount > 0
        )
        unpaid_result = await db.execute(unpaid_query)
        unpaid_fines = unpaid_result.scalar() or 0.0
        
        # Borrowings by month (last 12 months)
        borrowings_by_month = {}
        for i in range(12):
            month_start = datetime.utcnow() - timedelta(days=30*i)
            month_end = month_start + timedelta(days=30)
            
            month_query = select(func.count(BorrowingRecord.id)).where(
                BorrowingRecord.borrowed_date >= month_start,
                BorrowingRecord.borrowed_date < month_end
            )
            month_result = await db.execute(month_query)
            month_count = month_result.scalar()
            
            month_key = month_start.strftime("%Y-%m")
            borrowings_by_month[month_key] = month_count
        
        # Popular books (top 10 most borrowed)
        popular_query = select(
            BorrowingRecord.book_id,
            func.count(BorrowingRecord.id).label('borrow_count')
        ).group_by(BorrowingRecord.book_id).order_by(desc('borrow_count')).limit(10)
        
        popular_result = await db.execute(popular_query)
        popular_books = [
            {"book_id": row[0], "borrow_count": row[1]}
            for row in popular_result.all()
        ]
        
        return {
            "total_borrowings": total_borrowings,
            "active_borrowings": active_borrowings,
            "overdue_borrowings": overdue_borrowings,
            "total_fines": float(total_fines),
            "unpaid_fines": float(unpaid_fines),
            "borrowings_by_month": borrowings_by_month,
            "popular_books": popular_books
        }
    
    @staticmethod
    async def update_overdue_status(db: AsyncSession) -> int:
        """Update status of overdue borrowings."""
        logger.info("Updating overdue borrowings status")
        
        # Find active borrowings that are overdue
        query = select(BorrowingRecord).where(
            BorrowingRecord.status == BorrowingStatus.ACTIVE,
            BorrowingRecord.due_date < datetime.utcnow()
        )
        
        result = await db.execute(query)
        overdue_borrowings = result.scalars().all()
        
        updated_count = 0
        for borrowing in overdue_borrowings:
            borrowing.status = BorrowingStatus.OVERDUE
            # Calculate and update fine
            borrowing.fine_amount = borrowing.calculate_fine(BorrowingService.DAILY_FINE_RATE)
            borrowing.updated_at = datetime.utcnow()
            updated_count += 1
        
        if updated_count > 0:
            await db.commit()
        
        logger.info(f"Updated {updated_count} borrowings to OVERDUE status")
        return updated_count
    
    @staticmethod
    async def get_user_borrowings(user_id: int, db: AsyncSession) -> List[BorrowingRecord]:
        """Get all borrowings for a user."""
        query = select(BorrowingRecord).where(
            BorrowingRecord.user_id == user_id
        ).order_by(desc(BorrowingRecord.borrowed_date))
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def pay_fine(borrowing_id: int, payment_data: dict, db: AsyncSession) -> Tuple[bool, str]:
        """Pay fine for a borrowing."""
        logger.info(f"Paying fine for borrowing: {borrowing_id}")
        
        borrowing = await BorrowingService.get_borrowing(borrowing_id, db)
        if not borrowing:
            return False, "Borrowing not found"
        
        if borrowing.fine_amount <= 0:
            return False, "No fine to pay"
        
        if borrowing.fine_paid:
            return False, "Fine already paid"
        
        # Update borrowing record
        borrowing.fine_paid = True
        borrowing.updated_at = datetime.utcnow()
        
        # In a real system, you would record the payment transaction
        # For now, we just mark it as paid
        
        await db.commit()
        
        logger.info(f"Fine paid for borrowing {borrowing_id}: ${borrowing.fine_amount}")
        return True, f"Fine of ${borrowing.fine_amount} paid successfully"
'''
    
    service_path = Path("app/services/borrowing_service.py")
    service_path.parent.mkdir(exist_ok=True)
    service_path.write_text(borrowing_service)
    print(f"✅ Created borrowing service: {service_path}")
    
    # Create search service
    print("\n🔍 Creating search service...")
    search_service = '''"""
Search service for book discovery.
Covers: SCRUM-31, SCRUM-32
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
import logging

from app.models.book import Book, BookStatus
from app.schemas.book import BookSearchParams
from app.utils.logging import get_log