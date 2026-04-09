"""
Security middleware for adding security headers.
Covers: SCRUM-38, SCRUM-39
"""
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.utils.logging import get_logger

logger = get_logger(__name__)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""
    
    def __init__(
        self,
        app: ASGIApp,
        csp_directives: dict = None,
        hsts_max_age: int = 31536000,  # 1 year
        frame_options: str = "DENY",
        content_type_options: str = "nosniff",
        referrer_policy: str = "strict-origin-when-cross-origin",
        permissions_policy: dict = None
    ):
        super().__init__(app)
        self.csp_directives = csp_directives or {
            "default-src": ["'self'"],
            "script-src": ["'self'", "'unsafe-inline'"],
            "style-src": ["'self'", "'unsafe-inline'"],
            "img-src": ["'self'", "data:", "https:"],
            "font-src": ["'self'", "https:"],
            "connect-src": ["'self'"],
            "frame-src": ["'none'"],
            "object-src": ["'none'"],
            "base-uri": ["'self'"],
            "form-action": ["'self'"]
        }
        self.hsts_max_age = hsts_max_age
        self.frame_options = frame_options
        self.content_type_options = content_type_options
        self.referrer_policy = referrer_policy
        self.permissions_policy = permissions_policy or {
            "accelerometer": "()",
            "camera": "()",
            "geolocation": "()",
            "gyroscope": "()",
            "magnetometer": "()",
            "microphone": "()",
            "payment": "()",
            "usb": "()"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add security headers.
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler
            
        Returns:
            HTTP response with security headers
        """
        # Process request
        response = await call_next(request)
        
        # Add security headers
        self._add_security_headers(response)
        
        return response
    
    def _add_security_headers(self, response: Response):
        """Add security headers to response."""
        
        # Content Security Policy
        csp_header = self._build_csp_header()
        if csp_header:
            response.headers["Content-Security-Policy"] = csp_header
        
        # HTTP Strict Transport Security
        if self.hsts_max_age > 0:
            response.headers["Strict-Transport-Security"] = f"max-age={self.hsts_max_age}; includeSubDomains"
        
        # X-Frame-Options
        if self.frame_options:
            response.headers["X-Frame-Options"] = self.frame_options
        
        # X-Content-Type-Options
        if self.content_type_options:
            response.headers["X-Content-Type-Options"] = self.content_type_options
        
        # Referrer-Policy
        if self.referrer_policy:
            response.headers["Referrer-Policy"] = self.referrer_policy
        
        # Permissions-Policy
        permissions_header = self._build_permissions_header()
        if permissions_header:
            response.headers["Permissions-Policy"] = permissions_header
        
        # X-XSS-Protection (legacy, but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Cache-Control for sensitive endpoints
        if any(path in response.url.path for path in ["/api/", "/admin/", "/auth/"]):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        
        # Add server header (optional - can be removed for security)
        response.headers["Server"] = "LibraryManagementSystem"
        
        logger.debug("Security headers added to response")
    
    def _build_csp_header(self) -> str:
        """Build Content Security Policy header."""
        directives = []
        
        for directive, sources in self.csp_directives.items():
            if sources:
                sources_str = " ".join(sources)
                directives.append(f"{directive} {sources_str}")
        
        return "; ".join(directives)
    
    def _build_permissions_header(self) -> str:
        """Build Permissions-Policy header."""
        policies = []
        
        for feature, allowlist in self.permissions_policy.items():
            policies.append(f"{feature}={allowlist}")
        
        return ", ".join(policies)
    
    @staticmethod
    def validate_cors_origin(origin: str, allowed_origins: list) -> bool:
        """
        Validate CORS origin.
        
        Args:
            origin: Request origin
            allowed_origins: List of allowed origins
            
        Returns:
            True if origin is allowed
        """
        if not origin:
            return False
        
        # Allow all origins in development
        if "*" in allowed_origins:
            return True
        
        # Check exact match
        if origin in allowed_origins:
            return True
        
        # Check wildcard domains
        for allowed in allowed_origins:
            if allowed.startswith("*."):
                domain = allowed[2:]  # Remove "*."
                if origin.endswith(domain):
                    return True
        
        return False
    
    @staticmethod
    def sanitize_input(input_string: str) -> str:
        """
        Basic input sanitization.
        
        Args:
            input_string: Input string
            
        Returns:
            Sanitized string
        """
        if not input_string:
            return ""
        
        # Remove potentially dangerous characters
        dangerous_chars = ["<", ">", "\"", "'", "&", ";", "|", "`", "$", "(", ")", "{", "}", "[", "]"]
        
        sanitized = input_string
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, "")
        
        # Limit length
        max_length = 1000
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized.strip()
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email format.
        
        Args:
            email: Email address
            
        Returns:
            True if email is valid
        """
        import re
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_password(password: str) -> tuple:
        """
        Validate password strength.
        
        Args:
            password: Password
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if len(password) > 128:
            return False, "Password must be at most 128 characters long"
        
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        
        # Check for at least one lowercase letter
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        
        # Check for at least one digit
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit"
        
        # Check for at least one special character
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            return False, "Password must contain at least one special character"
        
        # Check for common passwords (simplified)
        common_passwords = ["password", "123456", "qwerty", "admin", "letmein"]
        if password.lower() in common_passwords:
            return False, "Password is too common"
        
        return True, "Password is strong"