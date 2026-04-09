"""
Celery configuration for background jobs.
Covers: SCRUM-20, SCRUM-35
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.config.settings')

# Create Celery app
celery_app = Celery('library_tasks')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
celery_app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
celery_app.autodiscover_tasks()

# Configure Celery
celery_app.conf.update(
    # Broker settings
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0'),
    
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    
    # Result settings
    result_expires=3600,  # 1 hour
    task_track_started=True,
    task_acks_late=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Queue settings
    task_default_queue='default',
    task_queues={
        'default': {
            'exchange': 'default',
            'exchange_type': 'direct',
            'routing_key': 'default',
        },
        'email': {
            'exchange': 'email',
            'exchange_type': 'direct',
            'routing_key': 'email',
        },
        'reports': {
            'exchange': 'reports',
            'exchange_type': 'direct',
            'routing_key': 'reports',
        },
        'cleanup': {
            'exchange': 'cleanup',
            'exchange_type': 'direct',
            'routing_key': 'cleanup',
        },
    },
    
    # Routing
    task_routes={
        'app.tasks.email_tasks.*': {'queue': 'email'},
        'app.tasks.background_tasks.generate_*': {'queue': 'reports'},
        'app.tasks.cleanup_tasks.*': {'queue': 'cleanup'},
    },
)

# Scheduled tasks (Beat schedule)
celery_app.conf.beat_schedule = {
    # Daily tasks
    'send-overdue-reminders-daily': {
        'task': 'app.tasks.email_tasks.send_overdue_reminders',
        'schedule': crontab(hour=9, minute=0),  # 9:00 AM daily
        'args': (),
        'options': {'queue': 'email'},
    },
    'update-overdue-status-daily': {
        'task': 'app.tasks.background_tasks.update_overdue_borrowings',
        'schedule': crontab(hour=0, minute=0),  # Midnight daily
        'args': (),
        'options': {'queue': 'cleanup'},
    },
    'cleanup-old-sessions-daily': {
        'task': 'app.tasks.cleanup_tasks.cleanup_old_sessions',
        'schedule': crontab(hour=2, minute=0),  # 2:00 AM daily
        'args': (),
        'options': {'queue': 'cleanup'},
    },
    
    # Weekly tasks
    'send-weekly-report': {
        'task': 'app.tasks.email_tasks.send_weekly_report',
        'schedule': crontab(day_of_week=0, hour=10, minute=0),  # Sunday 10:00 AM
        'args': (),
        'options': {'queue': 'email'},
    },
    
    # Monthly tasks
    'generate-monthly-statistics': {
        'task': 'app.tasks.background_tasks.generate_monthly_statistics',
        'schedule': crontab(day_of_month=1, hour=0, minute=0),  # 1st of month
        'args': (),
        'options': {'queue': 'reports'},
    },
    
    # Hourly tasks
    'check-system-health-hourly': {
        'task': 'app.tasks.background_tasks.check_system_health',
        'schedule': crontab(minute=0),  # Every hour
        'args': (),
        'options': {'queue': 'cleanup'},
    },
    
    # Every 5 minutes
    'process-pending-emails': {
        'task': 'app.tasks.email_tasks.process_pending_emails',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
        'args': (),
        'options': {'queue': 'email'},
    },
}

# Task error handling
celery_app.conf.task_annotations = {
    '*': {
        'rate_limit': '10/m',  # 10 tasks per minute per worker
    }
}

# Retry configuration
celery_app.conf.task_default_retry_delay = 30  # 30 seconds
celery_app.conf.task_max_retries = 3

if __name__ == '__main__':
    celery_app.start()