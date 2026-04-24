"""
Celery tasks for sending push notifications.

NOTE: This requires:
1. Celery to be configured in your Django project
2. Redis as the message broker
3. Firebase Admin SDK credentials

To configure Firebase:
1. Download your Firebase service account JSON file
2. Set FIREBASE_CREDENTIALS_PATH in settings.py
3. Or set FIREBASE_CREDENTIALS as environment variable with JSON content
"""
from typing import List
import logging

logger = logging.getLogger(__name__)

# Celery task decorator - will be imported when Celery is configured
try:
    from celery import shared_task
except ImportError:
    # Celery not installed, create a dummy decorator
    # Celery not installed, create a dummy decorator
    def shared_task(func):
        """Dummy decorator when Celery is not available"""
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Add .delay() method to run synchronously
        def delay(*args, **kwargs):
            print(f"⚠️ [Task] Celery not installed, running {func.__name__} synchronously")
            return func(*args, **kwargs)
            
        wrapper.delay = delay
        return wrapper


@shared_task
def send_push_notification(notification_id: str):
    """
    Send push notification to all user's devices.
    
    Args:
        notification_id: UUID of the notification to send
    """
    try:
        from .models import Notification
        from .fcm import send_fcm_message
        
        notification = Notification.objects.get(id=notification_id)
        device_tokens = notification.user.device_tokens.filter(is_active=True)
        
        if not device_tokens.exists():
            logger.info(f"No active device tokens for user {notification.user.email}")
            return
        
        success_count = 0
        error_count = 0
        
        for device_token in device_tokens:
            try:
                sent, error = send_fcm_message(
                    token=device_token.token,
                    title=notification.title,
                    body=notification.message,
                    data=notification.payload or {}
                )
                
                if sent:
                    success_count += 1
                    print(f"✅ [Task] Push sent to {device_token.user.email} ({device_token.device_type})")
                else:
                    error_count += 1
                    error_msg = str(error) if error else "Unknown error"
                    print(f"❌ [Task] Push FAILED for {device_token.user.email}: {error_msg}")
                    
                    # If token is invalid/unregistered, deactivate it
                    if error:
                        from firebase_admin import messaging
                        # These errors indicate the token is no longer valid
                        is_stale = isinstance(error, (messaging.UnregisteredError, messaging.SenderIdMismatchError))
                        
                        # Also check by code string if the class check fails or for other specific cases
                        error_code = getattr(error, 'code', None)
                        if not is_stale and error_code in ['registration-token-not-registered', 'invalid-argument']:
                            is_stale = True
                            
                        if is_stale:
                            device_token.is_active = False
                            device_token.save(update_fields=["is_active", "updated_at"])
                            print(f"⚠️ [Task] Deactivated stale token for {device_token.user.email}")
                            logger.info(f"Deactivated stale token for user {device_token.user.email}")

            except Exception as e:
                error_count += 1
                logger.error(
                    f"Failed to handle push for token {device_token.token[:20]}...: {str(e)}"
                )
                print(f"❌ [Task] Unexpected error for {device_token.user.email}: {e}")
        
        logger.info(
            f"Push notification sent for notification {notification_id}: "
            f"{success_count} success, {error_count} errors"
        )
        
    except Exception as e:
        logger.error(f"Error sending push notification {notification_id}: {str(e)}")
        # Re-raise to trigger Celery retry
        raise


@shared_task
def send_bulk_push_notifications(notification_ids: List[str]):
    """
    Send push notifications in bulk (for favorite deal notifications).
    Processes notifications in chunks to avoid overwhelming FCM.
    
    Args:
        notification_ids: List of notification UUIDs to send
    """
    try:
        from .models import Notification
        from .fcm import send_fcm_message
        
        notifications = Notification.objects.filter(
            id__in=notification_ids
        ).select_related("user").prefetch_related("user__device_tokens")
        
        total_sent = 0
        total_errors = 0
        
        for notification in notifications:
            device_tokens = notification.user.device_tokens.filter(is_active=True)
            
            for device_token in device_tokens:
                try:
                    sent, error = send_fcm_message(
                        token=device_token.token,
                        title=notification.title,
                        body=notification.message,
                        data=notification.payload or {}
                    )
                    
                    if sent:
                        total_sent += 1
                    elif error:
                        total_errors += 1
                        # Deactivate stale tokens in bulk flow too
                        from firebase_admin import messaging
                        if isinstance(error, (messaging.UnregisteredError, messaging.SenderIdMismatchError)):
                            device_token.is_active = False
                            device_token.save(update_fields=["is_active", "updated_at"])
                            logger.info(f"Deactivated stale token in bulk flow for {device_token.user.email}")
                except Exception as e:
                    total_errors += 1
                    logger.error(
                        f"Failed to send bulk push to token {device_token.token[:20]}...: {str(e)}"
                    )
        
        logger.info(
            f"Bulk push notifications sent: {total_sent} success, {total_errors} errors"
        )
        
    except Exception as e:
        logger.error(f"Error sending bulk push notifications: {str(e)}")
        # Re-raise to trigger Celery retry
        raise
