from django.db import models
import uuid
from django.conf import settings
from django.utils import timezone
from core.models import TimeStampedModel, SoftDeleteModel

class AppConfig(TimeStampedModel, SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    config_key = models.CharField(max_length=100, db_index=True)
    config_value = models.TextField()
    config_type = models.CharField(max_length=50, default='string')
    platform = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_configs'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='updated_configs'
    )

    class Meta:
        db_table = 'app_configs'
        verbose_name = 'App Configuration'
        verbose_name_plural = 'App Configurations'
        unique_together = ('config_key', 'platform')

    def __str__(self):
        return f"{self.config_key} ({self.platform or 'All'})"

class AppConfigKeys:
    MOBILE_APP_MINIMUM_VERSION_ANDROID = "MobileApp.MinimumVersion.Android"
    MOBILE_APP_MINIMUM_VERSION_IOS = "MobileApp.MinimumVersion.iOS"
    MOBILE_APP_LATEST_VERSION_ANDROID = "MobileApp.LatestVersion.Android"
    MOBILE_APP_LATEST_VERSION_IOS = "MobileApp.LatestVersion.iOS"
    MOBILE_APP_UPDATE_MESSAGE = "MobileApp.UpdateMessage"
    MOBILE_APP_STORE_URL_ANDROID = "MobileApp.StoreUrl.Android"
    MOBILE_APP_STORE_URL_IOS = "MobileApp.StoreUrl.iOS"
    MOBILE_APP_FORCE_UPDATE_THRESHOLD_ANDROID = "MobileApp.ForceUpdateThreshold.Android"
    MOBILE_APP_FORCE_UPDATE_THRESHOLD_IOS = "MobileApp.ForceUpdateThreshold.iOS"
    MOBILE_APP_CRITICAL_VERSION_ANDROID = "MobileApp.CriticalVersion.Android"
    MOBILE_APP_CRITICAL_VERSION_IOS = "MobileApp.CriticalVersion.iOS"
    MOBILE_APP_OPTIONAL_UPDATE_THRESHOLD_ANDROID = "MobileApp.OptionalUpdateThreshold.Android"
    MOBILE_APP_OPTIONAL_UPDATE_THRESHOLD_IOS = "MobileApp.OptionalUpdateThreshold.iOS"

class AppPlatforms:
    ANDROID = "android"
    IOS = "ios"


class SpinToWinCampaign(TimeStampedModel):
    """Spin to Win Campaign Configuration"""
    title = models.CharField(max_length=255, default="Spin & Win Rewards")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    max_spins_per_user_per_day = models.PositiveIntegerField(default=1)
    total_spins_count = models.PositiveIntegerField(default=0, help_text="Total spins count conducted across all users")

    class Meta:
        db_table = "spin_to_win_campaigns"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({'Active' if self.is_active else 'Inactive'})"


class SpinToWinItem(TimeStampedModel):
    """Wheel slice item configuration for Spin to Win"""
    ITEM_PROMOCODE = "promocode"
    ITEM_DISCOUNT = "discount"
    ITEM_EMPTY = "empty"
    ITEM_POINTS = "points"

    ITEM_TYPE_CHOICES = [
        (ITEM_PROMOCODE, "Promo Code"),
        (ITEM_DISCOUNT, "Discount"),
        (ITEM_EMPTY, "Try Again"),
        (ITEM_POINTS, "Reward Points"),
    ]

    campaign = models.ForeignKey(SpinToWinCampaign, on_delete=models.CASCADE, related_name="items")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon name or emoji")
    image = models.ImageField(upload_to="spin_items/%Y/%m/%d/", null=True, blank=True)
    item_type = models.CharField(max_length=30, choices=ITEM_TYPE_CHOICES, default=ITEM_PROMOCODE)
    promo_code_value = models.TextField(
        blank=True,
        help_text="Text message / Promo code text awarded for this item (e.g. 'Use code SAVE50 at checkout')"
    )
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    min_spins_before_win = models.PositiveIntegerField(
        default=0,
        help_text="Minimum total campaign spins required before giving away this item"
    )
    stock_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Max times this prize can be given away across all users. Null = unlimited"
    )
    times_won = models.PositiveIntegerField(default=0)
    probability_weight = models.PositiveIntegerField(default=1, help_text="Relative selection weight")
    slice_index = models.PositiveIntegerField(default=0, help_text="Wheel position index")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "spin_to_win_items"
        ordering = ["slice_index", "id"]

    def __str__(self):
        return f"{self.title} (Slice {self.slice_index})"


class UserSpinResult(TimeStampedModel):
    """Log of user spins and prizes/promocodes won"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="spin_results")
    campaign = models.ForeignKey(SpinToWinCampaign, on_delete=models.CASCADE, related_name="user_spin_results")
    item = models.ForeignKey(SpinToWinItem, on_delete=models.SET_NULL, null=True, related_name="win_records")
    is_win = models.BooleanField(default=False)
    promo_code = models.TextField(blank=True, help_text="Promo code / text message received by the user")
    spun_at = models.DateTimeField(default=timezone.now, db_index=True)
    claimed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "user_spin_results"
        ordering = ["-spun_at"]

    def __str__(self):
        return f"{self.user.email} - {self.item.title if self.item else 'No Item'} at {self.spun_at}"

