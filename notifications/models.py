import uuid
from django.db import models
from django.utils import timezone

from users.models import User
from core.models import TimeStampedModel
from core.mixins import ProcessedImageMixin


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
        ("BOOKING_REMINDER", "Upcoming Booking Reminder"),
        ("PROMO", "Admin Promotion"),
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


class AdminNotificationCampaign(ProcessedImageMixin, TimeStampedModel):
    """One admin-composed promo send (image stored once, not per recipient)."""

    AUDIENCE_ALL_CUSTOMERS = "all_customers"
    AUDIENCE_RESTAURANT_FAVOURITES = "restaurant_favourites"
    AUDIENCE_CHOICES = [
        (AUDIENCE_ALL_CUSTOMERS, "All customers"),
        (AUDIENCE_RESTAURANT_FAVOURITES, "Restaurant favourites"),
    ]

    STATUS_QUEUED = "queued"
    STATUS_SCHEDULED = "scheduled"
    STATUS_SENDING = "sending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_SENDING, "Sending"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="admin_notification_campaigns"
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    image = models.ImageField(upload_to="notification_campaigns/%Y/%m/%d/", null=True, blank=True)
    audience = models.CharField(max_length=40, choices=AUDIENCE_CHOICES, default=AUDIENCE_ALL_CUSTOMERS)
    restaurant = models.ForeignKey(
        "restaurants.Restaurant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_notification_campaigns",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True)
    scheduled_at = models.DateTimeField(null=True, blank=True, db_index=True)
    fcm_image_url = models.CharField(max_length=500, blank=True)
    recipient_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "admin_notification_campaigns"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.audience})"
