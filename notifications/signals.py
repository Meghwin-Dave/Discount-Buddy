"""
Django signals for automatic notification triggers.

These signals listen to model changes and automatically create notifications
when certain events occur (booking confirmed, deal created, deal redeemed).
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db import transaction

import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender='restaurants.Booking')
def notify_booking_confirmed(sender, instance, created, **kwargs):
    """
    Send notification when booking status changes to CONFIRMED.
    
    Triggered by: Booking model save
    Notification type: BOOKING_CONFIRMED
    """
    from restaurants.models import Booking
    from .services import NotificationService
    
    # Only send notification when status changes to CONFIRMED
    # We need to check if this is a status change, not initial creation
    if instance.status == Booking.STATUS_CONFIRMED:
        # Check if we've already sent a notification for this booking
        # by checking if a notification with this source_id exists
        from .models import Notification
        
        already_notified = Notification.objects.filter(
            source_id=instance.id,
            source_type='booking',
            notification_type='BOOKING_CONFIRMED'
        ).exists()
        
        if not already_notified:
            try:
                NotificationService.send_booking_confirmed(
                    user=instance.user,
                    booking=instance
                )
                logger.info(f"Sent booking confirmation notification for booking {instance.id}")
            except Exception as e:
                logger.error(f"Failed to send booking notification: {str(e)}")


@receiver(post_save, sender='restaurants.Deal')
def notify_favorite_restaurant_deal(sender, instance, created, **kwargs):
    """
    Notify users who favorited a restaurant when a new deal is created.
    
    Triggered by: Deal model creation
    Notification type: FAV_DEAL
    """
    from .services import NotificationService
    
    # Only send notifications for newly created deals
    if created and instance.is_active:
        # Use transaction.on_commit to ensure the deal is saved before sending notifications
        def send_notifications():
            try:
                count = NotificationService.notify_favorite_deal(
                    restaurant=instance.restaurant,
                    deal=instance
                )
                logger.info(
                    f"Sent {count} favorite deal notifications for deal {instance.id}"
                )
            except Exception as e:
                logger.error(f"Failed to send favorite deal notifications: {str(e)}")
        
        transaction.on_commit(send_notifications)


@receiver(post_save, sender='restaurants.DealUse')
def notify_deal_redeemed(sender, instance, created, **kwargs):
    """
    Send notification when a deal is successfully redeemed.
    
    Triggered by: DealUse model save when is_redeemed changes to True
    Notification type: DEAL_REDEEMED
    """
    from .services import NotificationService
    
    # Only send notification when deal is marked as redeemed
    if instance.is_redeemed:
        # Check if we've already sent a notification for this redemption
        from .models import Notification
        
        already_notified = Notification.objects.filter(
            source_id=instance.deal.id,
            source_type='deal',
            notification_type='DEAL_REDEEMED',
            user=instance.user
        ).exists()
        
        if not already_notified:
            try:
                NotificationService.send_deal_redeemed(
                    user=instance.user,
                    deal=instance.deal,
                    restaurant=instance.deal.restaurant
                )
                logger.info(
                    f"Sent deal redeemed notification for deal {instance.deal.id} "
                    f"to user {instance.user.email}"
                )
            except Exception as e:
                logger.error(f"Failed to send deal redeemed notification: {str(e)}")
