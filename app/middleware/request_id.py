"""
Request ID middleware for tracking requests across services.
"""
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.utils.logging import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add a unique request ID to each request.
    
    The request ID is:
    1. Generated for each incoming request
    2. Added to the request state
    3. Added to response headers
    4. Included in all log messages for that request
    """
    
    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID"):
        super().__init__(app)
        self.header_name = header_name
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and add request ID.
        """
        # Get or generate request ID
        request_id = request.headers.get(self.header_name)
        if not request_id:
            request_id = str(uuid.uuid4())
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Add request ID to logger
        logger_adapter = logging.LoggerAdapter(logger, {"request_id": request_id})
        
        # Log request start
        logger_adapter.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "unknown",
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add request ID to response headers
            response.headers[self.header_name] = request_id
            
            # Log request completion
            logger_adapter.info(
                f"Request completed: {request.method} {request.url.path} - Status: {response.status_code}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration": 0,  # Would need timing middleware for actual duration
                }
            )
            
            return response
            
        except Exception as exc:
            # Log request error
            logger_adapter.error(
                f"Request failed: {request.method} {request.url.path} - Error: {str(exc)}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(exc),
                    "error_type": exc.__class__.__name__,
                },
                exc_info=True,
            )
            raise


# For logging in the middleware
import logging