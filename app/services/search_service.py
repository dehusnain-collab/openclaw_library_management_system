"""
Search service for book discovery.
Covers: SCRUM-31, SCRUM-32
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, text
from datetime import datetime
import logging

from app.models.book import Book, BookStatus
from app.schemas.book import BookSearchParams
from app.utils.logging import get_logger

logger = get_logger(__name__)


class SearchService:
    """Service for search operations."""
    
    @staticmethod
    async def search_books(
        search_params: BookSearchParams,
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = None
    ) -> Tuple[List[Book], int]:
        """
        Search books with filters and return results with total count.
        
        Args:
            search_params: Search parameters
            skip: Number of records to skip
            limit: Maximum number of records to return
            db: Database session
            
        Returns:
            Tuple of (books list, total count)
        """
        logger.info(f"Searching books with params: {search_params.dict()}")
        
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
                    Book.isbn.ilike(search_term),
                    Book.publisher.ilike(search_term),
                    Book.genre.ilike(search_term)
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
        
        logger.info(f"Found {len(books)} books out of {total_count} total")
        return books, total_count
    
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
            fields = ["title", "author", "description", "isbn", "publisher"]
        
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
            # In a real system, you might use full-text search
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
        
        search_term = f"%{query}%"
        column = getattr(Book, field)
        
        query_stmt = select(column).where(
            column.ilike(search_term),
            column.isnot(None)
        ).distinct().order_by(column).limit(limit)
        
        result = await db.execute(query_stmt)
        suggestions = [row[0] for row in result.all()]
        
        logger.debug(f"Generated {len(suggestions)} suggestions for '{query}' in field '{field}'")
        return suggestions
    
    @staticmethod
    async def get_popular_searches(
        days: int = 7,
        limit: int = 20,
        db: AsyncSession = None
    ) -> List[Dict[str, Any]]:
        """
        Get popular search terms (would require search log table).
        For now, returns mock data or queries from cache.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of popular searches
            db: Database session
            
        Returns:
            List of popular searches with counts
        """
        # In a real system, you would query a search_logs table
        # For now, return empty list or mock data
        logger.info(f"Getting popular searches for last {days} days")
        
        # This would be implemented with a search logging system
        return [
            {"term": "python programming", "count": 42},
            {"term": "machine learning", "count": 38},
            {"term": "web development", "count": 35},
            {"term": "data science", "count": 32},
            {"term": "fiction", "count": 28},
        ][:limit]
    
    @staticmethod
    async def get_search_analytics(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Get search analytics.
        
        Args:
            start_date: Start date for analytics
            end_date: End date for analytics
            db: Database session
            
        Returns:
            Search analytics data
        """
        # In a real system, this would query search logs
        # For now, return mock analytics
        
        logger.info(f"Getting search analytics from {start_date} to {end_date}")
        
        return {
            "total_searches": 1250,
            "unique_users": 342,
            "avg_searches_per_user": 3.65,
            "most_popular_terms": [
                {"term": "python", "count": 156},
                {"term": "javascript", "count": 142},
                {"term": "database", "count": 128},
                {"term": "api", "count": 115},
                {"term": "testing", "count": 98},
            ],
            "no_results_rate": 0.12,  # 12% of searches returned no results
            "top_no_result_terms": [
                {"term": "xyzabc123", "count": 45},
                {"term": "nonexistentbook", "count": 32},
                {"term": "testsearch", "count": 28},
            ],
            "time_period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            }
        }
    
    @staticmethod
    async def full_text_search(
        query: str,
        language: str = "english",
        rank_threshold: float = 0.1,
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = None
    ) -> Tuple[List[Book], int]:
        """
        Full-text search using PostgreSQL tsvector.
        Requires PostgreSQL and proper indexes.
        
        Args:
            query: Search query
            language: Text search language
            rank_threshold: Minimum rank threshold
            skip: Number of records to skip
            limit: Maximum number of records to return
            db: Database session
            
        Returns:
            Tuple of (books list, total count)
        """
        logger.info(f"Full-text search: '{query}', language: {language}")
        
        # This is a simplified version. In practice, you would need:
        # 1. PostgreSQL with pg_trgm extension
        # 2. Generated columns or triggers for tsvector
        # 3. Proper indexes
        
        try:
            # Simple implementation using ilike for now
            # In production, use PostgreSQL full-text search
            search_term = f"%{query}%"
            
            base_query = select(Book).where(
                or_(
                    Book.title.ilike(search_term),
                    Book.author.ilike(search_term),
                    Book.description.ilike(search_term)
                )
            )
            
            count_query = select(func.count(Book.id)).where(
                or_(
                    Book.title.ilike(search_term),
                    Book.author.ilike(search_term),
                    Book.description.ilike(search_term)
                )
            )
            
            # Get total count
            count_result = await db.execute(count_query)
            total_count = count_result.scalar()
            
            # Apply pagination and ordering
            base_query = base_query.order_by(desc(Book.created_at)).offset(skip).limit(limit)
            
            # Execute query
            result = await db.execute(base_query)
            books = result.scalars().all()
            
            logger.info(f"Full-text search found {len(books)} books")
            return books, total_count
            
        except Exception as e:
            logger.error(f"Full-text search failed: {e}")
            # Fall back to simple search
            return await SearchService.search_books(
                BookSearchParams(query=query),
                skip=skip,
                limit=limit,
                db=db
            )