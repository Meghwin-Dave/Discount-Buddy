from django.contrib import admin
from .models import Wallet, WalletTransaction


class WalletTransactionInline(admin.TabularInline):
    """Inline admin for wallet transactions"""
    model = WalletTransaction
    extra = 0
    readonly_fields = ("created_at", "updated_at")
    fields = ("amount", "transaction_type", "reason", "created_at")
    can_delete = False


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    """Admin configuration for Wallet model"""
    list_display = ("user", "balance", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("user__email", "user__username")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("user",)
    inlines = [WalletTransactionInline]
    
    fieldsets = (
        ("Wallet Information", {
            "fields": ("user", "balance")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    """Admin configuration for WalletTransaction model"""
    list_display = ("wallet", "amount", "transaction_type", "reason", "created_at")
    list_filter = ("transaction_type", "created_at")
    search_fields = ("wallet__user__email", "wallet__user__username", "reason")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("wallet",)
    date_hierarchy = "created_at"
    
    fieldsets = (
        ("Transaction Information", {
            "fields": ("wallet", "amount", "transaction_type", "reason")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

