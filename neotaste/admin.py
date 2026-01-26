from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    NeoTasteUser, City, Category, Restaurant, Offer, Redemption, OTP
)


@admin.register(NeoTasteUser)
class NeoTasteUserAdmin(BaseUserAdmin):
    """Admin for NeoTasteUser"""
    list_display = ['mobile_number', 'is_active', 'selected_city', 'membership_status', 'created_at']
    list_filter = ['is_active', 'membership_status', 'created_at']
    search_fields = ['mobile_number']
    ordering = ['-created_at']
    filter_horizontal = []  # NeoTasteUser doesn't have groups or user_permissions
    
    fieldsets = (
        (None, {'fields': ('mobile_number', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Profile', {'fields': ('selected_city', 'membership_status')}),
        ('Important dates', {'fields': ('last_login', 'created_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('mobile_number', 'password1', 'password2'),
        }),
    )


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    """Admin for City"""
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    ordering = ['name']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin for Category"""
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    ordering = ['name']


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    """Admin for Restaurant"""
    list_display = ['name', 'city', 'is_active', 'is_featured', 'created_at']
    list_filter = ['is_active', 'is_featured', 'city', 'created_at']
    search_fields = ['name', 'address']
    filter_horizontal = ['categories']
    ordering = ['-is_featured', '-created_at']


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    """Admin for Offer"""
    list_display = ['title', 'restaurant', 'expiry_date', 'is_active', 'created_at']
    list_filter = ['is_active', 'expiry_date', 'created_at']
    search_fields = ['title', 'description', 'restaurant__name']
    ordering = ['-created_at']


@admin.register(Redemption)
class RedemptionAdmin(admin.ModelAdmin):
    """Admin for Redemption"""
    list_display = ['user', 'offer', 'status', 'redeemed_at']
    list_filter = ['status', 'redeemed_at']
    search_fields = ['user__mobile_number', 'offer__title']
    ordering = ['-redeemed_at']
    readonly_fields = ['redeemed_at', 'created_at']


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    """Admin for OTP"""
    list_display = ['mobile_number', 'is_verified', 'expires_at', 'created_at']
    list_filter = ['is_verified', 'created_at', 'expires_at']
    search_fields = ['mobile_number']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
