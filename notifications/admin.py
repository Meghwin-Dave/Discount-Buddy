"""
Django admin configuration for notifications app
"""
from django.contrib import admin
from .models import Notification, DeviceToken


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin interface for Notification model"""
    list_display = [
        "id",
        "user",
        "title",
        "notification_type",
        "is_read",
        "created_at",
    ]
    list_filter = [
        "notification_type",
        "is_read",
        "created_at",
    ]
    search_fields = [
        "user__email",
        "user__username",
        "title",
        "message",
    ]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]
    
    fieldsets = (
        ("User", {
            "fields": ("user",)
        }),
        ("Content", {
            "fields": ("title", "message", "notification_type")
        }),
        ("Metadata", {
            "fields": ("payload", "source_id", "source_type")
        }),
        ("Status", {
            "fields": ("is_read",)
        }),
        ("Timestamps", {
            "fields": ("id", "created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    """Admin interface for DeviceToken model"""
    list_display = [
        "id",
        "user",
        "device_type",
        "token_preview",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "device_type",
        "is_active",
        "created_at",
    ]
    search_fields = [
        "user__email",
        "user__username",
        "token",
    ]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]
    
    def token_preview(self, obj):
        """Show first 30 characters of token"""
        return f"{obj.token[:30]}..." if len(obj.token) > 30 else obj.token
    token_preview.short_description = "Token Preview"
