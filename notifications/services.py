"""
Notification Service Layer
Handles business logic for creating and sending notifications.
"""
from typing import Optional, Dict, Any
from django.db import transaction
from django.utils import timezone

from .models import Notification, DeviceToken
from users.models import User


class NotificationService:
    """
    Service class for handling notification creation and delivery.
    Separates business logic from API views.
    """

    @staticmethod
    def create_notification(
        user: User,
        title: str,
        message: str,
        notification_type: str,
        payload: Optional[Dict[str, Any]] = None,
        source_id: Optional[str] = None,
        source_type: Optional[str] = None,
        send_push: bool = True,
    ) -> Notification:
        """
        Create a notification and optionally trigger push notification.
        
        Args:
            user: User to notify
            title: Notification title
            message: Notification message
            notification_type: Type of notification (must match NOTIFICATION_TYPES)
            payload: Optional JSON payload with additional data
            source_id: Optional UUID of the source object (e.g., booking_id, deal_id)
            source_type: Optional type of source object (e.g., "booking", "deal")
            send_push: Whether to send push notification (default: True)
        
        Returns:
            Created Notification instance
        """
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type,
            payload=payload or {},
            source_id=source_id,
            source_type=source_type,
        )

        # Trigger async push notification if enabled
        if send_push:
            # Import here to avoid circular imports and allow Celery to be optional
            try:
                from .tasks import send_push_notification
                send_push_notification.delay(str(notification.id))
            except ImportError:
                # Celery not configured, skip push notification
                pass

        return notification

    @staticmethod
    def send_booking_confirmed(user: User, booking) -> Notification:
        """
        Send notification when booking is confirmed.
        
        Args:
            user: User who made the booking
            booking: Booking instance
        
        Returns:
            Created Notification instance
        """
        from restaurants.models import Booking  # Import here to avoid circular imports
        
        title = "Booking Confirmed 🎉"
        message = (
            f"Your table at {booking.restaurant.name} has been confirmed "
            f"for {booking.booking_date.strftime('%B %d, %Y at %I:%M %p')}."
        )
        
        payload = {
            "booking_id": str(booking.id),
            "restaurant_id": str(booking.restaurant.id),
            "booking_date": booking.booking_date.isoformat(),
        }
        
        return NotificationService.create_notification(
            user=user,
            title=title,
            message=message,
            notification_type="BOOKING_CONFIRMED",
            payload=payload,
            source_id=booking.id,
            source_type="booking",
        )

    @staticmethod
    def notify_favorite_deal(restaurant, deal) -> int:
        """
        Notify all users who favorited a restaurant about a new deal.
        Uses bulk_create for performance.
        
        Args:
            restaurant: Restaurant instance
            deal: Deal instance
        
        Returns:
            Number of notifications created
        """
        from restaurants.models import SavedRestaurant  # Import here to avoid circular imports
        
        # Get all users who favorited this restaurant
        favorited_users = User.objects.filter(
            saved_restaurants__restaurant=restaurant
        ).distinct()
        
        if not favorited_users.exists():
            return 0
        
        title = "New Deal Available 🔥"
        message = f"{restaurant.name} has launched a new offer: {deal.title}. Check it out!"
        
        payload = {
            "restaurant_id": str(restaurant.id),
            "deal_id": str(deal.id),
        }
        
        # Bulk create notifications for performance
        notifications = []
        for user in favorited_users:
            notifications.append(
                Notification(
                    user=user,
                    title=title,
                    message=message,
                    notification_type="FAV_DEAL",
                    payload=payload,
                    source_id=deal.id,
                    source_type="deal",
                )
            )
        
        # Use bulk_create for better performance
        created_notifications = Notification.objects.bulk_create(notifications)
        
        # Enqueue push notifications in chunks
        try:
            from .tasks import send_bulk_push_notifications
            notification_ids = [str(n.id) for n in created_notifications]
            send_bulk_push_notifications.delay(notification_ids)
        except ImportError:
            # Celery not configured, skip push notifications
            pass
        
        return len(created_notifications)

    @staticmethod
    def send_deal_redeemed(user: User, deal, restaurant) -> Notification:
        """
        Send notification when user successfully redeems a deal.
        
        Args:
            user: User who redeemed the deal
            deal: Deal instance
            restaurant: Restaurant instance
        
        Returns:
            Created Notification instance
        """
        title = "Deal Redeemed Successfully ✅"
        message = f"Enjoy your offer at {restaurant.name}. Bon appétit!"
        
        payload = {
            "deal_id": str(deal.id),
            "restaurant_id": str(restaurant.id),
        }
        
        return NotificationService.create_notification(
            user=user,
            title=title,
            message=message,
            notification_type="DEAL_REDEEMED",
            payload=payload,
            source_id=deal.id,
            source_type="deal",
        )

    @staticmethod
    def mark_as_read(notification_id: str, user: User) -> bool:
        """
        Mark a specific notification as read.
        
        Args:
            notification_id: UUID of the notification
            user: User who owns the notification
        
        Returns:
            True if successful, False otherwise
        """
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
            notification.is_read = True
            notification.save(update_fields=["is_read", "updated_at"])
            return True
        except Notification.DoesNotExist:
            return False

    @staticmethod
    def mark_all_as_read(user: User) -> int:
        """
        Mark all unread notifications as read for a user.
        
        Args:
            user: User whose notifications to mark as read
        
        Returns:
            Number of notifications marked as read
        """
        count = Notification.objects.filter(user=user, is_read=False).update(
            is_read=True,
            updated_at=timezone.now()
        )
        return count

    @staticmethod
    def get_unread_count(user: User) -> int:
        """
        Get count of unread notifications for a user.
        
        Args:
            user: User to get unread count for
        
        Returns:
            Number of unread notifications
        """
        return Notification.objects.filter(user=user, is_read=False).count()
