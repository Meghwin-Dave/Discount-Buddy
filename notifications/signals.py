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


@receiver(post_save, sender='restaurants.Booking')
def notify_merchant_new_booking(sender, instance, created, **kwargs):
    """
    Notify merchant / restaurant owner when a NEW booking request is made.

    Triggered by: Booking model creation (created=True)
    Notification type: NEW_BOOKING
    """
    from .services import NotificationService

    if not created:
        return  # only fire on brand-new bookings

    def send_notifications():
        try:
            count = NotificationService.notify_merchant_new_booking(booking=instance)
            logger.info(
                f"Sent {count} merchant new-booking notification(s) for booking {instance.id}"
            )
        except Exception as e:
            logger.error(f"Failed to send merchant new-booking notification: {str(e)}")

    transaction.on_commit(send_notifications)


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
    Notification type: DEAL_REDEEMED  (customer)
                       MERCHANT_DEAL_REDEEMED  (merchant / owner)
    """
    from .services import NotificationService

    # Only send notification when deal is marked as redeemed
    if instance.is_redeemed:
        from .models import Notification

        # ── Customer notification ──────────────────────────────────────────
        already_notified_customer = Notification.objects.filter(
            source_id=instance.deal.id,
            source_type='deal',
            notification_type='DEAL_REDEEMED',
            user=instance.user
        ).exists()

        if not already_notified_customer:
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

        # ── Merchant notification ──────────────────────────────────────────
        already_notified_merchant = Notification.objects.filter(
            source_id=instance.id,
            source_type='deal_use',
            notification_type='MERCHANT_DEAL_REDEEMED',
        ).exists()

        if not already_notified_merchant:
            try:
                count = NotificationService.notify_merchant_deal_redeemed(deal_use=instance)
                logger.info(
                    f"Sent {count} merchant deal-redeemed notification(s) for deal_use {instance.id}"
                )

                # ── Check for earnings milestones after each redemption ────
                _check_merchant_earnings_milestone(instance.deal.restaurant)

            except Exception as e:
                logger.error(f"Failed to send merchant deal-redeemed notification: {str(e)}")


def _check_merchant_earnings_milestone(restaurant):
    """
    Calculate the restaurant's total earnings through the app and fire a
    milestone notification if a threshold is crossed for the first time.

    Milestones (£): 100, 500, 1000, 5000, 10000, 50000
    """
    from restaurants.models import DealUse
    from .services import NotificationService
    from .models import Notification
    from django.db.models import Sum

    MILESTONES = [100, 500, 1000, 5000, 10_000, 50_000]

    try:
        total = DealUse.objects.filter(
            deal__restaurant=restaurant,
            is_redeemed=True,
            final_bill_amount__isnull=False,
        ).aggregate(total=Sum("final_bill_amount"))["total"] or 0

        total = float(total)

        for milestone in MILESTONES:
            if total >= milestone:
                already_sent = Notification.objects.filter(
                    source_type="restaurant",
                    source_id=restaurant.id,
                    notification_type="MILESTONE_EARNINGS",
                    payload__milestone_amount=milestone,
                ).exists()

                if not already_sent:
                    NotificationService.notify_merchant_milestone(
                        restaurant=restaurant,
                        milestone_amount=milestone,
                    )
                    logger.info(
                        f"Sent £{milestone} milestone notification for restaurant {restaurant.id}"
                    )
    except Exception as e:
        logger.error(f"Failed to check/send milestone notification: {str(e)}")


@receiver(post_save, sender='restaurants.Review')
def notify_merchant_new_review(sender, instance, created, **kwargs):
    """
    Notify restaurant owner(s) when a customer posts a new review.

    Triggered by: Review model creation
    Notification type: NEW_REVIEW
    """
    from .services import NotificationService

    if not created:
        return  # only fire on brand-new reviews

    def send_notifications():
        try:
            count = NotificationService.notify_merchant_new_review(review=instance)
            logger.info(
                f"Sent {count} merchant new-review notification(s) for review {instance.id}"
            )
        except Exception as e:
            logger.error(f"Failed to send merchant new-review notification: {str(e)}")

    transaction.on_commit(send_notifications)
