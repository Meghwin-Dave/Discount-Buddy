from django.db import models
import uuid
from django.conf import settings
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
