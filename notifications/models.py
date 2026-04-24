import uuid
from django.db import models
from django.utils import timezone

from users.models import User
from core.models import TimeStampedModel


class Notification(TimeStampedModel):
    """
    In-app notification model.
    Stores notifications for users with support for different types.
    """
    NOTIFICATION_TYPES = (
        # --- Customer-facing ---
        ("BOOKING_CONFIRMED", "Booking Confirmed"),
        ("FAV_DEAL", "Favorite Restaurant Deal"),
        ("DEAL_REDEEMED", "Deal Redeemed"),
        ("SYSTEM", "System"),
        # --- Merchant-facing ---
        ("NEW_BOOKING", "New Booking Request"),
        ("BOOKING_CANCELLED", "Booking Cancelled"),
        ("MERCHANT_DEAL_REDEEMED", "Deal Redeemed at Your Restaurant"),
        ("MILESTONE_EARNINGS", "Earnings Milestone Reached"),
        ("NEW_REVIEW", "New Customer Review"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")

    title = models.CharField(max_length=255)
    message = models.TextField()

    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)

    is_read = models.BooleanField(default=False, db_index=True)
    payload = models.JSONField(blank=True, null=True)

    source_id = models.UUIDField(blank=True, null=True)
    source_type = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["notification_type"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.title}"


class DeviceToken(TimeStampedModel):
    """
    Stores FCM device tokens for push notifications.
    A user can have multiple devices.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="device_tokens")
    token = models.CharField(max_length=255, unique=True, db_index=True)
    device_type = models.CharField(
        max_length=20,
        choices=[
            ("android", "Android"),
            ("ios", "iOS"),
            ("web", "Web"),
        ],
        default="android"
    )
    device_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["device_id"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.device_type} ({self.token[:20]}...)"
