"""
Structured logging utilities.
Covers: SCRUM-36, SCRUM-37
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
import traceback


class StructuredFormatter(logging.Formatter):
    """Formatter for structured JSON logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record
            
        Returns:
            JSON string
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.threadName,
            "process": record.processName,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        return json.dumps(log_data, default=str)


class AuditLogger:
    """Logger for audit events."""
    
    def __init__(self, name: str = "audit"):
        self.logger = logging.getLogger(name)
    
    def log_event(
        self,
        event_type: str,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[int] = None,
        action: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True
    ):
        """
        Log an audit event.
        
        Args:
            event_type: Type of event
            user_id: User ID
            resource_type: Type of resource
            resource_id: Resource ID
            action: Action performed
            details: Additional details
            ip_address: IP address
            user_agent: User agent string
            success: Whether the action was successful
        """
        log_data = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "success": success
        }
        
        self.logger.info(
            f"Audit event: {event_type}",
            extra={"audit": log_data}
        )
    
    def log_login(
        self,
        user_id: int,
        success: bool = True,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log login event."""
        self.log_event(
            event_type="login",
            user_id=user_id,
            action="login",
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
    
    def log_logout(
        self,
        user_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log logout event."""
        self.log_event(
            event_type="logout",
            user_id=user_id,
            action="logout",
            success=True,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_data_access(
        self,
        user_id: int,
        resource_type: str,
        resource_id: Optional[int] = None,
        action: str = "access",
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Log data access event."""
        self.log_event(
            event_type="data_access",
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True
        )
    
    def log_security_event(
        self,
        event_type: str,
        severity: str = "medium",
        user_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ):
        """Log security event."""
        log_data = {
            "event_type": event_type,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "details": details or {},
            "ip_address": ip_address
        }
        
        # Log at appropriate level based on severity
        if severity == "critical":
            self.logger.critical(
                f"Security event: {event_type}",
                extra={"security": log_data}
            )
        elif severity == "high":
            self.logger.error(
                f"Security event: {event_type}",
                extra={"security": log_data}
            )
        elif severity == "medium":
            self.logger.warning(
                f"Security event: {event_type}",
                extra={"security": log_data}
            )
        else:
            self.logger.info(
                f"Security event: {event_type}",
                extra={"security": log_data}
            )


class PerformanceLogger:
    """Logger for performance metrics."""
    
    def __init__(self, name: str = "performance"):
        self.logger = logging.getLogger(name)
    
    def log_request(
        self,
        method: str,
        path: str,
        duration_ms: float,
        status_code: int,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None
    ):
        """
        Log HTTP request performance.
        
        Args:
            method: HTTP method
            path: Request path
            duration_ms: Request duration in milliseconds
            status_code: HTTP status code
            user_id: User ID
            ip_address: IP address
        """
        log_data = {
            "type": "http_request",
            "timestamp": datetime.utcnow().isoformat(),
            "method": method,
            "path": path,
            "duration_ms": duration_ms,
            "status_code": status_code,
            "user_id": user_id,
            "ip_address": ip_address
        }
        
        # Log slow requests as warnings
        if duration_ms > 1000:  # > 1 second
            self.logger.warning(
                f"Slow request: {method} {path} took {duration_ms:.2f}ms",
                extra={"performance": log_data}
            )
        else:
            self.logger.info(
                f"Request: {method} {path} took {duration_ms:.2f}ms",
                extra={"performance": log_data}
            )
    
    def log_database_query(
        self,
        query: str,
        duration_ms: float,
        rows_returned: Optional[int] = None,
        user_id: Optional[int] = None
    ):
        """
        Log database query performance.
        
        Args:
            query: SQL query (or query type)
            duration_ms: Query duration in milliseconds
            rows_returned: Number of rows returned
            user_id: User ID
        """
        log_data = {
            "type": "database_query",
            "timestamp": datetime.utcnow().isoformat(),
            "query": query[:100] + "..." if len(query) > 100 else query,  # Truncate long queries
            "duration_ms": duration_ms,
            "rows_returned": rows_returned,
            "user_id": user_id
        }
        
        # Log slow queries as warnings
        if duration_ms > 100:  # > 100ms
            self.logger.warning(
                f"Slow query: {query[:50]}... took {duration_ms:.2f}ms",
                extra={"performance": log_data}
            )
        else:
            self.logger.debug(
                f"Query: {query[:50]}... took {duration_ms:.2f}ms",
                extra={"performance": log_data}
            )
    
    def log_cache_operation(
        self,
        operation: str,
        key: str,
        duration_ms: float,
        success: bool = True,
        user_id: Optional[int] = None
    ):
        """
        Log cache operation performance.
        
        Args:
            operation: Cache operation (get/set/delete)
            key: Cache key
            duration_ms: Operation duration in milliseconds
            success: Whether the operation was successful
            user_id: User ID
        """
        log_data = {
            "type": "cache_operation",
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "key": key,
            "duration_ms": duration_ms,
            "success": success,
            "user_id": user_id
        }
        
        # Log slow cache operations
        if duration_ms > 10:  # > 10ms
            self.logger.warning(
                f"Slow cache {operation}: {key} took {duration_ms:.2f}ms",
                extra={"performance": log_data}
            )
        else:
            self.logger.debug(
                f"Cache {operation}: {key} took {duration_ms:.2f}ms",
                extra={"performance": log_data}
            )


def setup_structured_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_json: bool = True
):
    """
    Set up structured logging.
    
    Args:
        log_level: Logging level
        log_file: Log file path (optional)
        enable_json: Whether to use JSON formatting
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    
    if enable_json:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
    
    root_logger.addHandler(console_handler)
    
    # Create file handler if log file is specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        
        if enable_json:
            file_handler.setFormatter(StructuredFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            )
        
        root_logger.addHandler(file_handler)
    
    # Create specialized loggers
    audit_logger = AuditLogger()
    performance_logger = PerformanceLogger()
    
    return audit_logger, performance_logger