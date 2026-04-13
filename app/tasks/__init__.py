"""
Celery tasks package for background jobs.
Covers: SCRUM-20, SCRUM-35
"""

from celery import Celery

# Create Celery app
celery_app = Celery('library_tasks')

# Import tasks
from . import email_tasks
from . import background_tasks
from . import cleanup_tasks

__all__ = ['celery_app', 'email_tasks', 'background_tasks', 'cleanup_tasks']