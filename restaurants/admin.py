from django.contrib import admin
from .models import (
    Country, City, RestaurantCategory, Restaurant, Deal,
    RestaurantImage, DealImage, SavedRestaurant, SavedDeal, DealUse
)


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "flag_emoji", "created_at")
    search_fields = ("name", "code")
    list_filter = ("created_at",)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "is_active", "created_at")
    search_fields = ("name", "country__name")
    list_filter = ("country", "is_active", "created_at")
    raw_id_fields = ("country",)


@admin.register(RestaurantCategory)
class RestaurantCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


class RestaurantImageInline(admin.TabularInline):
    model = RestaurantImage
    extra = 1
    fields = ("image", "alt_text", "is_primary", "order")


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = (
        "name", "city", "verified", "is_featured",
        "price_range", "created_at"
    )
    list_filter = ("verified", "is_featured", "city__country", "city", "created_at")
    search_fields = ("name", "address", "city__name", "description")
    raw_id_fields = ("merchant", "city")
    filter_horizontal = ("categories",)
    inlines = [RestaurantImageInline]
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        ("Basic Information", {
            "fields": ("merchant", "name", "slug", "description")
        }),
        ("Location", {
            "fields": ("city", "address", "postcode", "latitude", "longitude")
        }),
        ("Contact", {
            "fields": ("phone", "email", "website")
        }),
        ("Details", {
            "fields": ("categories", "price_range", "opening_hours")
        }),
        ("Status", {
            "fields": ("verified", "is_featured", "is_active")
        }),
    )


class DealImageInline(admin.TabularInline):
    model = DealImage
    extra = 1
    fields = ("image", "alt_text", "is_primary", "order")


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = (
        "title", "restaurant", "deal_type", "is_featured",
        "start_date", "end_date", "used_count", "created_at"
    )
    list_filter = ("deal_type", "is_featured", "restaurant__city", "start_date", "end_date", "created_at")
    search_fields = ("title", "description", "restaurant__name")
    raw_id_fields = ("restaurant",)
    inlines = [DealImageInline]
    date_hierarchy = "start_date"
    fieldsets = (
        ("Basic Information", {
            "fields": ("restaurant", "title", "description", "deal_type")
        }),
        ("Deal Details", {
            "fields": (
                "discount_percentage", "discount_amount", "minimum_spend",
                "terms_and_conditions"
            )
        }),
        ("Validity", {
            "fields": ("start_date", "end_date")
        }),
        ("Usage Limits", {
            "fields": ("max_uses", "used_count", "max_per_user")
        }),
        ("Status", {
            "fields": ("is_featured", "is_active")
        }),
    )


@admin.register(RestaurantImage)
class RestaurantImageAdmin(admin.ModelAdmin):
    list_display = ("restaurant", "is_primary", "order", "created_at")
    list_filter = ("is_primary", "created_at")
    search_fields = ("restaurant__name", "alt_text")
    raw_id_fields = ("restaurant",)


@admin.register(DealImage)
class DealImageAdmin(admin.ModelAdmin):
    list_display = ("deal", "is_primary", "order", "created_at")
    list_filter = ("is_primary", "created_at")
    search_fields = ("deal__title", "alt_text")
    raw_id_fields = ("deal",)


@admin.register(SavedRestaurant)
class SavedRestaurantAdmin(admin.ModelAdmin):
    list_display = ("user", "restaurant", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "restaurant__name")
    raw_id_fields = ("user", "restaurant")


@admin.register(SavedDeal)
class SavedDealAdmin(admin.ModelAdmin):
    list_display = ("user", "deal", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "deal__title")
    raw_id_fields = ("user", "deal")


@admin.register(DealUse)
class DealUseAdmin(admin.ModelAdmin):
    list_display = ("user", "deal", "used_at", "restaurant_confirmed", "created_at")
    list_filter = ("restaurant_confirmed", "used_at", "created_at")
    search_fields = ("user__email", "deal__title", "notes")
    raw_id_fields = ("user", "deal")
