"""
Cache service for Redis integration.
Covers: SCRUM-33, SCRUM-34
"""
import json
import pickle
from typing import Any, Optional, Union, List, Dict
import redis
import logging
from datetime import timedelta

from app.config.settings import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class CacheService:
    """Service for Redis cache operations."""
    
    _redis_client = None
    
    @classmethod
    def get_redis_client(cls):
        """Get Redis client (singleton)."""
        if cls._redis_client is None:
            try:
                cls._redis_client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    password=settings.REDIS_PASSWORD,
                    db=settings.REDIS_DB,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
                # Test connection
                cls._redis_client.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                cls._redis_client = None
                raise
        
        return cls._redis_client
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if Redis cache is available."""
        try:
            client = cls.get_redis_client()
            return client.ping()
        except:
            return False
    
    @classmethod
    def set(
        cls, 
        key: str, 
        value: Any, 
        expire_seconds: Optional[int] = None,
        serialize: bool = True
    ) -> bool:
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            expire_seconds: Time to live in seconds
            serialize: Whether to serialize the value
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = cls.get_redis_client()
            
            if serialize:
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                else:
                    value = str(value)
            
            if expire_seconds:
                client.setex(key, expire_seconds, value)
            else:
                client.set(key, value)
            
            logger.debug(f"Cache set: {key}")
            return True
        except Exception as e:
            logger.warning(f"Failed to set cache for key {key}: {e}")
            return False
    
    @classmethod
    def get(
        cls, 
        key: str, 
        default: Any = None,
        deserialize: bool = True
    ) -> Any:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            default: Default value if key not found
            deserialize: Whether to deserialize the value
            
        Returns:
            Cached value or default
        """
        try:
            client = cls.get_redis_client()
            value = client.get(key)
            
            if value is None:
                logger.debug(f"Cache miss: {key}")
                return default
            
            logger.debug(f"Cache hit: {key}")
            
            if deserialize:
                try:
                    return json.loads(value)
                except:
                    return value
            
            return value
        except Exception as e:
            logger.warning(f"Failed to get cache for key {key}: {e}")
            return default
    
    @classmethod
    def delete(cls, key: str) -> bool:
        """
        Delete a key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = cls.get_redis_client()
            result = client.delete(key)
            logger.debug(f"Cache delete: {key} (deleted: {result})")
            return result > 0
        except Exception as e:
            logger.warning(f"Failed to delete cache key {key}: {e}")
            return False
    
    @classmethod
    def delete_pattern(cls, pattern: str) -> int:
        """
        Delete keys matching a pattern.
        
        Args:
            pattern: Redis pattern (e.g., "book:*")
            
        Returns:
            Number of keys deleted
        """
        try:
            client = cls.get_redis_client()
            keys = client.keys(pattern)
            
            if not keys:
                return 0
            
            deleted = client.delete(*keys)
            logger.debug(f"Cache delete pattern: {pattern} (deleted: {deleted})")
            return deleted
        except Exception as e:
            logger.warning(f"Failed to delete cache pattern {pattern}: {e}")
            return 0
    
    @classmethod
    def exists(cls, key: str) -> bool:
        """
        Check if a key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            client = cls.get_redis_client()
            return client.exists(key) > 0
        except Exception as e:
            logger.warning(f"Failed to check cache key {key}: {e}")
            return False
    
    @classmethod
    def increment(cls, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment a counter in cache.
        
        Args:
            key: Cache key
            amount: Amount to increment
            
        Returns:
            New value or None if failed
        """
        try:
            client = cls.get_redis_client()
            return client.incrby(key, amount)
        except Exception as e:
            logger.warning(f"Failed to increment cache key {key}: {e}")
            return None
    
    @classmethod
    def decrement(cls, key: str, amount: int = 1) -> Optional[int]:
        """
        Decrement a counter in cache.
        
        Args:
            key: Cache key
            amount: Amount to decrement
            
        Returns:
            New value or None if failed
        """
        try:
            client = cls.get_redis_client()
            return client.decrby(key, amount)
        except Exception as e:
            logger.warning(f"Failed to decrement cache key {key}: {e}")
            return None
    
    @classmethod
    def get_keys(cls, pattern: str = "*") -> List[str]:
        """
        Get keys matching a pattern.
        
        Args:
            pattern: Redis pattern
            
        Returns:
            List of matching keys
        """
        try:
            client = cls.get_redis_client()
            return client.keys(pattern)
        except Exception as e:
            logger.warning(f"Failed to get cache keys for pattern {pattern}: {e}")
            return []
    
    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            client = cls.get_redis_client()
            info = client.info()
            
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human", "N/A"),
                "total_keys": info.get("db0", {}).get("keys", 0),
                "uptime_days": info.get("uptime_in_days", 0),
                "connected_clients": info.get("connected_clients", 0),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": (
                    info.get("keyspace_hits", 0) / 
                    max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
                )
            }
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {"connected": False, "error": str(e)}
    
    # Book-specific cache methods
    @classmethod
    def cache_book(cls, book_id: int, book_data: Dict[str, Any]) -> bool:
        """
        Cache book data.
        
        Args:
            book_id: Book ID
            book_data: Book data to cache
            
        Returns:
            True if successful, False otherwise
        """
        key = f"book:{book_id}"
        return cls.set(key, book_data, expire_seconds=3600)  # 1 hour
    
    @classmethod
    def get_cached_book(cls, book_id: int) -> Optional[Dict[str, Any]]:
        """
        Get cached book data.
        
        Args:
            book_id: Book ID
            
        Returns:
            Cached book data or None
        """
        key = f"book:{book_id}"
        return cls.get(key)
    
    @classmethod
    def invalidate_book_cache(cls, book_id: int) -> bool:
        """
        Invalidate book cache.
        
        Args:
            book_id: Book ID
            
        Returns:
            True if successful, False otherwise
        """
        key = f"book:{book_id}"
        return cls.delete(key)
    
    @classmethod
    def invalidate_all_books_cache(cls) -> int:
        """
        Invalidate all book cache entries.
        
        Returns:
            Number of keys deleted
        """
        return cls.delete_pattern("book:*")
    
    # Search cache methods
    @classmethod
    def cache_search_results(
        cls, 
        search_params: Dict[str, Any], 
        results: List[Dict[str, Any]]
    ) -> bool:
        """
        Cache search results.
        
        Args:
            search_params: Search parameters
            results: Search results
            
        Returns:
            True if successful, False otherwise
        """
        # Create a cache key from search parameters
        params_str = json.dumps(search_params, sort_keys=True)
        key = f"search:{hash(params_str)}"
        return cls.set(key, results, expire_seconds=300)  # 5 minutes
    
    @classmethod
    def get_cached_search_results(
        cls, 
        search_params: Dict[str, Any]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached search results.
        
        Args:
            search_params: Search parameters
            
        Returns:
            Cached search results or None
        """
        params_str = json.dumps(search_params, sort_keys=True)
        key = f"search:{hash(params_str)}"
        return cls.get(key)
    
    # User session cache methods
    @classmethod
    def cache_user_session(cls, user_id: int, session_data: Dict[str, Any]) -> bool:
        """
        Cache user session data.
        
        Args:
            user_id: User ID
            session_data: Session data
            
        Returns:
            True if successful, False otherwise
        """
        key = f"session:user:{user_id}"
        return cls.set(key, session_data, expire_seconds=86400)  # 24 hours
    
    @classmethod
    def get_cached_user_session(cls, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get cached user session data.
        
        Args:
            user_id: User ID
            
        Returns:
            Cached session data or None
        """
        key = f"session:user:{user_id}"
        return cls.get(key)
    
    @classmethod
    def invalidate_user_session(cls, user_id: int) -> bool:
        """
        Invalidate user session cache.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful, False otherwise
        """
        key = f"session:user:{user_id}"
        return cls.delete(key)
    
    # Rate limiting cache methods
    @classmethod
    def check_rate_limit(
        cls, 
        identifier: str, 
        limit: int, 
        window_seconds: int
    ) -> Dict[str, Any]:
        """
        Check rate limit for an identifier.
        
        Args:
            identifier: Rate limit identifier (e.g., "ip:127.0.0.1" or "user:123")
            limit: Maximum requests in window
            window_seconds: Time window in seconds
            
        Returns:
            Dictionary with rate limit status
        """
        key = f"ratelimit:{identifier}"
        
        try:
            client = cls.get_redis_client()
            
            # Use Redis transactions for atomic operations
            pipe = client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_seconds)
            results = pipe.execute()
            
            current_count = results[0]
            
            return {
                "allowed": current_count <= limit,
                "current": current_count,
                "limit": limit,
                "remaining": max(0, limit - current_count),
                "reset_in": window_seconds
            }
        except Exception as e:
            logger.warning(f"Failed to check rate limit for {identifier}: {e}")
            # If Redis fails, allow the request
            return {
                "allowed": True,
                "current": 0,
                "limit": limit,
                "remaining": limit,
                "reset_in": window_seconds,
                "cache_error": True
            }