"""
Audit logging service.
Covers: SCRUM-36, SCRUM-37
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, or_
from datetime import datetime, timedelta
import logging
import json

from app.models.audit_log import AuditLog, AuditAction, AuditResource
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AuditService:
    """Service for audit logging operations."""
    
    @staticmethod
    async def log_action(
        db: AsyncSession,
        user_id: Optional[int],
        action: AuditAction,
        resource_type: AuditResource,
        resource_id: Optional[int],
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """
        Log an audit action.
        
        Args:
            db: Database session
            user_id: ID of user performing action (None for system actions)
            action: Type of action
            resource_type: Type of resource being acted upon
            resource_id: ID of resource being acted upon
            details: Additional details about the action
            ip_address: IP address of requester
            user_agent: User agent string
            
        Returns:
            Created audit log entry
        """
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=json.dumps(details) if details else None,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            db.add(audit_log)
            await db.commit()
            await db.refresh(audit_log)
            
            logger.debug(f"Audit log created: {action.value} on {resource_type.value} by user {user_id}")
            return audit_log
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            await db.rollback()
            raise
    
    @staticmethod
    async def get_audit_log(
        log_id: int,
        db: AsyncSession
    ) -> Optional[AuditLog]:
        """
        Get an audit log entry by ID.
        
        Args:
            log_id: Audit log ID
            db: Database session
            
        Returns:
            Audit log entry or None
        """
        query = select(AuditLog).where(AuditLog.id == log_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def search_audit_logs(
        db: AsyncSession,
        user_id: Optional[int] = None,
        action: Optional[AuditAction] = None,
        resource_type: Optional[AuditResource] = None,
        resource_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        ip_address: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Search audit logs with filters.
        
        Args:
            db: Database session
            user_id: Filter by user ID
            action: Filter by action type
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            start_date: Filter by start date
            end_date: Filter by end date
            ip_address: Filter by IP address
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of audit log entries
        """
        query = select(AuditLog)
        
        filters = []
        
        if user_id is not None:
            filters.append(AuditLog.user_id == user_id)
        
        if action:
            filters.append(AuditLog.action == action)
        
        if resource_type:
            filters.append(AuditLog.resource_type == resource_type)
        
        if resource_id is not None:
            filters.append(AuditLog.resource_id == resource_id)
        
        if start_date:
            filters.append(AuditLog.created_at >= start_date)
        
        if end_date:
            filters.append(AuditLog.created_at <= end_date)
        
        if ip_address:
            filters.append(AuditLog.ip_address == ip_address)
        
        if filters:
            query = query.where(and_(*filters))
        
        query = query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_audit_stats(
        db: AsyncSession,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get audit statistics.
        
        Args:
            db: Database session
            days: Number of days to include in statistics
            
        Returns:
            Audit statistics
        """
        from sqlalchemy import func, text
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Total logs in period
        total_query = select(func.count(AuditLog.id)).where(
            AuditLog.created_at >= start_date,
            AuditLog.created_at <= end_date
        )
        total_result = await db.execute(total_query)
        total_logs = total_result.scalar()
        
        # Logs by action
        actions_query = select(
            AuditLog.action,
            func.count(AuditLog.id).label('count')
        ).where(
            AuditLog.created_at >= start_date,
            AuditLog.created_at <= end_date
        ).group_by(AuditLog.action)
        
        actions_result = await db.execute(actions_query)
        logs_by_action = {row[0].value: row[1] for row in actions_result.all()}
        
        # Logs by resource type
        resources_query = select(
            AuditLog.resource_type,
            func.count(AuditLog.id).label('count')
        ).where(
            AuditLog.created_at >= start_date,
            AuditLog.created_at <= end_date
        ).group_by(AuditLog.resource_type)
        
        resources_result = await db.execute(resources_query)
        logs_by_resource = {row[0].value: row[1] for row in resources_result.all()}
        
        # Logs by user (top 10)
        users_query = select(
            AuditLog.user_id,
            func.count(AuditLog.id).label('count')
        ).where(
            AuditLog.created_at >= start_date,
            AuditLog.created_at <= end_date,
            AuditLog.user_id.isnot(None)
        ).group_by(AuditLog.user_id).order_by(desc('count')).limit(10)
        
        users_result = await db.execute(users_query)
        top_users = [{"user_id": row[0], "count": row[1]} for row in users_result.all()]
        
        # Logs by day (last 7 days)
        daily_query = text("""
            SELECT DATE(created_at) as day, COUNT(*) as count
            FROM audit_logs
            WHERE created_at >= :start_date AND created_at <= :end_date
            GROUP BY DATE(created_at)
            ORDER BY day DESC
            LIMIT 7
        """)
        
        daily_result = await db.execute(
            daily_query,
            {"start_date": start_date, "end_date": end_date}
        )
        
        logs_by_day = {}
        for row in daily_result.all():
            logs_by_day[row[0].isoformat()] = row[1]
        
        return {
            "period_days": days,
            "total_logs": total_logs,
            "logs_by_action": logs_by_action,
            "logs_by_resource": logs_by_resource,
            "top_users": top_users,
            "logs_by_day": logs_by_day,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    
    @staticmethod
    async def cleanup_old_logs(
        db: AsyncSession,
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
        from sqlalchemy import delete
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        delete_query = delete(AuditLog).where(AuditLog.created_at < cutoff_date)
        result = await db.execute(delete_query)
        await db.commit()
        
        deleted_count = result.rowcount
        logger.info(f"Cleaned up {deleted_count} audit logs older than {cutoff_date}")
        
        return deleted_count
    
    @staticmethod
    async def export_audit_logs(
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format: str = "json"
    ) -> List[Dict[str, Any]]:
        """
        Export audit logs for reporting.
        
        Args:
            db: Database session
            start_date: Start date for export
            end_date: End date for export
            format: Export format (only JSON supported for now)
            
        Returns:
            List of audit log entries as dictionaries
        """
        query = select(AuditLog)
        
        filters = []
        if start_date:
            filters.append(AuditLog.created_at >= start_date)
        if end_date:
            filters.append(AuditLog.created_at <= end_date)
        
        if filters:
            query = query.where(and_(*filters))
        
        query = query.order_by(AuditLog.created_at)
        
        result = await db.execute(query)
        logs = result.scalars().all()
        
        # Convert to dictionaries
        exported_logs = []
        for log in logs:
            log_dict = {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action.value,
                "resource_type": log.resource_type.value,
                "resource_id": log.resource_id,
                "details": json.loads(log.details) if log.details else None,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "created_at": log.created_at.isoformat()
            }
            exported_logs.append(log_dict)
        
        return exported_logs
    
    # Helper methods for common audit scenarios
    
    @staticmethod
    async def log_user_login(
        db: AsyncSession,
        user_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Log user login action."""
        return await AuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditAction.LOGIN,
            resource_type=AuditResource.USER,
            resource_id=user_id,
            details={"event": "user_login"},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    async def log_user_logout(
        db: AsyncSession,
        user_id: int,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Log user logout action."""
        return await AuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditAction.LOGOUT,
            resource_type=AuditResource.USER,
            resource_id=user_id,
            details={"event": "user_logout"},
            ip_address=ip_address
        )
    
    @staticmethod
    async def log_book_borrow(
        db: AsyncSession,
        user_id: int,
        book_id: int,
        borrowing_id: int
    ) -> AuditLog:
        """Log book borrowing action."""
        return await AuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditAction.CREATE,
            resource_type=AuditResource.BORROWING,
            resource_id=borrowing_id,
            details={
                "event": "book_borrowed",
                "book_id": book_id,
                "borrowing_id": borrowing_id
            }
        )
    
    @staticmethod
    async def log_book_return(
        db: AsyncSession,
        user_id: int,
        book_id: int,
        borrowing_id: int,
        fine_amount: float = 0.0
    ) -> AuditLog:
        """Log book return action."""
        return await AuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditAction.UPDATE,
            resource_type=AuditResource.BORROWING,
            resource_id=borrowing_id,
            details={
                "event": "book_returned",
                "book_id": book_id,
                "borrowing_id": borrowing_id,
                "fine_amount": fine_amount
            }
        )
    
    @staticmethod
    async def log_book_create(
        db: AsyncSession,
        user_id: int,
        book_id: int,
        book_data: Dict[str, Any]
    ) -> AuditLog:
        """Log book creation action."""
        return await AuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditAction.CREATE,
            resource_type=AuditResource.BOOK,
            resource_id=book_id,
            details={
                "event": "book_created",
                "book_data": book_data
            }
        )
    
    @staticmethod
    async def log_book_update(
        db: AsyncSession,
        user_id: int,
        book_id: int,
        update_data: Dict[str, Any]
    ) -> AuditLog:
        """Log book update action."""
        return await AuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditAction.UPDATE,
            resource_type=AuditResource.BOOK,
            resource_id=book_id,
            details={
                "event": "book_updated",
                "update_data": update_data
            }
        )
    
    @staticmethod
    async def log_book_delete(
        db: AsyncSession,
        user_id: int,
        book_id: int
    ) -> AuditLog:
        """Log book deletion action."""
        return await AuditService.log_action(
            db=db,
            user_id=user_id,
            action=AuditAction.DELETE,
            resource_type=AuditResource.BOOK,
            resource_id=book_id,
            details={
                "event": "book_deleted",
                "book_id": book_id
            }
        )
    
    @staticmethod
    async def log_user_create(
        db: AsyncSession,
        admin_user_id: int,
        new_user_id: int,
        user_data: Dict[str, Any]
    ) -> AuditLog:
        """Log user creation action."""
        return await AuditService.log_action(
            db=db,
            user_id=admin_user_id,
            action=AuditAction.CREATE,
            resource_type=AuditResource.USER,
            resource_id=new_user_id,
            details={
                "event": "user_created",
                "user_data": user_data
            }
        )
    
    @staticmethod
    async def log_permission_change(
        db: AsyncSession,
        admin_user_id: int,
        target_user_id: int,
        permission_changes: Dict[str, Any]
    ) -> AuditLog:
        """Log permission change action."""
        return await AuditService.log_action(
            db=db,
            user_id=admin_user_id,
            action=AuditAction.UPDATE,
            resource_type=AuditResource.PERMISSION,
            resource_id=target_user_id,
            details={
                "event": "permission_changed",
                "target_user_id": target_user_id,
                "changes": permission_changes
            }
        )