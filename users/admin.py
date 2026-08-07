from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .merchant_utils import ensure_merchant_account
from .models import User, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0
    fields = ("role", "phone_number", "marketing_opt_in")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model"""
    inlines = (UserProfileInline,)
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

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.is_merchant:
            ensure_merchant_account(obj)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin configuration for UserProfile model"""
    list_display = ("user", "role", "phone_number", "marketing_opt_in")
    list_filter = ("role", "marketing_opt_in")
    search_fields = ("user__email", "user__username", "phone_number")
    raw_id_fields = ("user",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.role == UserProfile.ROLE_MERCHANT:
            ensure_merchant_account(obj.user)
