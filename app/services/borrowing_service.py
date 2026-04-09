"""
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
        """
        Borrow a book.
        
        Args:
            borrow_data: Borrowing data
            db: Database session
            
        Returns:
            Borrowing record if successful, None otherwise
        """
        logger.info(f"Borrowing book {borrow_data.book_id} for user {borrow_data.user_id}")
        
        try:
            # Get book
            book_query = select(Book).where(Book.id == borrow_data.book_id)
            book_result = await db.execute(book_query)
            book = book_result.scalar_one_or_none()
            
            if not book:
                logger.warning(f"Book not found: {borrow_data.book_id}")
                return None
            
            # Check if book can be borrowed
            if not book.is_borrowable:
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
            due_date = borrow_data.due_date
            if not due_date:
                due_date = datetime.utcnow() + timedelta(days=BorrowingService.BORROWING_PERIOD_DAYS)
            else:
                due_date = datetime.combine(due_date, datetime.min.time())
            
            # Create borrowing record
            borrowing = BorrowingRecord(
                book_id=borrow_data.book_id,
                user_id=borrow_data.user_id,
                due_date=due_date,
                status=BorrowingStatus.ACTIVE
            )
            
            # Update book availability
            book.borrow_copy()
            
            db.add(borrowing)
            await db.commit()
            await db.refresh(borrowing)
            
            logger.info(f"Book {book.id} borrowed by user {user.id}, borrowing ID: {borrowing.id}")
            return borrowing
            
        except Exception as e:
            logger.error(f"Failed to borrow book: {e}")
            await db.rollback()
            return None
    
    @staticmethod
    async def return_book(return_data: BorrowReturn, db: AsyncSession) -> Tuple[bool, str, Optional[float]]:
        """
        Return a borrowed book.
        
        Args:
            return_data: Return data
            db: Database session
            
        Returns:
            Tuple of (success, message, fine_amount)
        """
        logger.info(f"Returning borrowing: {return_data.borrowing_id}")
        
        try:
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
            
            # Calculate fine if overdue
            fine_amount = 0.0
            if borrowing.is_overdue:
                fine_amount = borrowing.calculate_fine(BorrowingService.DAILY_FINE_RATE)
            
            # Update borrowing record
            borrowing.mark_as_returned(fine_amount)
            borrowing.notes = return_data.condition_notes
            borrowing.fine_paid = return_data.fine_paid
            
            # Update book availability
            book.return_copy()
            
            await db.commit()
            await db.refresh(borrowing)
            
            logger.info(f"Book {book.id} returned, borrowing ID: {borrowing.id}, fine: ${fine_amount}")
            return True, "Book returned successfully", fine_amount
            
        except Exception as e:
            logger.error(f"Failed to return book: {e}")
            await db.rollback()
            return False, f"Failed to return book: {str(e)}", None
    
    @staticmethod
    async def get_borrowing(borrowing_id: int, db: AsyncSession) -> Optional[BorrowingRecord]:
        """
        Get a borrowing record by ID.
        
        Args:
            borrowing_id: Borrowing ID
            db: Database session
            
        Returns:
            Borrowing record if found, None otherwise
        """
        logger.debug(f"Getting borrowing: {borrowing_id}")
        
        try:
            query = select(BorrowingRecord).where(BorrowingRecord.id == borrowing_id)
            result = await db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get borrowing {borrowing_id}: {e}")
            return None
    
    @staticmethod
    async def search_borrowings(
        search_params: BorrowingSearchParams,
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = None
    ) -> List[BorrowingRecord]:
        """
        Search borrowing records with filters.
        
        Args:
            search_params: Search parameters
            skip: Number of records to skip
            limit: Maximum number of records to return
            db: Database session
            
        Returns:
            List of borrowing records matching search criteria
        """
        logger.info(f"Searching borrowings with params: {search_params.dict()}")
        
        try:
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
            
            logger.info(f"Found {len(borrowings)} borrowings matching search criteria")
            return borrowings
            
        except Exception as e:
            logger.error(f"Failed to search borrowings: {e}")
            return []
    
    @staticmethod
    async def get_borrowing_stats(db: AsyncSession) -> Dict[str, Any]:
        """
        Get borrowing statistics.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with borrowing statistics
        """
        logger.info("Getting borrowing statistics")
        
        try:
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
            
        except Exception as e:
            logger.error(f"Failed to get borrowing statistics: {e}")
            return {
                "total_borrowings": 0,
                "active_borrowings": 0,
                "overdue_borrowings": 0,
                "total_fines": 0.0,
                "unpaid_fines": 0.0,
                "borrowings_by_month": {},
                "popular_books": []
            }
    
    @staticmethod
    async def update_overdue_status(db: AsyncSession) -> int:
        """
        Update status of overdue borrowings.
        
        Args:
            db: Database session
            
        Returns:
            Number of borrowings updated
        """
        logger.info("Updating overdue borrowings status")
        
        try:
            # Find active borrowings that are overdue
            query = select(BorrowingRecord).where(
                BorrowingRecord.status == BorrowingStatus.ACTIVE,
                BorrowingRecord.due_date < datetime.utcnow()
            )
            
            result = await db.execute(query)
            overdue_borrowings = result.scalars().all()
            
            updated_count = 0
            for borrowing in overdue_borrowings:
                borrowing.mark_as_overdue()
                updated_count += 1
            
            if updated_count > 0:
                await db.commit()
            
            logger.info(f"Updated {updated_count} borrowings to OVERDUE status")
            return updated_count
            
        except Exception as e:
            logger.error(f"Failed to update overdue status: {e}")
            await db.rollback()
            return 0
    
    @staticmethod
    async def get_user_borrowings(user_id: int, db: AsyncSession) -> List[BorrowingRecord]:
        """
        Get all borrowings for a user.
        
        Args:
            user_id: User ID
            db: Database session
            
        Returns:
            List of user's borrowing records
        """
        logger.debug(f"Getting borrowings for user: {user_id}")
        
        try:
            query = select(BorrowingRecord).where(
                BorrowingRecord.user_id == user_id
            ).order_by(desc(BorrowingRecord.borrowed_date))
            
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get user borrowings: {e}")
            return []
    
    @staticmethod
    async def pay_fine(borrowing_id: int, payment_amount: float, db: AsyncSession) -> Tuple[bool, str]:
        """
        Pay fine for a borrowing.
        
        Args:
            borrowing_id: Borrowing ID
            payment_amount: Payment amount
            db: Database session
            
        Returns:
            Tuple of (success, message)
        """
        logger.info(f"Paying fine for borrowing: {borrowing_id}, amount: ${payment_amount}")
        
        try:
            borrowing = await BorrowingService.get_borrowing(borrowing_id, db)
            if not borrowing:
                return False, "Borrowing not found"
            
            if borrowing.fine_amount <= 0:
                return False, "No fine to pay"
            
            if borrowing.fine_paid:
                return False, "Fine already paid"
            
            # Update borrowing record
            success = borrowing.pay_fine(payment_amount)
            
            if success:
                await db.commit()
                logger.info(f"Fine paid for borrowing {borrowing_id}: ${payment_amount}")
                return True, f"Fine payment of ${payment_amount} processed successfully"
            else:
                return False, "Payment amount must be greater than 0"
            
        except Exception as e:
            logger.error(f"Failed to pay fine: {e}")
            await db.rollback()
            return False, f"Failed to process payment: {str(e)}"
    
    @staticmethod
    async def get_overdue_borrowings(db: AsyncSession, limit: int = 100) -> List[BorrowingRecord]:
        """
        Get overdue borrowings.
        
        Args:
            db: Database session
            limit: Maximum number of records to return
            
        Returns:
            List of overdue borrowing records
        """
        logger.debug(f"Getting {limit} overdue borrowings")
        
        try:
            query = select(BorrowingRecord).where(
                BorrowingRecord.status == BorrowingStatus.ACTIVE,
                BorrowingRecord.due_date < datetime.utcnow()
            ).order_by(BorrowingRecord.due_date).limit(limit)
            
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get overdue borrowings: {e}")
            return []