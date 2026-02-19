"""
Celery configuration for Discount Buddy project.

This module configures Celery for async task processing,
primarily used for sending push notifications.

To run Celery worker:
    celery -A discount_buddy worker --loglevel=info

To run Celery beat (for scheduled tasks):
    celery -A discount_buddy beat --loglevel=info

For development, you can run both together:
    celery -A discount_buddy worker --beat --loglevel=info
"""
import os
from celery import Celery

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'discount_buddy.settings')

# Create Celery app
app = Celery('discount_buddy')

# Load configuration from Django settings
# - namespace='CELERY' means all celery-related config keys should have a `CELERY_` prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery setup"""
    print(f'Request: {self.request!r}')
