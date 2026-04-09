"""
Search endpoints for book discovery.
Covers: SCRUM-31, SCRUM-32
"""
from typing import List, Any, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.book import BookSimpleResponse, BookSearchParams
from app.middleware.auth import get_current_user
from app.services.search_service import SearchService
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["search"])


@router.get("/search/books", response_model=Dict[str, Any])
async def search_books(
    query: Optional[str] = Query(None, min_length=1, max_length=100, description="Search query"),
    author: Optional[str] = Query(None, description="Filter by author"),
    genre: Optional[str] = Query(None, description="Filter by genre"),
    status: Optional[str] = Query(None, description="Filter by status"),
    min_year: Optional[int] = Query(None, ge=1000, le=2100, description="Minimum publication year"),
    max_year: Optional[int] = Query(None, ge=1000, le=2100, description="Maximum publication year"),
    language: Optional[str] = Query(None, description="Filter by language"),
    available_only: bool = Query(False, description="Only return available books"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Search books with multiple filters.
    
    Search books by title, author, description, ISBN, or other criteria.
    Available to all authenticated users.
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
        
        books, total_count = await SearchService.search_books(search_params, skip, limit, db)
        
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
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    fields: Optional[str] = Query(None, description="Comma-separated fields to search"),
    genre: Optional[str] = Query(None, description="Filter by genre"),
    language: Optional[str] = Query(None, description="Filter by language"),
    available_only: bool = Query(False, description="Only return available books"),
    sort_by: str = Query("relevance", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Advanced book search with field selection and sorting.
    
    Advanced search with multiple search fields and sorting options.
    Available to all authenticated users.
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
            filters["available_copies"] = {"$gt": 0}  # Simplified filter
        
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
    q: str = Query(..., min_length=1, max_length=50, description="Partial search query"),
    field: str = Query("title", description="Field to get suggestions from"),
    limit: int = Query(10, ge=1, le=50, description="Maximum suggestions"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Any:
    """
    Get search suggestions for auto-complete.
    
    Returns search suggestions for auto-complete functionality.
    Available to all authenticated users.
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