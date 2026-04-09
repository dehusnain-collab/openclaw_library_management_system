"""
Search endpoints for book discovery.
Covers: SCRUM-31, SCRUM-32
"""
from typing import List, Any, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.book import BookResponse, BookSearchParams
from app.middleware.auth import get_current_user
from app.services.search_service import SearchService
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["search"])


@router.get("/search/books", response_model=Dict[str, Any])
async def search_books(
    query: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    genre: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    min_year: Optional[int] = Query(None, ge=1000, le=2100),
    max_year: Optional[int] = Query(None, ge=1000, le=2100),
    language: Optional[str] = Query(None),
    available_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Search books with multiple filters.
    
    Args:
        query: Search term for title, author, description, or ISBN
        author: Filter by author
        genre: Filter by genre
        status: Filter by status
        min_year: Minimum publication year
        max_year: Maximum publication year
        language: Filter by language
        available_only: Only return available books
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Search results with metadata
    """
    logger.info(f"User {current_user['id']} searching books: query='{query}'")
    
    try:
        search_params = BookSearchParams(
            query=query,
            author=author,
            genre=genre,
            status=status,
            min_year=min_year,
            max_year=max_year,
            language=language,
            available_only=available_only
        )
        
        books, total_count = await SearchService.search_books(
            search_params, skip, limit, db
        )
        
        return {
            "books": books,
            "metadata": {
                "total_count": total_count,
                "returned_count": len(books),
                "skip": skip,
                "limit": limit,
                "has_more": (skip + len(books)) < total_count,
                "search_params": search_params.dict(exclude_none=True)
            }
        }
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/search/advanced", response_model=Dict[str, Any])
async def advanced_search(
    q: str = Query(..., min_length=1, max_length=100),
    fields: Optional[str] = Query(None, description="Comma-separated fields to search"),
    genre: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    available_only: bool = Query(False),
    sort_by: str = Query("relevance", regex="^(relevance|title|author|publication_year|created_at)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Advanced book search with field selection and sorting.
    
    Args:
        q: Search query
        fields: Comma-separated fields to search (title,author,description,isbn,publisher,genre)
        genre: Filter by genre
        language: Filter by language
        available_only: Only return available books
        sort_by: Field to sort by
        sort_order: Sort order (asc or desc)
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Advanced search results with metadata
    """
    logger.info(f"User {current_user['id']} advanced search: '{q}', sort_by={sort_by}")
    
    try:
        # Parse fields
        search_fields = None
        if fields:
            search_fields = [f.strip() for f in fields.split(",") if f.strip()]
        
        # Build filters
        filters = {}
        if genre:
            filters["genre"] = genre
        if language:
            filters["language"] = language
        if available_only:
            filters["available_copies"] = {"$gt": 0}  # This is simplified
        
        books, total_count, metadata = await SearchService.advanced_search(
            query=q,
            fields=search_fields,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            skip=skip,
            limit=limit,
            db=db
        )
        
        return {
            "books": books,
            "metadata": metadata
        }
    except Exception as e:
        logger.error(f"Advanced search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Advanced search failed: {str(e)}"
        )


@router.get("/search/suggestions", response_model=List[str])
async def get_search_suggestions(
    q: str = Query(..., min_length=1, max_length=50),
    field: str = Query("title", regex="^(title|author|genre)$"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get search suggestions for auto-complete.
    
    Args:
        q: Partial search query
        field: Field to get suggestions from
        limit: Maximum number of suggestions
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of search suggestions
    """
    logger.info(f"User {current_user['id']} getting suggestions for '{q}' in field '{field}'")
    
    try:
        suggestions = await SearchService.get_search_suggestions(q, field, limit, db)
        return suggestions
    except Exception as e:
        logger.error(f"Failed to get suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggestions: {str(e)}"
        )


@router.get("/search/popular", response_model=List[Dict[str, Any]])
async def get_popular_searches(
    days: int = Query(7, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get popular search terms.
    
    Args:
        days: Number of days to look back
        limit: Maximum number of popular searches
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        List of popular searches with counts
    """
    logger.info(f"User {current_user['id']} getting popular searches for last {days} days")
    
    try:
        popular_searches = await SearchService.get_popular_searches(days, limit, db)
        return popular_searches
    except Exception as e:
        logger.error(f"Failed to get popular searches: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get popular searches: {str(e)}"
        )


@router.get("/search/full-text", response_model=Dict[str, Any])
async def full_text_search(
    q: str = Query(..., min_length=1, max_length=100),
    language: str = Query("english"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Full-text search using PostgreSQL text search.
    
    Args:
        q: Search query
        language: Text search language
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Full-text search results
    """
    logger.info(f"User {current_user['id']} full-text search: '{q}', language: {language}")
    
    try:
        books, total_count = await SearchService.full_text_search(
            query=q,
            language=language,
            skip=skip,
            limit=limit,
            db=db
        )
        
        return {
            "books": books,
            "metadata": {
                "query": q,
                "language": language,
                "total_count": total_count,
                "returned_count": len(books),
                "skip": skip,
                "limit": limit,
                "has_more": (skip + len(books)) < total_count
            }
        }
    except Exception as e:
        logger.error(f"Full-text search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Full-text search failed: {str(e)}"
        )


@router.get("/search/analytics", response_model=Dict[str, Any])
async def get_search_analytics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get search analytics (admin only).
    
    Args:
        days: Number of days to analyze
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Search analytics data
    """
    logger.info(f"User {current_user['id']} getting search analytics for last {days} days")
    
    try:
        # Check if user is admin (simplified)
        if current_user.get('role') != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required for search analytics"
            )
        
        from datetime import datetime, timedelta
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        analytics = await SearchService.get_search_analytics(start_date, end_date, db)
        return analytics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get search analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get search analytics: {str(e)}"
        )