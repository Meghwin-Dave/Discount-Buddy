from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, UserProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model"""
    list_display = ("email", "username", "is_merchant", "is_customer", "is_staff", "is_active", "date_joined")
    list_filter = ("is_merchant", "is_customer", "is_staff", "is_active", "is_superuser", "date_joined")
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("-date_joined",)
    
    fieldsets = (
        (None, {"fields": ("email", "username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_merchant",
                    "is_customer",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "username", "password1", "password2", "is_merchant", "is_customer"),
            },
        ),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin configuration for UserProfile model"""
    list_display = ("user", "role", "phone_number", "marketing_opt_in")
    list_filter = ("role", "marketing_opt_in")
    search_fields = ("user__email", "user__username", "phone_number")
    raw_id_fields = ("user",)


