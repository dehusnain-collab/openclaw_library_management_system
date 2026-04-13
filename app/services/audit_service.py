"""
Audit logging service.
Covers: SCRUM-36, SCRUM-37
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.models.audit_log import AuditLog
from app.database import get_db
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AuditService:
    """Service for audit logging."""
    
    @staticmethod
    def log_action(
        db: Session,
        user_id: Optional[int],
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """
        Log an audit action.
        
        Args:
            db: Database session
            user_id: User ID (None for system actions)
            action: Action performed
            resource_type: Type of resource
            resource_id: Resource ID
            details: Additional details
            ip_address: IP address
            user_agent: User agent string
            
        Returns:
            AuditLog object
        """
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
                timestamp=datetime.utcnow()
            )
            
            db.add(audit_log)
            db.commit()
            db.refresh(audit_log)
            
            logger.debug(f"Audit log created: {action} on {resource_type} by user {user_id}")
            
            return audit_log
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            db.rollback()
            raise
    
    @staticmethod
    def log_user_action(
        db: Session,
        user_id: int,
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """
        Log a user action.
        
        Args:
            db: Database session
            user_id: User ID
            action: Action performed
            resource_type: Type of resource
            resource_id: Resource ID
            details: Additional details
            ip_address: IP address
            user_agent: User agent string
            
        Returns:
            AuditLog object
        """
        return AuditService.log_action(
            db=db,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_system_action(
        db: Session,
        action: str,
        resource_type: str,
        resource_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """
        Log a system action.
        
        Args:
            db: Database session
            action: Action performed
            resource_type: Type of resource
            resource_id: Resource ID
            details: Additional details
            
        Returns:
            AuditLog object
        """
        return AuditService.log_action(
            db=db,
            user_id=None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=None,
            user_agent=None
        )
    
    @staticmethod
    def get_user_audit_logs(
        db: Session,
        user_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """
        Get audit logs for a specific user.
        
        Args:
            db: Database session
            user_id: User ID
            limit: Maximum number of logs to return
            offset: Offset for pagination
            
        Returns:
            List of audit logs
        """
        try:
            logs = db.query(AuditLog)\
                .filter(AuditLog.user_id == user_id)\
                .order_by(desc(AuditLog.timestamp))\
                .offset(offset)\
                .limit(limit)\
                .all()
            
            return logs
        except Exception as e:
            logger.error(f"Failed to get user audit logs: {e}")
            return []
    
    @staticmethod
    def get_resource_audit_logs(
        db: Session,
        resource_type: str,
        resource_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """
        Get audit logs for a specific resource.
        
        Args:
            db: Database session
            resource_type: Type of resource
            resource_id: Resource ID (optional)
            limit: Maximum number of logs to return
            offset: Offset for pagination
            
        Returns:
            List of audit logs
        """
        try:
            query = db.query(AuditLog)\
                .filter(AuditLog.resource_type == resource_type)
            
            if resource_id is not None:
                query = query.filter(AuditLog.resource_id == resource_id)
            
            logs = query.order_by(desc(AuditLog.timestamp))\
                .offset(offset)\
                .limit(limit)\
                .all()
            
            return logs
        except Exception as e:
            logger.error(f"Failed to get resource audit logs: {e}")
            return []
    
    @staticmethod
    def search_audit_logs(
        db: Session,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """
        Search audit logs with filters.
        
        Args:
            db: Database session
            user_id: Filter by user ID
            action: Filter by action
            resource_type: Filter by resource type
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of logs to return
            offset: Offset for pagination
            
        Returns:
            List of audit logs
        """
        try:
            query = db.query(AuditLog)
            
            # Apply filters
            if user_id is not None:
                query = query.filter(AuditLog.user_id == user_id)
            
            if action is not None:
                query = query.filter(AuditLog.action == action)
            
            if resource_type is not None:
                query = query.filter(AuditLog.resource_type == resource_type)
            
            if start_date is not None:
                query = query.filter(AuditLog.timestamp >= start_date)
            
            if end_date is not None:
                query = query.filter(AuditLog.timestamp <= end_date)
            
            # Execute query
            logs = query.order_by(desc(AuditLog.timestamp))\
                .offset(offset)\
                .limit(limit)\
                .all()
            
            return logs
        except Exception as e:
            logger.error(f"Failed to search audit logs: {e}")
            return []
    
    @staticmethod
    def get_audit_statistics(
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get audit statistics.
        
        Args:
            db: Database session
            days: Number of days to include
            
        Returns:
            Statistics dictionary
        """
        try:
            from sqlalchemy import func, text
            
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Total logs
            total_logs = db.query(func.count(AuditLog.id))\
                .filter(AuditLog.timestamp >= start_date)\
                .scalar() or 0
            
            # Logs by action
            logs_by_action = db.query(
                AuditLog.action,
                func.count(AuditLog.id).label('count')
            )\
                .filter(AuditLog.timestamp >= start_date)\
                .group_by(AuditLog.action)\
                .order_by(text('count DESC'))\
                .all()
            
            # Logs by resource type
            logs_by_resource = db.query(
                AuditLog.resource_type,
                func.count(AuditLog.id).label('count')
            )\
                .filter(AuditLog.timestamp >= start_date)\
                .group_by(AuditLog.resource_type)\
                .order_by(text('count DESC'))\
                .all()
            
            # Logs by user
            logs_by_user = db.query(
                AuditLog.user_id,
                func.count(AuditLog.id).label('count')
            )\
                .filter(AuditLog.timestamp >= start_date)\
                .filter(AuditLog.user_id.isnot(None))\
                .group_by(AuditLog.user_id)\
                .order_by(text('count DESC'))\
                .limit(10)\
                .all()
            
            # Daily logs
            daily_logs = db.query(
                func.date(AuditLog.timestamp).label('date'),
                func.count(AuditLog.id).label('count')
            )\
                .filter(AuditLog.timestamp >= start_date)\
                .group_by(func.date(AuditLog.timestamp))\
                .order_by(text('date DESC'))\
                .limit(30)\
                .all()
            
            return {
                "period_days": days,
                "start_date": start_date.isoformat(),
                "total_logs": total_logs,
                "logs_by_action": [
                    {"action": action, "count": count}
                    for action, count in logs_by_action
                ],
                "logs_by_resource": [
                    {"resource_type": resource_type, "count": count}
                    for resource_type, count in logs_by_resource
                ],
                "top_users": [
                    {"user_id": user_id, "count": count}
                    for user_id, count in logs_by_user
                ],
                "daily_logs": [
                    {"date": date.isoformat() if hasattr(date, 'isoformat') else str(date), "count": count}
                    for date, count in daily_logs
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get audit statistics: {e}")
            return {
                "period_days": days,
                "error": str(e)
            }
    
    @staticmethod
    def cleanup_old_logs(
        db: Session,
        days_to_keep: int = 365
    ) -> int:
        """
        Cleanup old audit logs.
        
        Args:
            db: Database session
            days_to_keep: Number of days to keep logs
            
        Returns:
            Number of logs deleted
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Count logs to be deleted
            count_query = db.query(func.count(AuditLog.id))\
                .filter(AuditLog.timestamp < cutoff_date)
            
            count = count_query.scalar() or 0
            
            if count > 0:
                # Delete old logs
                delete_query = db.query(AuditLog)\
                    .filter(AuditLog.timestamp < cutoff_date)
                
                deleted_count = delete_query.delete(synchronize_session=False)
                db.commit()
                
                logger.info(f"Cleaned up {deleted_count} audit logs older than {days_to_keep} days")
                return deleted_count
            
            return 0
        except Exception as e:
            logger.error(f"Failed to cleanup old audit logs: {e}")
            db.rollback()
            return 0
    
    @staticmethod
    def export_audit_logs(
        db: Session,
        format: str = "json",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Export audit logs.
        
        Args:
            db: Database session
            format: Export format (json/csv)
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            List of audit log dictionaries
        """
        try:
            query = db.query(AuditLog)
            
            # Apply date filters
            if start_date is not None:
                query = query.filter(AuditLog.timestamp >= start_date)
            
            if end_date is not None:
                query = query.filter(AuditLog.timestamp <= end_date)
            
            # Get logs
            logs = query.order_by(AuditLog.timestamp).all()
            
            # Convert to dictionaries
            log_dicts = []
            for log in logs:
                log_dict = {
                    "id": log.id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "details": log.details,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None
                }
                log_dicts.append(log_dict)
            
            return log_dicts
        except Exception as e:
            logger.error(f"Failed to export audit logs: {e}")
            return []