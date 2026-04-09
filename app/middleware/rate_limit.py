"""
Rate limiting middleware.
Covers: SCRUM-39
"""
import time
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import logging
from datetime import datetime, timedelta

from app.services.cache_service import CacheService
from app.utils.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Rate limiting implementation."""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        requests_per_day: int = 10000,
        burst_limit: int = 10
    ):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Max requests per minute
            requests_per_hour: Max requests per hour
            requests_per_day: Max requests per day
            burst_limit: Max burst requests
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day
        self.burst_limit = burst_limit
    
    def get_client_identifier(self, request: Request) -> str:
        """
        Get client identifier for rate limiting.
        
        Args:
            request: FastAPI request
            
        Returns:
            Client identifier string
        """
        # Try to get authenticated user ID
        user = getattr(request.state, 'user', None)
        if user and user.get('id'):
            return f"user:{user['id']}"
        
        # Fall back to IP address
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # Get the first IP in the chain
            client_ip = forwarded_for.split(',')[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return f"ip:{client_ip}"
    
    def check_rate_limit(
        self,
        identifier: str,
        endpoint: str
    ) -> Dict[str, Any]:
        """
        Check rate limit for identifier and endpoint.
        
        Args:
            identifier: Client identifier
            endpoint: API endpoint
            
        Returns:
            Rate limit status
        """
        if not CacheService.is_available():
            # If Redis is down, allow all requests
            return {
                "allowed": True,
                "limit": 0,
                "remaining": 0,
                "reset_in": 0,
                "cache_down": True
            }
        
        # Create rate limit keys
        current_minute = int(time.time() / 60)
        current_hour = int(time.time() / 3600)
        current_day = datetime.utcnow().strftime("%Y%m%d")
        
        minute_key = f"ratelimit:{identifier}:{endpoint}:minute:{current_minute}"
        hour_key = f"ratelimit:{identifier}:{endpoint}:hour:{current_hour}"
        day_key = f"ratelimit:{identifier}:{endpoint}:day:{current_day}"
        burst_key = f"ratelimit:{identifier}:{endpoint}:burst"
        
        # Check burst limit first (sliding window of 10 seconds)
        burst_result = CacheService.check_rate_limit(
            burst_key,
            limit=self.burst_limit,
            window_seconds=10
        )
        
        if not burst_result.get("allowed", True):
            return {
                "allowed": False,
                "limit": self.burst_limit,
                "remaining": burst_result.get("remaining", 0),
                "reset_in": burst_result.get("reset_in", 10),
                "window": "burst",
                "identifier": identifier,
                "endpoint": endpoint
            }
        
        # Check minute limit
        minute_result = CacheService.check_rate_limit(
            minute_key,
            limit=self.requests_per_minute,
            window_seconds=60
        )
        
        if not minute_result.get("allowed", True):
            return {
                "allowed": False,
                "limit": self.requests_per_minute,
                "remaining": minute_result.get("remaining", 0),
                "reset_in": minute_result.get("reset_in", 60),
                "window": "minute",
                "identifier": identifier,
                "endpoint": endpoint
            }
        
        # Check hour limit
        hour_result = CacheService.check_rate_limit(
            hour_key,
            limit=self.requests_per_hour,
            window_seconds=3600
        )
        
        if not hour_result.get("allowed", True):
            return {
                "allowed": False,
                "limit": self.requests_per_hour,
                "remaining": hour_result.get("remaining", 0),
                "reset_in": hour_result.get("reset_in", 3600),
                "window": "hour",
                "identifier": identifier,
                "endpoint": endpoint
            }
        
        # Check day limit
        day_result = CacheService.check_rate_limit(
            day_key,
            limit=self.requests_per_day,
            window_seconds=86400
        )
        
        if not day_result.get("allowed", True):
            return {
                "allowed": False,
                "limit": self.requests_per_day,
                "remaining": day_result.get("remaining", 0),
                "reset_in": day_result.get("reset_in", 86400),
                "window": "day",
                "identifier": identifier,
                "endpoint": endpoint
            }
        
        # All checks passed
        return {
            "allowed": True,
            "limit": self.requests_per_minute,
            "remaining": minute_result.get("remaining", self.requests_per_minute),
            "reset_in": 60,
            "window": "minute",
            "identifier": identifier,
            "endpoint": endpoint
        }
    
    async def __call__(self, request: Request, call_next):
        """
        Rate limiting middleware.
        
        Args:
            request: FastAPI request
            call_next: Next middleware or endpoint
            
        Returns:
            HTTP response
        """
        # Skip rate limiting for certain paths
        if self.should_skip_rate_limit(request):
            return await call_next(request)
        
        # Get client identifier
        identifier = self.get_client_identifier(request)
        endpoint = request.url.path
        
        # Check rate limit
        rate_limit_status = self.check_rate_limit(identifier, endpoint)
        
        if not rate_limit_status.get("allowed", True):
            logger.warning(
                f"Rate limit exceeded for {identifier} on {endpoint}: "
                f"{rate_limit_status.get('window', 'unknown')} window"
            )
            
            # Add rate limit headers
            headers = {
                "X-RateLimit-Limit": str(rate_limit_status.get("limit", 0)),
                "X-RateLimit-Remaining": str(rate_limit_status.get("remaining", 0)),
                "X-RateLimit-Reset": str(int(time.time() + rate_limit_status.get("reset_in", 60))),
                "X-RateLimit-Window": rate_limit_status.get("window", "unknown"),
                "Retry-After": str(rate_limit_status.get("reset_in", 60))
            }
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"Rate limit exceeded. Try again in {rate_limit_status.get('reset_in', 60)} seconds.",
                    "window": rate_limit_status.get("window"),
                    "limit": rate_limit_status.get("limit"),
                    "remaining": rate_limit_status.get("remaining"),
                    "reset_in": rate_limit_status.get("reset_in")
                },
                headers=headers
            )
        
        # Add rate limit headers to successful response
        response = await call_next(request)
        
        response.headers["X-RateLimit-Limit"] = str(rate_limit_status.get("limit", 0))
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_status.get("remaining", 0))
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + rate_limit_status.get("reset_in", 60)))
        response.headers["X-RateLimit-Window"] = rate_limit_status.get("window", "minute")
        
        return response
    
    def should_skip_rate_limit(self, request: Request) -> bool:
        """
        Determine if rate limiting should be skipped for this request.
        
        Args:
            request: FastAPI request
            
        Returns:
            True if rate limiting should be skipped
        """
        # Skip health checks
        if request.url.path in ["/health", "/health/database", "/health/full", "/docs", "/redoc", "/openapi.json"]:
            return True
        
        # Skip static files
        if request.url.path.startswith("/static/"):
            return True
        
        # Skip based on user role (admins might have higher limits)
        user = getattr(request.state, 'user', None)
        if user and user.get('role') == 'admin':
            # Admins still have limits, but we could adjust them here
            pass
        
        return False


class RateLimitConfig:
    """Rate limit configuration for different endpoints."""
    
    # Default limits
    DEFAULT_LIMITS = {
        "default": {
            "requests_per_minute": 60,
            "requests_per_hour": 1000,
            "requests_per_day": 10000,
            "burst_limit": 10
        },
        "auth": {
            "requests_per_minute": 30,  # Stricter limits for auth endpoints
            "requests_per_hour": 300,
            "requests_per_day": 1000,
            "burst_limit": 5
        },
        "admin": {
            "requests_per_minute": 120,  # Higher limits for admins
            "requests_per_hour": 5000,
            "requests_per_day": 50000,
            "burst_limit": 20
        },
        "public": {
            "requests_per_minute": 30,  # Stricter for public endpoints
            "requests_per_hour": 500,
            "requests_per_day": 5000,
            "burst_limit": 5
        }
    }
    
    # Endpoint patterns and their rate limit categories
    ENDPOINT_PATTERNS = {
        "/api/v1/auth/": "auth",
        "/api/v1/admin/": "admin",
        "/api/v1/users/": "default",
        "/api/v1/books/": "default",
        "/api/v1/borrow/": "default",
        "/api/v1/search/": "public",
        "/api/v1/health/": "public",
    }
    
    @classmethod
    def get_limits_for_endpoint(cls, endpoint: str) -> Dict[str, int]:
        """
        Get rate limits for a specific endpoint.
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            Rate limit configuration
        """
        for pattern, category in cls.ENDPOINT_PATTERNS.items():
            if endpoint.startswith(pattern):
                return cls.DEFAULT_LIMITS[category]
        
        return cls.DEFAULT_LIMITS["default"]


# Global rate limiter instance
default_rate_limiter = RateLimiter()


def get_rate_limiter_for_endpoint(endpoint: str) -> RateLimiter:
    """
    Get appropriate rate limiter for endpoint.
    
    Args:
        endpoint: API endpoint path
        
    Returns:
        RateLimiter instance
    """
    limits = RateLimitConfig.get_limits_for_endpoint(endpoint)
    return RateLimiter(**limits)


# Dependency for endpoint-specific rate limiting
def rate_limit_dependency(request: Request):
    """Dependency to apply rate limiting in specific endpoints."""
    endpoint = request.url.path
    limiter = get_rate_limiter_for_endpoint(endpoint)
    identifier = limiter.get_client_identifier(request)
    
    rate_limit_status = limiter.check_rate_limit(identifier, endpoint)
    
    if not rate_limit_status.get("allowed", True):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {rate_limit_status.get('reset_in', 60)} seconds."
        )
    
    return rate_limit_status