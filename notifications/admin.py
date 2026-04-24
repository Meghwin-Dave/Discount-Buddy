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

    def save_model(self, request, obj, form, change):
        """
        Override save_model to trigger push notification when created via Admin.
        """
        super().save_model(request, obj, form, change)
        
        # Only send push notification for new objects (not updates)
        if not change:
            try:
                from .tasks import send_push_notification
                # Use delay() if Celery is running, otherwise call directly if configured differently
                # But here we stick to the pattern in services.py
                send_push_notification.delay(str(obj.id))
                print(f"✅ [Admin] Triggered push notification for {obj.id}")
            except ImportError:
                print("⚠️ [Admin] Could not import tasks, skipping push")
            except AttributeError as e:
                print(f"⚠️ [Admin] Task does not support .delay() (Celery missing?): {e}")
                # Fallback: try calling directly if .delay fails
                try:
                    send_push_notification(str(obj.id))
                    print(f"✅ [Admin] Validated synchronous fallback for {obj.id}")
                except Exception as inner_e:
                     print(f"❌ [Admin] Synchronous fallback failed: {inner_e}")
            except Exception as e:
                print(f"❌ [Admin] Failed to trigger push: {e}")


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    """Admin interface for DeviceToken model"""
    list_display = [
        "id",
        "user",
        "device_type",
        "device_id",
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
        "device_id",
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
