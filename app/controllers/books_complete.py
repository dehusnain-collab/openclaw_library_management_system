"""
Complete book management endpoints.
Covers: SCRUM-18, SCRUM-19, SCRUM-27
"""
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.book import (
    BookCreate, BookResponse, BookUpdate, BookSearchParams,
    BookBulkCreate, BookBulkUpdate, BookStatsResponse
)
from app.middleware.auth import get_current_user, require_admin, require_librarian
from app.services.book_service import BookService
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["books"])


@router.get("/books", response_model=List[BookResponse])
async def get_books(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    genre: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    available_only: bool = Query(False),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get books with optional filtering.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        search: Search term for title, author, description, or ISBN
        author: Filter by author
        genre: Filter by genre
        status: Filter by status
        available_only: Only return available books
        db: Database session
        
    Returns:
        List of books
    """
    logger.info(f"Getting books (skip={skip}, limit={limit})")
    
    try:
        search_params = BookSearchParams(
            query=search,
            author=author,
            genre=genre,
            status=status,
            available_only=available_only
        )
        
        books = await BookService.search_books(search_params, skip, limit, db)
        return books
    except Exception as e:
        logger.error(f"Failed to get books: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get books: {str(e)}"
        )


@router.get("/books/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: int,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get a specific book by ID.
    
    Args:
        book_id: ID of book to retrieve
        db: Database session
        
    Returns:
        Book details
    """
    logger.info(f"Getting book: {book_id}")
    
    try:
        book = await BookService.get_book(book_id, db)
        
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book not found: {book_id}"
            )
        
        return book
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get book: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get book: {str(e)}"
        )


@router.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    book_data: BookCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_librarian)
) -> Any:
    """
    Create a new book (librarian or admin only).
    
    Args:
        book_data: Book data to create
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Created book
    """
    logger.info(f"Creating book: {book_data.title}")
    
    try:
        book = await BookService.create_book(book_data, current_user["id"], db)
        return book
    except Exception as e:
        logger.error(f"Failed to create book: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create book: {str(e)}"
        )


@router.put("/books/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int,
    book_data: BookUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_librarian)
) -> Any:
    """
    Update a book (librarian or admin only).
    
    Args:
        book_id: ID of book to update
        book_data: Book data to update
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Updated book
    """
    logger.info(f"Updating book: {book_id}")
    
    try:
        book = await BookService.update_book(book_id, book_data, db)
        
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book not found: {book_id}"
            )
        
        return book
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update book: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update book: {str(e)}"
        )


@router.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
) -> None:
    """
    Delete a book (admin only).
    
    Args:
        book_id: ID of book to delete
        db: Database session
        current_user: Current authenticated user
    """
    logger.info(f"Deleting book: {book_id}")
    
    try:
        success, message = await BookService.delete_book(book_id, db)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete book: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete book: {str(e)}"
        )


@router.get("/books/stats", response_model=BookStatsResponse)
async def get_book_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get book statistics.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Book statistics
    """
    logger.info(f"User {current_user['id']} getting book stats")
    
    try:
        stats = await BookService.get_book_stats(db)
        return stats
    except Exception as e:
        logger.error(f"Failed to get book stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get book stats: {str(e)}"
        )


@router.post("/books/bulk", response_model=List[BookResponse], status_code=status.HTTP_201_CREATED)
async def bulk_create_books(
    bulk_data: BookBulkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_librarian)
) -> Any:
    """
    Create multiple books at once (librarian or admin only).
    
    Args:
        bulk_data: Bulk book creation data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of created books
    """
    logger.info(f"Bulk creating {len(bulk_data.books)} books")
    
    try:
        books = await BookService.bulk_create_books(bulk_data.books, current_user["id"], db)
        return books
    except Exception as e:
        logger.error(f"Failed to bulk create books: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk create books: {str(e)}"
        )


@router.put("/books/bulk", response_model=dict)
async def bulk_update_books(
    bulk_data: BookBulkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_librarian)
) -> Any:
    """
    Update multiple books at once (librarian or admin only).
    
    Args:
        bulk_data: Bulk book update data
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Update statistics
    """
    logger.info(f"Bulk updating {len(bulk_data.book_ids)} books")
    
    try:
        updated_count = await BookService.bulk_update_books(
            bulk_data.book_ids,
            bulk_data.update_data,
            db
        )
        
        return {
            "updated_count": updated_count,
            "total_requested": len(bulk_data.book_ids),
            "message": f"Updated {updated_count} books successfully"
        }
    except Exception as e:
        logger.error(f"Failed to bulk update books: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk update books: {str(e)}"
        )


@router.get("/books/search/advanced", response_model=List[BookResponse])
async def advanced_search_books(
    search_params: BookSearchParams,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Advanced book search with multiple filters.
    
    Args:
        search_params: Search parameters
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List of matching books
    """
    logger.info(f"Advanced book search: {search_params.dict()}")
    
    try:
        books = await BookService.search_books(search_params, skip, limit, db)
        return books
    except Exception as e:
        logger.error(f"Failed to search books: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search books: {str(e)}"
        )


@router.get("/books/recent", response_model=List[BookResponse])
async def get_recent_books(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get recently added books.
    
    Args:
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List of recent books
    """
    logger.info(f"Getting {limit} recent books")
    
    try:
        books = await BookService.get_recent_books(limit, db)
        return books
    except Exception as e:
        logger.error(f"Failed to get recent books: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recent books: {str(e)}"
        )


@router.get("/books/popular", response_model=List[BookResponse])
async def get_popular_books(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get popular books (based on borrow count).
    
    Args:
        limit: Maximum number of records to return
        db: Database session
        
    Returns:
        List of popular books
    """
    logger.info(f"Getting {limit} popular books")
    
    try:
        books = await BookService.get_popular_books(limit, db)
        return books
    except Exception as e:
        logger.error(f"Failed to get popular books: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get popular books: {str(e)}"
        )