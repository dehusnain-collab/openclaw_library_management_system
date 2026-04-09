"""
Search service for book discovery.
Covers: SCRUM-31, SCRUM-32
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from datetime import datetime
import logging

from app.models.book import Book, BookStatus
from app.schemas.book import BookSearchParams
from app.services.cache_service import CacheService
from app.utils.logging import get_logger

logger = get_logger(__name__)


class SearchService:
    """Service for search operations."""
    
    @staticmethod
    async def search_books(
        search_params: BookSearchParams,
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = None,
        use_cache: bool = True
    ) -> Tuple[List[Book], int]:
        """
        Search books with filters and return results with total count.
        
        Args:
            search_params: Search parameters
            skip: Number of records to skip
            limit: Maximum number of records to return
            db: Database session
            use_cache: Whether to use cache
            
        Returns:
            Tuple of (books list, total count)
        """
        logger.info(f"Searching books with params: {search_params.dict()}, use_cache={use_cache}")
        
        try:
            # Try to get from cache first
            if use_cache and CacheService.is_available() and skip == 0:
                cached_results = CacheService.get_cached_search_results(search_params.dict())
                if cached_results:
                    logger.debug("Search results found in cache")
                    # Convert dicts back to Book objects
                    books = [Book(**book_dict) for book_dict in cached_results[:limit]]
                    return books, len(cached_results)
            
            # Build base query
            query = select(Book)
            count_query = select(func.count(Book.id))
            
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
            
            # Apply filters to both queries
            if filters:
                query = query.where(and_(*filters))
                count_query = count_query.where(and_(*filters))
            
            # Get total count
            count_result = await db.execute(count_query)
            total_count = count_result.scalar()
            
            # Apply pagination and ordering to main query
            query = query.order_by(desc(Book.created_at)).offset(skip).limit(limit)
            
            # Execute main query
            result = await db.execute(query)
            books = result.scalars().all()
            
            # Cache the results (first page only)
            if use_cache and CacheService.is_available() and skip == 0 and books:
                books_dict = [book.to_dict() for book in books]
                CacheService.cache_search_results(search_params.dict(), books_dict)
            
            logger.info(f"Found {len(books)} books out of {total_count} total")
            return books, total_count
            
        except Exception as e:
            logger.error(f"Failed to search books: {e}")
            return [], 0
    
    @staticmethod
    async def get_search_suggestions(
        query: str,
        field: str = "title",
        limit: int = 10,
        db: AsyncSession = None
    ) -> List[str]:
        """
        Get search suggestions for auto-complete.
        
        Args:
            query: Partial query string
            field: Field to get suggestions from (title, author, genre)
            limit: Maximum number of suggestions
            db: Database session
            
        Returns:
            List of suggestions
        """
        if not query or len(query) < 2:
            return []
        
        if field not in ["title", "author", "genre"]:
            field = "title"
        
        try:
            search_term = f"%{query}%"
            
            if field == "title":
                column = Book.title
            elif field == "author":
                column = Book.author
            else:  # genre
                column = Book.genre
            
            query_stmt = select(column).where(
                column.ilike(search_term),
                column.isnot(None)
            ).distinct().order_by(column).limit(limit)
            
            result = await db.execute(query_stmt)
            suggestions = [row[0] for row in result.all()]
            
            logger.debug(f"Generated {len(suggestions)} suggestions for '{query}' in field '{field}'")
            return suggestions
            
        except Exception as e:
            logger.error(f"Failed to get search suggestions: {e}")
            return []
    
    @staticmethod
    async def advanced_search(
        query: str,
        fields: List[str] = None,
        filters: Dict[str, Any] = None,
        sort_by: str = "relevance",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = None
    ) -> Tuple[List[Book], int, Dict[str, Any]]:
        """
        Advanced search with multiple fields and sorting options.
        
        Args:
            query: Search query string
            fields: Fields to search in (title, author, description, etc.)
            filters: Additional filters
            sort_by: Field to sort by (relevance, title, author, year, etc.)
            sort_order: Sort order (asc or desc)
            skip: Number of records to skip
            limit: Maximum number of records to return
            db: Database session
            
        Returns:
            Tuple of (books list, total count, search metadata)
        """
        logger.info(f"Advanced search: '{query}', fields: {fields}, sort: {sort_by}")
        
        if not fields:
            fields = ["title", "author", "description", "isbn"]
        
        try:
            # Build search conditions
            search_conditions = []
            if query:
                search_term = f"%{query}%"
                for field in fields:
                    if hasattr(Book, field):
                        search_conditions.append(getattr(Book, field).ilike(search_term))
            
            # Build filter conditions
            filter_conditions = []
            if filters:
                for field, value in filters.items():
                    if hasattr(Book, field) and value is not None:
                        if isinstance(value, (list, tuple)):
                            filter_conditions.append(getattr(Book, field).in_(value))
                        else:
                            filter_conditions.append(getattr(Book, field) == value)
            
            # Combine conditions
            conditions = []
            if search_conditions:
                conditions.append(or_(*search_conditions))
            if filter_conditions:
                conditions.append(and_(*filter_conditions))
            
            # Build queries
            base_query = select(Book)
            count_query = select(func.count(Book.id))
            
            if conditions:
                combined_condition = and_(*conditions) if len(conditions) > 1 else conditions[0]
                base_query = base_query.where(combined_condition)
                count_query = count_query.where(combined_condition)
            
            # Get total count
            count_result = await db.execute(count_query)
            total_count = count_result.scalar()
            
            # Apply sorting
            if sort_by == "relevance" and query:
                # Simple relevance scoring based on field matches
                base_query = base_query.order_by(
                    desc(Book.title.ilike(f"%{query}%")),
                    desc(Book.author.ilike(f"%{query}%")),
                    desc(Book.created_at)
                )
            elif hasattr(Book, sort_by):
                sort_column = getattr(Book, sort_by)
                if sort_order.lower() == "desc":
                    base_query = base_query.order_by(desc(sort_column))
                else:
                    base_query = base_query.order_by(sort_column)
            else:
                base_query = base_query.order_by(desc(Book.created_at))
            
            # Apply pagination
            base_query = base_query.offset(skip).limit(limit)
            
            # Execute query
            result = await db.execute(base_query)
            books = result.scalars().all()
            
            # Calculate search metadata
            metadata = {
                "query": query,
                "fields_searched": fields,
                "filters_applied": filters or {},
                "sort_by": sort_by,
                "sort_order": sort_order,
                "total_count": total_count,
                "returned_count": len(books),
                "page": (skip // limit) + 1 if limit > 0 else 1,
                "page_size": limit
            }
            
            logger.info(f"Advanced search found {len(books)} books")
            return books, total_count, metadata
            
        except Exception as e:
            logger.error(f"Advanced search failed: {e}")
            return [], 0, {
                "query": query,
                "error": str(e),
                "total_count": 0,
                "returned_count": 0
            }