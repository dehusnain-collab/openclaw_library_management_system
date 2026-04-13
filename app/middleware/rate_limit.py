"""
Complete rate limiting middleware.
Covers: SCRUM-38, SCRUM-39
"""
import time
import logging
from typing import Callable, Dict, Tuple, Optional
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from collections import defaultdict

from app.utils.logging import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting."""
    
    def __init__(
        self,
        app: ASGIApp,
        default_limit: int = 100,  # requests per window
        default_window: int = 60,  # seconds
        limits: Dict[str, Tuple[int, int]] = None,  # path -> (limit, window)
        exempt_paths: list = None,
        storage_backend: str = "memory"  # memory or redis
    ):
        super().__init__(app)
        self.default_limit = default_limit
        self.default_window = default_window
        self.limits = limits or {}
        self.exempt_paths = exempt_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
        self.storage_backend = storage_backend
        
        # In-memory storage (for development)
        self.request_counts = defaultdict(list)
        
        # Redis storage (for production)
        self.redis_client = None
        if storage_backend == "redis":
            try:
                import redis
                self.redis_client = redis.Redis(
                    host="localhost",
                    port=6379,
                    decode_responses=True
                )
                logger.info("Redis connected for rate limiting")
            except ImportError:
                logger.warning("Redis not available, using memory storage")
                self.storage_backend = "memory"
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.storage_backend = "memory"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler
            
        Returns:
            HTTP response
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        # Skip exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_id(request)
        
        # Get rate limit for this path
        limit, window = self._get_limit_for_path(request.url.path)
        
        # Check rate limit
        if not self._check_rate_limit(client_id, request.url.path, limit, window):
            # Rate limit exceeded
            logger.warning(f"Rate limit exceeded for {client_id} on {request.url.path}")
            
            # Get reset time
            reset_time = self._get_reset_time(client_id, request.url.path, window)
            
            # Return 429 Too Many Requests
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": limit,
                    "window": window,
                    "reset_in": reset_time,
                    "message": f"Too many requests. Please try again in {reset_time} seconds."
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time)
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining, reset_time = self._get_rate_limit_info(client_id, request.url.path, limit, window)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """
        Get client identifier for rate limiting.
        
        Args:
            request: HTTP request
            
        Returns:
            Client identifier
        """
        # Try to get user ID from request state
        user_id = None
        if hasattr(request.state, "user"):
            user_id = getattr(request.state.user, "id", None)
        
        if user_id:
            return f"user:{user_id}"
        
        # Fall back to IP address
        ip_address = request.client.host if request.client else "unknown"
        return f"ip:{ip_address}"
    
    def _get_limit_for_path(self, path: str) -> Tuple[int, int]:
        """
        Get rate limit for a specific path.
        
        Args:
            path: Request path
            
        Returns:
            Tuple of (limit, window)
        """
        # Check for exact path match
        if path in self.limits:
            return self.limits[path]
        
        # Check for prefix match
        for limit_path, (limit, window) in self.limits.items():
            if path.startswith(limit_path):
                return limit, window
        
        # Use default
        return self.default_limit, self.default_window
    
    def _check_rate_limit(self, client_id: str, path: str, limit: int, window: int) -> bool:
        """
        Check if client is within rate limit.
        
        Args:
            client_id: Client identifier
            path: Request path
            limit: Rate limit
            window: Time window in seconds
            
        Returns:
            True if within limit, False otherwise
        """
        key = f"{client_id}:{path}"
        current_time = time.time()
        
        if self.storage_backend == "redis" and self.redis_client:
            return self._check_redis_rate_limit(key, limit, window, current_time)
        else:
            return self._check_memory_rate_limit(key, limit, window, current_time)
    
    def _check_memory_rate_limit(self, key: str, limit: int, window: int, current_time: float) -> bool:
        """Check rate limit using in-memory storage."""
        # Clean old requests
        cutoff_time = current_time - window
        self.request_counts[key] = [
            timestamp for timestamp in self.request_counts[key]
            if timestamp > cutoff_time
        ]
        
        # Check if limit exceeded
        if len(self.request_counts[key]) >= limit:
            return False
        
        # Add current request
        self.request_counts[key].append(current_time)
        return True
    
    def _check_redis_rate_limit(self, key: str, limit: int, window: int, current_time: float) -> bool:
        """Check rate limit using Redis storage."""
        try:
            # Use Redis sorted set for rate limiting
            redis_key = f"ratelimit:{key}"
            
            # Remove old entries
            self.redis_client.zremrangebyscore(redis_key, 0, current_time - window)
            
            # Get current count
            current_count = self.redis_client.zcard(redis_key)
            
            # Check if limit exceeded
            if current_count >= limit:
                return False
            
            # Add current request
            self.redis_client.zadd(redis_key, {str(current_time): current_time})
            self.redis_client.expire(redis_key, window)
            
            return True
        except Exception as e:
            logger.error(f"Redis rate limit error: {e}")
            # Fall back to memory storage
            return self._check_memory_rate_limit(key, limit, window, current_time)
    
    def _get_reset_time(self, client_id: str, path: str, window: int) -> int:
        """
        Get time until rate limit resets.
        
        Args:
            client_id: Client identifier
            path: Request path
            window: Time window in seconds
            
        Returns:
            Seconds until reset
        """
        key = f"{client_id}:{path}"
        current_time = time.time()
        
        if self.storage_backend == "redis" and self.redis_client:
            return self._get_redis_reset_time(key, window, current_time)
        else:
            return self._get_memory_reset_time(key, window, current_time)
    
    def _get_memory_reset_time(self, key: str, window: int, current_time: float) -> int:
        """Get reset time using in-memory storage."""
        if key not in self.request_counts or not self.request_counts[key]:
            return 0
        
        # Get oldest request time
        oldest_time = min(self.request_counts[key])
        reset_time = int(oldest_time + window - current_time)
        
        return max(0, reset_time)
    
    def _get_redis_reset_time(self, key: str, window: int, current_time: float) -> int:
        """Get reset time using Redis storage."""
        try:
            redis_key = f"ratelimit:{key}"
            
            # Get oldest request time
            oldest = self.redis_client.zrange(redis_key, 0, 0, withscores=True)
            
            if not oldest:
                return 0
            
            oldest_time = oldest[0][1]
            reset_time = int(oldest_time + window - current_time)
            
            return max(0, reset_time)
        except Exception as e:
            logger.error(f"Redis reset time error: {e}")
            return window
    
    def _get_rate_limit_info(self, client_id: str, path: str, limit: int, window: int) -> Tuple[int, int]:
        """
        Get rate limit information.
        
        Args:
            client_id: Client identifier
            path: Request path
            limit: Rate limit
            window: Time window in seconds
            
        Returns:
            Tuple of (remaining_requests, reset_time)
        """
        key = f"{client_id}:{path}"
        current_time = time.time()
        
        if self.storage_backend == "redis" and self.redis_client:
            return self._get_redis_rate_limit_info(key, limit, window, current_time)
        else:
            return self._get_memory_rate_limit_info(key, limit, window, current_time)
    
    def _get_memory_rate_limit_info(self, key: str, limit: int, window: int, current_time: float) -> Tuple[int, int]:
        """Get rate limit info using in-memory storage."""
        # Clean old requests
        cutoff_time = current_time - window
        if key in self.request_counts:
            self.request_counts[key] = [
                timestamp for timestamp in self.request_counts[key]
                if timestamp > cutoff_time
            ]
            current_count = len(self.request_counts[key])
        else:
            current_count = 0
        
        # Calculate remaining requests
        remaining = max(0, limit - current_count)
        
        # Calculate reset time
        reset_time = 0
        if current_count > 0:
            oldest_time = min(self.request_counts[key])
            reset_time = int(oldest_time + window - current_time)
            reset_time = max(0, reset_time)
        
        return remaining, reset_time
    
    def _get_redis_rate_limit_info(self, key: str, limit: int, window: int, current_time: float) -> Tuple[int, int]:
        """Get rate limit info using Redis storage."""
        try:
            redis_key = f"ratelimit:{key}"
            
            # Remove old entries
            self.redis_client.zremrangebyscore(redis_key, 0, current_time - window)
            
            # Get current count
            current_count = self.redis_client.zcard(redis_key)
            
            # Calculate remaining requests
            remaining = max(0, limit - current_count)
            
            # Calculate reset time
            reset_time = 0
            if current_count > 0:
                oldest = self.redis_client.zrange(redis_key, 0, 0, withscores=True)
                if oldest:
                    oldest_time = oldest[0][1]
                    reset_time = int(oldest_time + window - current_time)
                    reset_time = max(0, reset_time)
            
            return remaining, reset_time
        except Exception as e:
            logger.error(f"Redis rate limit info error: {e}")
            return limit, window


# Rate limit configurations
RATE_LIMIT_CONFIGS = {
    # Public endpoints (more restrictive)
    "/api/v1/auth/login": (10, 300),  # 10 requests per 5 minutes
    "/api/v1/auth/register": (5, 3600),  # 5 requests per hour
    "/api/v1/auth/forgot-password": (3, 3600),  # 3 requests per hour
    
    # User endpoints
    "/api/v1/users": (100, 60),  # 100 requests per minute
    
    # Book endpoints
    "/api/v1/books": (200, 60),  # 200 requests per minute
    
    # Borrowing endpoints
    "/api/v1/borrow": (50, 60),  # 50 requests per minute
    "/api/v1/return": (50, 60),  # 50 requests per minute
    
    # Search endpoints
    "/api/v1/search": (300, 60),  # 300 requests per minute
    
    # Admin endpoints (more restrictive)
    "/api/v1/admin": (50, 60),  # 50 requests per minute
}


def get_rate_limit_middleware(app: ASGIApp) -> RateLimitMiddleware:
    """
    Get rate limit middleware with default configuration.
    
    Args:
        app: ASGI application
        
    Returns:
        RateLimitMiddleware instance
    """
    return RateLimitMiddleware(
        app=app,
        default_limit=100,  # 100 requests per minute
        default_window=60,  # 1 minute
        limits=RATE_LIMIT_CONFIGS,
        storage_backend="redis"  # Use Redis in production
    )