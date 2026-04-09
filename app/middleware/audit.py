"""
Audit middleware for logging user actions.
Covers: SCRUM-36, SCRUM-37
"""
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.services.audit_service import AuditService
from app.database import get_db
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware for audit logging."""
    
    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: list = None,
        include_paths: list = None
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico"
        ]
        self.include_paths = include_paths
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log audit information.
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler
            
        Returns:
            HTTP response
        """
        # Skip excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Check if path should be included
        if self.include_paths and not any(request.url.path.startswith(path) for path in self.include_paths):
            return await call_next(request)
        
        # Get request information
        method = request.method
        path = request.url.path
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # Get user information from request state (set by auth middleware)
        user_id = None
        if hasattr(request.state, "user"):
            user_id = getattr(request.state.user, "id", None)
        
        # Determine action and resource type from path
        action, resource_type = self._parse_path(method, path)
        
        # Create audit log
        try:
            db = next(get_db())
            
            AuditService.log_action(
                db=db,
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                details={
                    "method": method,
                    "path": path,
                    "query_params": dict(request.query_params),
                    "headers": dict(request.headers)
                },
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.debug(f"Audit log created: {method} {path} by user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
        
        # Process request
        response = await call_next(request)
        
        # Add audit information to response headers
        response.headers["X-Audit-Logged"] = "true"
        
        return response
    
    def _parse_path(self, method: str, path: str) -> tuple:
        """
        Parse path to determine action and resource type.
        
        Args:
            method: HTTP method
            path: Request path
            
        Returns:
            Tuple of (action, resource_type)
        """
        # Map HTTP methods to actions
        method_to_action = {
            "GET": "view",
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete"
        }
        
        action = method_to_action.get(method, "unknown")
        
        # Parse resource type from path
        parts = path.strip("/").split("/")
        
        # Common API patterns
        if len(parts) >= 2 and parts[0] == "api":
            # /api/v1/books -> books
            # /api/v1/books/1 -> books
            resource_type = parts[-2] if parts[-1].isdigit() else parts[-1]
        elif len(parts) >= 1:
            # /books -> books
            # /books/1 -> books
            resource_type = parts[-2] if parts[-1].isdigit() and len(parts) > 1 else parts[-1]
        else:
            resource_type = "unknown"
        
        # Clean up resource type
        resource_type = resource_type.replace("-", "_").lower()
        
        return action, resource_type