"""
Background job service with Celery.
Covers: SCRUM-20, SCRUM-35
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from celery import Celery
from celery.schedules import crontab

from app.config.settings import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Create Celery app
celery_app = Celery(
    'library_tasks',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['app.tasks.email_tasks', 'app.tasks.background_tasks', 'app.tasks.cleanup_tasks']
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=1,
)

# Scheduled tasks (beat schedule)
celery_app.conf.beat_schedule = {
    # Daily tasks
    'send-overdue-reminders-daily': {
        'task': 'app.tasks.email_tasks.send_overdue_reminders',
        'schedule': crontab(hour=9, minute=0),  # 9:00 AM daily
        'args': (),
    },
    'update-overdue-status-daily': {
        'task': 'app.tasks.background_tasks.update_overdue_borrowings',
        'schedule': crontab(hour=0, minute=0),  # Midnight daily
        'args': (),
    },
    'cleanup-old-sessions-daily': {
        'task': 'app.tasks.cleanup_tasks.cleanup_old_sessions',
        'schedule': crontab(hour=2, minute=0),  # 2:00 AM daily
        'args': (),
    },
    
    # Weekly tasks
    'send-weekly-report': {
        'task': 'app.tasks.email_tasks.send_weekly_report',
        'schedule': crontab(day_of_week=0, hour=10, minute=0),  # Sunday 10:00 AM
        'args': (),
    },
    
    # Monthly tasks
    'generate-monthly-statistics': {
        'task': 'app.tasks.background_tasks.generate_monthly_statistics',
        'schedule': crontab(day_of_month=1, hour=0, minute=0),  # 1st of month
        'args': (),
    },
}


class BackgroundService:
    """Service for managing background jobs."""
    
    @staticmethod
    def send_welcome_email(user_id: int, user_email: str, user_name: str) -> str:
        """
        Send welcome email to new user.
        
        Args:
            user_id: User ID
            user_email: User email
            user_name: User name
            
        Returns:
            Task ID
        """
        from app.tasks.email_tasks import send_welcome_email_task
        
        try:
            task = send_welcome_email_task.delay(user_id, user_email, user_name)
            logger.info(f"Welcome email task queued for user {user_id}: {task.id}")
            return task.id
        except Exception as e:
            logger.error(f"Failed to queue welcome email task: {e}")
            return None
    
    @staticmethod
    def send_borrowing_confirmation(borrowing_id: int) -> str:
        """
        Send borrowing confirmation email.
        
        Args:
            borrowing_id: Borrowing ID
            
        Returns:
            Task ID
        """
        from app.tasks.email_tasks import send_borrowing_confirmation_task
        
        try:
            task = send_borrowing_confirmation_task.delay(borrowing_id)
            logger.info(f"Borrowing confirmation task queued for borrowing {borrowing_id}: {task.id}")
            return task.id
        except Exception as e:
            logger.error(f"Failed to queue borrowing confirmation task: {e}")
            return None
    
    @staticmethod
    def send_return_confirmation(borrowing_id: int, fine_amount: float = 0.0) -> str:
        """
        Send return confirmation email.
        
        Args:
            borrowing_id: Borrowing ID
            fine_amount: Fine amount (if any)
            
        Returns:
            Task ID
        """
        from app.tasks.email_tasks import send_return_confirmation_task
        
        try:
            task = send_return_confirmation_task.delay(borrowing_id, fine_amount)
            logger.info(f"Return confirmation task queued for borrowing {borrowing_id}: {task.id}")
            return task.id
        except Exception as e:
            logger.error(f"Failed to queue return confirmation task: {e}")
            return None
    
    @staticmethod
    def send_overdue_notification(borrowing_id: int) -> str:
        """
        Send overdue notification email.
        
        Args:
            borrowing_id: Borrowing ID
            
        Returns:
            Task ID
        """
        from app.tasks.email_tasks import send_overdue_notification_task
        
        try:
            task = send_overdue_notification_task.delay(borrowing_id)
            logger.info(f"Overdue notification task queued for borrowing {borrowing_id}: {task.id}")
            return task.id
        except Exception as e:
            logger.error(f"Failed to queue overdue notification task: {e}")
            return None
    
    @staticmethod
    def generate_user_report(user_id: int, report_type: str = "borrowing_history") -> str:
        """
        Generate user report.
        
        Args:
            user_id: User ID
            report_type: Type of report
            
        Returns:
            Task ID
        """
        from app.tasks.background_tasks import generate_user_report_task
        
        try:
            task = generate_user_report_task.delay(user_id, report_type)
            logger.info(f"User report task queued for user {user_id}: {task.id}")
            return task.id
        except Exception as e:
            logger.error(f"Failed to queue user report task: {e}")
            return None
    
    @staticmethod
    def generate_system_report(report_type: str = "monthly_stats") -> str:
        """
        Generate system report.
        
        Args:
            report_type: Type of report
            
        Returns:
            Task ID
        """
        from app.tasks.background_tasks import generate_system_report_task
        
        try:
            task = generate_system_report_task.delay(report_type)
            logger.info(f"System report task queued: {task.id}")
            return task.id
        except Exception as e:
            logger.error(f"Failed to queue system report task: {e}")
            return None
    
    @staticmethod
    def cleanup_old_data(data_type: str, days_old: int = 30) -> str:
        """
        Cleanup old data.
        
        Args:
            data_type: Type of data to cleanup
            days_old: Age threshold in days
            
        Returns:
            Task ID
        """
        from app.tasks.cleanup_tasks import cleanup_old_data_task
        
        try:
            task = cleanup_old_data_task.delay(data_type, days_old)
            logger.info(f"Cleanup task queued for {data_type}: {task.id}")
            return task.id
        except Exception as e:
            logger.error(f"Failed to queue cleanup task: {e}")
            return None
    
    @staticmethod
    def get_task_status(task_id: str) -> Dict[str, Any]:
        """
        Get task status.
        
        Args:
            task_id: Celery task ID
            
        Returns:
            Task status information
        """
        try:
            from celery.result import AsyncResult
            
            task_result = AsyncResult(task_id, app=celery_app)
            
            status_info = {
                "task_id": task_id,
                "status": task_result.status,
                "ready": task_result.ready(),
                "successful": task_result.successful(),
                "failed": task_result.failed(),
            }
            
            if task_result.ready():
                if task_result.successful():
                    status_info["result"] = task_result.result
                elif task_result.failed():
                    status_info["error"] = str(task_result.result)
                    status_info["traceback"] = task_result.traceback
            
            return status_info
        except Exception as e:
            logger.error(f"Failed to get task status for {task_id}: {e}")
            return {
                "task_id": task_id,
                "status": "UNKNOWN",
                "error": str(e)
            }
    
    @staticmethod
    def get_queue_stats() -> Dict[str, Any]:
        """
        Get queue statistics.
        
        Returns:
            Queue statistics
        """
        try:
            # This would require Redis inspection
            # For now, return basic stats
            inspector = celery_app.control.inspect()
            
            stats = {
                "active_workers": 0,
                "scheduled_tasks": 0,
                "active_tasks": 0,
                "reserved_tasks": 0,
            }
            
            if inspector:
                active = inspector.active()
                scheduled = inspector.scheduled()
                reserved = inspector.reserved()
                
                if active:
                    stats["active_workers"] = len(active)
                    stats["active_tasks"] = sum(len(tasks) for tasks in active.values())
                
                if scheduled:
                    stats["scheduled_tasks"] = sum(len(tasks) for tasks in scheduled.values())
                
                if reserved:
                    stats["reserved_tasks"] = sum(len(tasks) for tasks in reserved.values())
            
            return stats
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {
                "error": str(e),
                "active_workers": 0,
                "scheduled_tasks": 0,
                "active_tasks": 0,
                "reserved_tasks": 0,
            }
    
    @staticmethod
    def health_check() -> Dict[str, Any]:
        """
        Perform health check on background job system.
        
        Returns:
            Health check results
        """
        try:
            # Check Celery worker status
            inspector = celery_app.control.inspect()
            
            if not inspector:
                return {
                    "status": "unhealthy",
                    "message": "Cannot connect to Celery workers",
                    "workers": []
                }
            
            # Ping workers
            ping_result = inspector.ping()
            
            if not ping_result:
                return {
                    "status": "unhealthy",
                    "message": "No workers responding to ping",
                    "workers": []
                }
            
            workers = []
            for worker, response in ping_result.items():
                workers.append({
                    "name": worker,
                    "status": "active",
                    "response_time": response.get("ok", "unknown")
                })
            
            # Get queue stats
            queue_stats = BackgroundService.get_queue_stats()
            
            return {
                "status": "healthy",
                "message": f"{len(workers)} workers active",
                "workers": workers,
                "queue_stats": queue_stats,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Background job health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": str(e),
                "workers": [],
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @staticmethod
    def schedule_custom_task(
        task_name: str,
        args: tuple = (),
        kwargs: dict = None,
        schedule_time: datetime = None,
        schedule_seconds: int = None
    ) -> str:
        """
        Schedule a custom task.
        
        Args:
            task_name: Name of the task to schedule
            args: Task arguments
            kwargs: Task keyword arguments
            schedule_time: Specific time to run the task
            schedule_seconds: Seconds from now to run the task
            
        Returns:
            Task ID
        """
        try:
            from celery import current_app
            
            if schedule_time:
                # Schedule at specific time
                task = current_app.send_task(
                    task_name,
                    args=args,
                    kwargs=kwargs or {},
                    eta=schedule_time
                )
            elif schedule_seconds:
                # Schedule after specific seconds
                task = current_app.send_task(
                    task_name,
                    args=args,
                    kwargs=kwargs or {},
                    countdown=schedule_seconds
                )
            else:
                # Run immediately
                task = current_app.send_task(
                    task_name,
                    args=args,
                    kwargs=kwargs or {}
                )
            
            logger.info(f"Custom task {task_name} scheduled: {task.id}")
            return task.id
        except Exception as e:
            logger.error(f"Failed to schedule custom task {task_name}: {e}")
            return None