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

    # ------------------------------------------------------------------ #
    # Merchant-facing notifications
    # ------------------------------------------------------------------ #

    @staticmethod
    def _get_restaurant_owners(restaurant) -> list:
        """
        Return a list of User objects who are owners / managers of the given
        restaurant.  Checks both the RestaurantProfile (owner_profile) and the
        linked vouchers.Merchant user.
        """
        owners = []
        try:
            if hasattr(restaurant, "owner_profile") and restaurant.owner_profile:
                owners.append(restaurant.owner_profile.user)
        except Exception:
            pass

        try:
            if restaurant.merchant and restaurant.merchant.user:
                merchant_user = restaurant.merchant.user
                if merchant_user not in owners:
                    owners.append(merchant_user)
        except Exception:
            pass

        return owners

    @staticmethod
    def notify_merchant_new_booking(booking) -> int:
        """
        Notify restaurant owner(s) when a customer makes a new booking request.

        Args:
            booking: Booking instance (status PENDING)

        Returns:
            Number of notifications created
        """
        restaurant = booking.restaurant
        owners = NotificationService._get_restaurant_owners(restaurant)

        if not owners:
            return 0

        # Ensure booking_date is formatted safely
        try:
            if isinstance(booking.booking_date, str):
                from django.utils.dateparse import parse_datetime
                dt_obj = parse_datetime(booking.booking_date)
                booking_date_str = dt_obj.strftime('%B %d, %Y at %I:%M %p') if dt_obj else booking.booking_date
            else:
                booking_date_str = booking.booking_date.strftime('%B %d, %Y at %I:%M %p')
        except Exception:
            booking_date_str = str(booking.booking_date)

        title = "New Table Booking Request 📅"
        message = (
            f"{booking.contact_name or booking.user.get_full_name() or booking.user.email} "
            f"has requested a table for {booking.number_of_guests} guest(s) "
            f"at {restaurant.name} on "
            f"{booking_date_str}."
        )

        payload = {
            "booking_id": str(booking.id),
            "restaurant_id": str(restaurant.id),
            "customer_name": booking.contact_name or booking.user.get_full_name() or booking.user.email,
            "number_of_guests": booking.number_of_guests,
            "booking_date": booking_date_str,
        }

        count = 0
        for owner in owners:
            NotificationService.create_notification(
                user=owner,
                title=title,
                message=message,
                notification_type="NEW_BOOKING",
                payload=payload,
                source_id=booking.id,
                source_type="booking",
            )
            count += 1

        return count

    @staticmethod
    def notify_merchant_deal_redeemed(deal_use) -> int:
        """
        Notify restaurant owner(s) when a customer successfully redeems a deal
        at their restaurant.

        Args:
            deal_use: DealUse instance after is_redeemed is set to True

        Returns:
            Number of notifications created
        """
        restaurant = deal_use.deal.restaurant
        owners = NotificationService._get_restaurant_owners(restaurant)

        if not owners:
            return 0

        customer_name = (
            deal_use.user.get_full_name() or deal_use.user.username or deal_use.user.email
        )

        title = "Deal Redeemed at Your Restaurant 🎉"
        message = (
            f"{customer_name} just redeemed \"{deal_use.deal.title}\" at {restaurant.name}."
        )

        payload = {
            "deal_use_id": str(deal_use.id),
            "deal_id": str(deal_use.deal.id),
            "restaurant_id": str(restaurant.id),
            "customer_name": customer_name,
            "redemption_code": deal_use.redemption_code,
        }

        count = 0
        for owner in owners:
            NotificationService.create_notification(
                user=owner,
                title=title,
                message=message,
                notification_type="MERCHANT_DEAL_REDEEMED",
                payload=payload,
                source_id=deal_use.id,
                source_type="deal_use",
            )
            count += 1

        return count

    @staticmethod
    def notify_merchant_milestone(restaurant, milestone_amount: float) -> int:
        """
        Send a milestone congratulations notification to restaurant owner(s) when
        cumulative earnings via the app cross a threshold.

        Args:
            restaurant: Restaurant instance
            milestone_amount: The milestone value crossed (e.g. 100, 500, 1000)

        Returns:
            Number of notifications created
        """
        owners = NotificationService._get_restaurant_owners(restaurant)

        if not owners:
            return 0

        title = f"Milestone Reached – £{int(milestone_amount):,} Earned! 🏆"
        message = (
            f"Congratulations! Your restaurant {restaurant.name} has crossed "
            f"£{int(milestone_amount):,} in total customer savings/earnings through "
            f"Discount Buddy. Keep it up!"
        )

        payload = {
            "restaurant_id": str(restaurant.id),
            "milestone_amount": milestone_amount,
        }

        count = 0
        for owner in owners:
            NotificationService.create_notification(
                user=owner,
                title=title,
                message=message,
                notification_type="MILESTONE_EARNINGS",
                payload=payload,
                source_id=restaurant.id,
                source_type="restaurant",
            )
            count += 1

        return count

    @staticmethod
    def notify_merchant_new_review(review) -> int:
        """
        Notify restaurant owner(s) when a customer posts a new review.

        Args:
            review: Review instance

        Returns:
            Number of notifications created
        """
        restaurant = review.restaurant
        owners = NotificationService._get_restaurant_owners(restaurant)

        if not owners:
            return 0

        customer_name = (
            review.user.get_full_name() or review.user.username or review.user.email
        )
        stars = "⭐" * review.rating

        title = "New Customer Review Posted ✍️"
        message = (
            f"{customer_name} left a {review.rating}-star review for {restaurant.name}. "
            f"{stars}"
        )
        if review.comment:
            # Include a snippet of the comment (max 80 chars)
            snippet = review.comment[:80] + ("…" if len(review.comment) > 80 else "")
            message += f'\n"{snippet}"'

        payload = {
            "review_id": str(review.id),
            "restaurant_id": str(restaurant.id),
            "customer_name": customer_name,
            "rating": review.rating,
        }

        count = 0
        for owner in owners:
            NotificationService.create_notification(
                user=owner,
                title=title,
                message=message,
                notification_type="NEW_REVIEW",
                payload=payload,
                source_id=review.id,
                source_type="review",
            )
            count += 1

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
