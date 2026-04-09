"""
Book management endpoints.
Covers: SCRUM-18, SCRUM-19, SCRUM-27
"""
from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.book import (
    BookCreate, BookResponse, BookUpdate, BookSearchParams,
    BookBulkCreate, BookBulkUpdate, BookStatsResponse, BookSimpleResponse
)
from app.middleware.auth import get_current_user, require_admin, require_librarian
from app.services.book_service import BookService
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["books"])


@router.get("/books", response_model=List[BookSimpleResponse])
async def get_books(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    search: Optional[str] = Query(None, description="Search term"),
    author: Optional[str] = Query(None, description="Filter by author"),
    genre: Optional[str] = Query(None, description="Filter by genre"),
    status: Optional[str] = Query(None, description="Filter by status"),
    available_only: bool = Query(False, description="Only return available books"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get books with optional filtering.
    
    Returns a list of books with pagination and filtering options.
    Available to all authenticated users.
    """
    logger.info(f"User {current_user['id']} getting books (skip={skip}, limit={limit})")
    
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
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get a specific book by ID.
    
    Returns detailed information about a specific book.
    Available to all authenticated users.
    """
    logger.info(f"User {current_user['id']} getting book: {book_id}")
    
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
    Create a new book.
    
    Creates a new book in the library system.
    Requires librarian or admin role.
    """
    logger.info(f"User {current_user['id']} creating book: {book_data.title}")
    
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
    Update a book.
    
    Updates an existing book's information.
    Requires librarian or admin role.
    """
    logger.info(f"User {current_user['id']} updating book: {book_id}")
    
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
    Delete a book.
    
    Deletes a book from the library system.
    Requires admin role.
    """
    logger.info(f"User {current_user['id']} deleting book: {book_id}")
    
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
    
    Returns statistics about books in the library.
    Available to all authenticated users.
    """
    logger.info(f"User {current_user['id']} getting book statistics")
    
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
    Create multiple books at once.
    
    Creates multiple books in a single request.
    Requires librarian or admin role.
    """
    logger.info(f"User {current_user['id']} bulk creating {len(bulk_data.books)} books")
    
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
    Update multiple books at once.
    
    Updates multiple books in a single request.
    Requires librarian or admin role.
    """
    logger.info(f"User {current_user['id']} bulk updating {len(bulk_data.book_ids)} books")
    
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


@router.get("/books/recent", response_model=List[BookSimpleResponse])
async def get_recent_books(
    limit: int = Query(10, ge=1, le=100, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get recently added books.
    
    Returns the most recently added books.
    Available to all authenticated users.
    """
    logger.info(f"User {current_user['id']} getting {limit} recent books")
    
    try:
        books = await BookService.get_recent_books(limit, db)
        return books
    except Exception as e:
        logger.error(f"Failed to get recent books: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recent books: {str(e)}"
        )


@router.get("/books/popular", response_model=List[BookSimpleResponse])
async def get_popular_books(
    limit: int = Query(10, ge=1, le=100, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get popular books.
    
    Returns the most popular books (based on borrowing activity).
    Available to all authenticated users.
    """
    logger.info(f"User {current_user['id']} getting {limit} popular books")
    
    try:
        books = await BookService.get_popular_books(limit, db)
        return books
    except Exception as e:
        logger.error(f"Failed to get popular books: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get popular books: {str(e)}"
        )


@router.get("/search/books", response_model=List[BookSimpleResponse])
async def search_books(
    query: str = Query(..., min_length=1, max_length=100, description="Search query"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Search books.
    
    Search books by title, author, description, or ISBN.
    Available to all authenticated users.
    """
    logger.info(f"User {current_user['id']} searching books: '{query}'")
    
    try:
        search_params = BookSearchParams(query=query)
        books = await BookService.search_books(search_params, skip, limit, db)
        return books
    except Exception as e:
        logger.error(f"Failed to search books: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search books: {str(e)}"
        )