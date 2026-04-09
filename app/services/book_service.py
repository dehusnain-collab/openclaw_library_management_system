"""
Book service for business logic.
Covers: SCRUM-18, SCRUM-19, SCRUM-27
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from datetime import datetime
import logging

from app.models.book import Book, BookStatus
from app.schemas.book import BookCreate, BookUpdate, BookSearchParams
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BookService:
    """Service for book operations."""
    
    @staticmethod
    async def create_book(book_data: BookCreate, created_by_id: int, db: AsyncSession) -> Book:
        """
        Create a new book.
        
        Args:
            book_data: Book creation data
            created_by_id: ID of user creating the book
            db: Database session
            
        Returns:
            Created book
        """
        logger.info(f"Creating book: {book_data.title}")
        
        try:
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
            
            logger.info(f"Book created successfully: {book.id} - {book.title}")
            return book
            
        except Exception as e:
            logger.error(f"Failed to create book: {e}")
            await db.rollback()
            raise
    
    @staticmethod
    async def get_book(book_id: int, db: AsyncSession) -> Optional[Book]:
        """
        Get a book by ID.
        
        Args:
            book_id: Book ID
            db: Database session
            
        Returns:
            Book if found, None otherwise
        """
        logger.debug(f"Getting book: {book_id}")
        
        try:
            query = select(Book).where(Book.id == book_id)
            result = await db.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Failed to get book {book_id}: {e}")
            return None
    
    @staticmethod
    async def update_book(book_id: int, update_data: BookUpdate, db: AsyncSession) -> Optional[Book]:
        """
        Update a book.
        
        Args:
            book_id: Book ID
            update_data: Update data
            db: Database session
            
        Returns:
            Updated book if successful, None otherwise
        """
        logger.info(f"Updating book: {book_id}")
        
        try:
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
            
            logger.info(f"Book updated successfully: {book_id}")
            return book
            
        except Exception as e:
            logger.error(f"Failed to update book {book_id}: {e}")
            await db.rollback()
            return None
    
    @staticmethod
    async def delete_book(book_id: int, db: AsyncSession) -> Tuple[bool, str]:
        """
        Delete a book.
        
        Args:
            book_id: Book ID
            db: Database session
            
        Returns:
            Tuple of (success, message)
        """
        logger.info(f"Deleting book: {book_id}")
        
        try:
            book = await BookService.get_book(book_id, db)
            if not book:
                return False, f"Book not found: {book_id}"
            
            # Check if book has active borrowings
            # This would require checking borrowing records
            # For now, we'll check if all copies are available
            if book.available_copies < book.total_copies:
                return False, f"Cannot delete book with borrowed copies"
            
            await db.delete(book)
            await db.commit()
            
            logger.info(f"Book deleted successfully: {book_id}")
            return True, "Book deleted successfully"
            
        except Exception as e:
            logger.error(f"Failed to delete book {book_id}: {e}")
            await db.rollback()
            return False, f"Failed to delete book: {str(e)}"
    
    @staticmethod
    async def search_books(
        search_params: BookSearchParams,
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = None
    ) -> List[Book]:
        """
        Search books with filters.
        
        Args:
            search_params: Search parameters
            skip: Number of records to skip
            limit: Maximum number of records to return
            db: Database session
            
        Returns:
            List of books matching search criteria
        """
        logger.info(f"Searching books with params: {search_params.dict()}")
        
        try:
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
            
            logger.info(f"Found {len(books)} books matching search criteria")
            return books
            
        except Exception as e:
            logger.error(f"Failed to search books: {e}")
            return []
    
    @staticmethod
    async def get_book_stats(db: AsyncSession) -> Dict[str, Any]:
        """
        Get book statistics.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with book statistics
        """
        logger.info("Getting book statistics")
        
        try:
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
            
        except Exception as e:
            logger.error(f"Failed to get book statistics: {e}")
            return {
                "total_books": 0,
                "total_copies": 0,
                "available_books": 0,
                "borrowed_books": 0,
                "books_by_genre": {},
                "books_by_status": {},
                "books_by_language": {},
                "average_copies_per_book": 0.0
            }
    
    @staticmethod
    async def bulk_create_books(books_data: List[BookCreate], created_by_id: int, db: AsyncSession) -> List[Book]:
        """
        Create multiple books at once.
        
        Args:
            books_data: List of book creation data
            created_by_id: ID of user creating the books
            db: Database session
            
        Returns:
            List of created books
        """
        logger.info(f"Creating {len(books_data)} books in bulk")
        
        created_books = []
        errors = []
        
        for i, book_data in enumerate(books_data):
            try:
                book = await BookService.create_book(book_data, created_by_id, db)
                created_books.append(book)
            except Exception as e:
                errors.append(f"Book {i}: {str(e)}")
        
        if errors:
            logger.warning(f"Bulk create completed with {len(errors)} errors: {errors}")
        
        logger.info(f"Created {len(created_books)} books in bulk")
        return created_books
    
    @staticmethod
    async def bulk_update_books(book_ids: List[int], update_data: BookUpdate, db: AsyncSession) -> int:
        """
        Update multiple books at once.
        
        Args:
            book_ids: List of book IDs to update
            update_data: Update data to apply
            db: Database session
            
        Returns:
            Number of books successfully updated
        """
        logger.info(f"Updating {len(book_ids)} books in bulk")
        
        updated_count = 0
        errors = []
        
        for book_id in book_ids:
            try:
                book = await BookService.get_book(book_id, db)
                if book:
                    update_dict = update_data.dict(exclude_unset=True)
                    for field, value in update_dict.items():
                        setattr(book, field, value)
                    book.updated_at = datetime.utcnow()
                    updated_count += 1
            except Exception as e:
                errors.append(f"Book {book_id}: {str(e)}")
        
        if updated_count > 0:
            await db.commit()
        
        if errors:
            logger.warning(f"Bulk update completed with {len(errors)} errors: {errors}")
        
        logger.info(f"Updated {updated_count} books in bulk")
        return updated_count
    
    @staticmethod
    async def get_recent_books(limit: int = 10, db: AsyncSession = None) -> List[Book]:
        """
        Get recently added books.
        
        Args:
            limit: Maximum number of books to return
            db: Database session
            
        Returns:
            List of recent books
        """
        logger.debug(f"Getting {limit} recent books")
        
        try:
            query = select(Book).order_by(desc(Book.created_at)).limit(limit)
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get recent books: {e}")
            return []
    
    @staticmethod
    async def get_popular_books(limit: int = 10, db: AsyncSession = None) -> List[Book]:
        """
        Get popular books (based on borrow count).
        Note: This would need borrowing tracking to be accurate.
        
        Args:
            limit: Maximum number of books to return
            db: Database session
            
        Returns:
            List of popular books
        """
        logger.debug(f"Getting {limit} popular books")
        
        try:
            # For now, return books with most copies borrowed
            # In a real system, you would join with borrowing records
            query = select(Book).order_by(
                desc(Book.total_copies - Book.available_copies),
                desc(Book.created_at)
            ).limit(limit)
            
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get popular books: {e}")
            return []