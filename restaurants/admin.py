from django.contrib import admin
from .models import (
    Country,
    City,
    RestaurantCategory,
    Restaurant,
    Deal,
    RestaurantImage,
    DealImage,
    SavedRestaurant,
    SavedDeal,
    DealUse,
    Cuisine,
    Review,
    Booking,
    MenuCategory,
    MenuItem,
    OpeningSlot,
    RestaurantProfile,
    MysteryVisit,
    MysteryScore,
    MysteryEvidence,
    Facility,
)
from wallet.models import Wallet, WalletTransaction
from .opening_hours_sync import sync_opening_slots_from_opening_hours

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


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon", "is_active", "created_at")
    search_fields = ("name", "slug")
    list_filter = ("is_active", "created_at")
    prepopulated_fields = {"slug": ("name",)}


class RestaurantImageInline(admin.TabularInline):
    model = RestaurantImage
    extra = 1
    fields = ("image", "alt_text", "is_primary", "order")


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "city",
        "verified",
        "is_featured",
        "price_range",
        "occupancy",
        "required_visit_gap",
        "last_mystery_visit_date",
        "next_mystery_visit_date",
        "created_at",
    )
    list_filter = ("verified", "is_featured", "city__country", "city", "created_at")
    search_fields = ("name", "address", "city__name", "description")
    raw_id_fields = ("merchant", "city")
    filter_horizontal = ("categories", "cuisines", "facilities")
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
        (
            "Details",
            {
                "fields": (
                    "categories",
                    "cuisines",
                    "facilities",
                    "price_range",
                    "occupancy",
                    "opening_hours",
                    "required_visit_gap",
                )
            },
        ),
        ("Status", {
            "fields": ("verified", "is_featured", "is_active")
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.opening_hours:
            sync_opening_slots_from_opening_hours(obj)

    def last_mystery_visit_date(self, obj):
        visit = (
            MysteryVisit.objects.filter(restaurant=obj, status=MysteryVisit.STATUS_SUBMITTED)
            .order_by("-scheduled_for")
            .first()
        )
        return visit.scheduled_for if visit else None

    last_mystery_visit_date.short_description = "Last Mystery Visit"

    def next_mystery_visit_date(self, obj):
        visit = (
            MysteryVisit.objects.filter(
                restaurant=obj, status__in=[MysteryVisit.STATUS_ASSIGNED, MysteryVisit.STATUS_IN_PROGRESS]
            )
            .order_by("scheduled_for")
            .first()
        )
        return visit.scheduled_for if visit else None

    next_mystery_visit_date.short_description = "Next Mystery Visit"


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


@admin.register(Cuisine)
class CuisineAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon", "is_active", "created_at")
    search_fields = ("name", "slug")
    list_filter = ("is_active", "created_at")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("user", "restaurant", "rating", "is_verified", "created_at")
    list_filter = ("rating", "is_verified", "created_at")
    search_fields = ("user__email", "restaurant__name", "comment")
    raw_id_fields = ("user", "restaurant")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("user", "restaurant", "booking_date", "number_of_guests", "status", "created_at")
    list_filter = ("status", "booking_date", "created_at")
    search_fields = ("user__email", "restaurant__name", "contact_name", "contact_phone")
    raw_id_fields = ("user", "restaurant")
    date_hierarchy = "booking_date"


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 1
    fields = ("name", "description", "price", "is_vegetarian", "is_vegan", "is_gluten_free", "is_available", "order")


@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ("restaurant", "name", "order", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("restaurant__name", "name", "description")
    raw_id_fields = ("restaurant",)
    inlines = [MenuItemInline]
    ordering = ("restaurant", "order", "name")


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_available", "order", "created_at")
    list_filter = ("is_vegetarian", "is_vegan", "is_gluten_free", "is_available", "created_at")
    search_fields = ("name", "description", "category__name", "category__restaurant__name")
    raw_id_fields = ("category",)


@admin.register(OpeningSlot)
class OpeningSlotAdmin(admin.ModelAdmin):
    list_display = ("restaurant", "day_of_week", "opening_time", "closing_time", "is_closed")
    list_filter = ("day_of_week", "is_closed")
    search_fields = ("restaurant__name",)
    raw_id_fields = ("restaurant",)


@admin.register(RestaurantProfile)
class RestaurantProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "restaurant", "is_primary_owner", "created_at")
    list_filter = ("is_primary_owner", "created_at")
    search_fields = ("user__email", "restaurant__name")
    raw_id_fields = ("user", "restaurant")


@admin.register(MysteryVisit)
class MysteryVisitAdmin(admin.ModelAdmin):
    list_display = (
        "restaurant",
        "mystery_guest",
        "scheduled_for",
        "status",
        "overall_score",
        "is_risk_flagged",
        "created_at",
    )
    list_filter = ("status", "is_risk_flagged", "scheduled_for", "created_at")
    search_fields = ("restaurant__name", "mystery_guest__email")
    raw_id_fields = ("restaurant", "mystery_guest")
    date_hierarchy = "scheduled_for"


@admin.register(MysteryScore)
class MysteryScoreAdmin(admin.ModelAdmin):
    list_display = ("visit", "section", "score", "created_at")
    list_filter = ("section", "created_at")
    search_fields = ("visit__restaurant__name", "visit__mystery_guest__email")
    raw_id_fields = ("visit",)


@admin.register(MysteryEvidence)
class MysteryEvidenceAdmin(admin.ModelAdmin):
    list_display = ("visit", "description", "created_at")
    search_fields = ("visit__restaurant__name", "visit__mystery_guest__email", "description")
    raw_id_fields = ("visit",)
