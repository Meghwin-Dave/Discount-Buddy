from django.contrib import admin
from .models import Merchant, Voucher, VoucherCategory, VoucherRedemption


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "verified", "created_at")
    search_fields = ("name", "user__email", "user__username")
    list_filter = ("verified", "created_at")
    raw_id_fields = ("user",)
    ordering = ("-created_at",)


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "merchant", "discount_percent", "start_date", "end_date", "remaining_quantity")
    search_fields = ("code", "title", "merchant__name", "description")
    list_filter = ("merchant", "start_date", "end_date", "created_at")
    raw_id_fields = ("merchant",)
    date_hierarchy = "start_date"
    fieldsets = (
        ("Basic Information", {
            "fields": ("code", "title", "description", "merchant", "category")
        }),
        ("Pricing", {
            "fields": ("discount_percent", "original_price", "sale_price")
        }),
        ("Validity", {
            "fields": ("start_date", "end_date")
        }),
        ("Quantity", {
            "fields": ("total_quantity", "sold_quantity", "max_per_user")
        }),
        ("Status", {
            "fields": ("is_active",)
        }),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(VoucherCategory)
class VoucherCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(VoucherRedemption)
class VoucherRedemptionAdmin(admin.ModelAdmin):
    list_display = ("voucher", "user", "redeemed_at", "is_successful", "created_at")
    search_fields = ("voucher__code", "user__email", "user__username")
    list_filter = ("is_successful", "redeemed_at", "created_at")
    raw_id_fields = ("voucher", "user")
    date_hierarchy = "redeemed_at"
    readonly_fields = ("created_at", "updated_at")
