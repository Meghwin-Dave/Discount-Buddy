from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import math

from core.models import TimeStampedModel, SoftDeleteModel
from users.models import User


class Country(TimeStampedModel):
    """Country model"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=2, unique=True, help_text="ISO 3166-1 alpha-2 code (e.g., GB, DE)")
    flag_emoji = models.CharField(max_length=10, blank=True, help_text="Flag emoji for the country")
    
    class Meta:
        verbose_name_plural = "Countries"
        ordering = ["name"]
        
    def __str__(self):
        return self.name


class City(TimeStampedModel):
    """City model"""
    name = models.CharField(max_length=100)
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="cities")
    slug = models.SlugField(max_length=120, unique=True)
    latitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    longitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    class Meta:
        verbose_name_plural = "Cities"
        unique_together = [["name", "country"]]
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active", "country"]),
        ]
        
    def __str__(self):
        return f"{self.name}, {self.country.name}"


class RestaurantCategory(TimeStampedModel):
    """Restaurant category (e.g., Italian, Asian, Fast Food)"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon name or emoji")
    
    class Meta:
        verbose_name_plural = "Restaurant Categories"
        ordering = ["name"]
        
    def __str__(self):
        return self.name


class Facility(TimeStampedModel):
    """Restaurant facility (e.g., WiFi, Parking, Outdoor Seating)"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon name (e.g., wifi, local_parking)")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name_plural = "Facilities"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Restaurant(TimeStampedModel, SoftDeleteModel):
    """Restaurant model"""
    merchant = models.ForeignKey(
        "vouchers.Merchant",
        on_delete=models.CASCADE,
        related_name="restaurants",
        null=True,
        blank=True
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    
    # Location
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="restaurants")
    address = models.CharField(max_length=500)
    postcode = models.CharField(max_length=20, blank=True)
    latitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    longitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    
    # Contact
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    
    # Details
    categories = models.ManyToManyField(RestaurantCategory, related_name="restaurants", blank=True)
    cuisines = models.ManyToManyField("Cuisine", related_name="restaurants", blank=True)
    facilities = models.ManyToManyField(Facility, related_name="restaurants", blank=True)
    price_range = models.PositiveIntegerField(
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        help_text="Price range from 1 (budget) to 4 (expensive)"
    )
    OCCUPANCY_AVAILABLE = "available"
    OCCUPANCY_MODERATELY_BUSY = "moderately_busy"
    OCCUPANCY_VERY_BUSY = "very_busy"

    OCCUPANCY_CHOICES = [
        (OCCUPANCY_AVAILABLE, "Available"),
        (OCCUPANCY_MODERATELY_BUSY, "Moderately Busy"),
        (OCCUPANCY_VERY_BUSY, "Very Busy"),
    ]

    occupancy = models.CharField(
        max_length=32,
        choices=OCCUPANCY_CHOICES,
        default=OCCUPANCY_AVAILABLE,
        help_text="Current occupancy status as shown to users.",
    )
    
    # Status
    verified = models.BooleanField(default=False, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    
    # Menu configuration
    MENU_TYPE_STRUCTURED = "structured"
    MENU_TYPE_IMAGE = "image"
    MENU_TYPE_CHOICES = [
        (MENU_TYPE_STRUCTURED, "Structured Menu"),
        (MENU_TYPE_IMAGE, "Image Menu"),
    ]
    menu_type = models.CharField(
        max_length=20,
        choices=MENU_TYPE_CHOICES,
        default=MENU_TYPE_STRUCTURED,
        help_text="Whether to show structured menu items or uploaded menu images.",
    )

    # Hours (simple JSON field - can be extended later)
    opening_hours = models.JSONField(default=dict, blank=True)

    # Mystery Guest configuration
    required_visit_gap = models.PositiveIntegerField(
        default=30,
        help_text="Required minimum gap in days between scheduled mystery visits.",
    )
    
    class Meta:
        ordering = ["-is_featured", "-created_at"]
        indexes = [
            models.Index(fields=["city", "verified"]),
            models.Index(fields=["is_featured", "verified"]),
            models.Index(fields=["latitude", "longitude"]),
        ]
        
    def __str__(self):
        return f"{self.name} ({self.city.name})"
    
    def get_active_deals_count(self):
        """Count of active deals for this restaurant"""
        now = timezone.now()
        return self.deals.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).count()
    
    def get_average_rating(self):
        """Calculate average rating from reviews"""
        from django.db.models import Avg
        result = self.reviews.aggregate(avg_rating=Avg('rating'))
        return result['avg_rating'] or 0.0
    
    def get_reviews_count(self):
        """Get total number of reviews"""
        return self.reviews.count()
    
    def is_open_now(self):
        """Check if restaurant is currently open"""
        from datetime import datetime
        now = datetime.now()
        current_day = now.weekday()
        current_time = now.time()
        
        slot = self.opening_slots.filter(day_of_week=current_day).first()
        if not slot or slot.is_closed:
            return False
        return slot.opening_time <= current_time <= slot.closing_time

    @property
    def last_mystery_visit(self):
        """Return the most recent completed mystery visit for this restaurant."""
        return getattr(self, "_last_mystery_visit", None)

    @property
    def next_mystery_visit(self):
        """Return the next scheduled mystery visit for this restaurant."""
        return getattr(self, "_next_mystery_visit", None)

    def get_latest_mystery_visit(self):
        """Return the most recent submitted mystery visit, if any."""
        from .models import MysteryVisit  # local import to avoid circulars

        return (
            MysteryVisit.objects.filter(
                restaurant=self, status=MysteryVisit.STATUS_SUBMITTED
            )
            .order_by("-submitted_at", "-scheduled_for")
            .first()
        )

    def get_mystery_score_with_decay(self, now=None) -> float:
        """
        Return the decayed mystery score on a 0–100 scale.

        Implements freshness decay so older visits contribute less:
        - Uses exponential decay with a 90-day time constant.
        """
        now = now or timezone.now()
        visit = self.get_latest_mystery_visit()
        if not visit or visit.overall_score is None:
            return 0.0

        reference_date = visit.submitted_at or visit.scheduled_for or visit.created_at
        if not reference_date:
            return float(visit.overall_score)

        days_since = (now - reference_date).days
        if days_since <= 0:
            return float(visit.overall_score)

        # Exponential decay; around ~37% contribution after 90 days.
        decay_factor = math.exp(-days_since / 90.0)
        return float(visit.overall_score) * decay_factor

    def get_leaderboard_score(self, now=None) -> float:
        """
        Leaderboard Score = (User Rating × 40%) + (Mystery Score × 60%)

        - User Rating is the average review rating (0–5) normalised to 0–100.
        - Mystery Score is the decayed overall mystery score (0–100).
        """
        now = now or timezone.now()

        # Average user rating on 0–5
        avg_rating = getattr(self, "average_rating", None)
        if avg_rating is None:
            avg_rating = self.get_average_rating()
        user_component = float(avg_rating or 0.0) * 20.0  # 0–5 → 0–100

        mystery_component = self.get_mystery_score_with_decay(now=now)

        return round(user_component * 0.4 + mystery_component * 0.6, 2)


class Deal(TimeStampedModel, SoftDeleteModel):
    """Deal model - different types of deals"""
    DEAL_TYPE_TWO_FOR_ONE = "two_for_one"
    DEAL_TYPE_PERCENTAGE = "percentage"
    DEAL_TYPE_FIXED = "fixed"
    DEAL_TYPE_COMBO = "combo"
    DEAL_TYPE_OTHER = "other"
    
    DEAL_TYPE_CHOICES = [
        (DEAL_TYPE_TWO_FOR_ONE, "2-for-1"),
        (DEAL_TYPE_PERCENTAGE, "Percentage Discount"),
        (DEAL_TYPE_FIXED, "Fixed Discount"),
        (DEAL_TYPE_COMBO, "Combo Deal"),
        (DEAL_TYPE_OTHER, "Other"),
    ]
    
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="deals"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=50, blank=True, null=True, help_text="Two-word description (e.g. Save Today)")
    deal_type = models.CharField(max_length=20, choices=DEAL_TYPE_CHOICES, default=DEAL_TYPE_PERCENTAGE)
    
    # Deal details
    discount_percentage = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentage discount (0-100)"
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Fixed discount amount"
    )
    combo_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Fixed price for the combo"
    )
    minimum_spend = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum spend required"
    )
    terms_and_conditions = models.TextField(blank=True)
    
    # Validity
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Usage limits
    max_uses = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum total uses (None = unlimited)")
    used_count = models.PositiveIntegerField(default=0)
    max_per_user = models.PositiveIntegerField(default=1, help_text="Maximum uses per user")
    
    # Status
    is_featured = models.BooleanField(default=False, db_index=True)
    
    class Meta:
        ordering = ["-is_featured", "-created_at"]
        indexes = [
            models.Index(fields=["restaurant", "is_active"]),
            models.Index(fields=["start_date", "end_date", "is_active"]),
            models.Index(fields=["is_featured", "is_active"]),
        ]
        
    def __str__(self):
        return f"{self.title} - {self.restaurant.name}"
    
    def is_active_now(self):
        """Check if deal is currently active"""
        now = timezone.now()
        return (
            self.is_active  # From SoftDeleteModel
            and self.start_date <= now <= self.end_date
            and (self.max_uses is None or self.used_count < self.max_uses)
        )
    
    def can_user_use(self, user):
        """Check if user can use this deal"""
        if not self.is_active_now():
            return False
        user_uses = self.deal_uses.filter(user=user).count()
        return user_uses < self.max_per_user


class RestaurantImage(TimeStampedModel):
    """Restaurant images"""
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="images"
    )
    image = models.ImageField(upload_to="restaurants/%Y/%m/%d/")
    alt_text = models.CharField(max_length=255, blank=True)
    
    # Image types
    TYPE_GALLERY = "gallery"
    TYPE_MENU = "menu"
    TYPE_CHOICES = [
        (TYPE_GALLERY, "Gallery"),
        (TYPE_MENU, "Menu Image"),
    ]
    image_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_GALLERY
    )
    
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ["is_primary", "order", "created_at"]
        
    def __str__(self):
        return f"{self.restaurant.name} - Image {self.id}"


class DealImage(TimeStampedModel):
    """Deal images"""
    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name="images"
    )
    image = models.ImageField(upload_to="deals/%Y/%m/%d/")
    alt_text = models.CharField(max_length=255, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ["is_primary", "order", "created_at"]
        
    def __str__(self):
        return f"{self.deal.title} - Image {self.id}"


class SavedRestaurant(TimeStampedModel):
    """User saved restaurants"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_restaurants")
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="saved_by")
    
    class Meta:
        unique_together = [["user", "restaurant"]]
        indexes = [
            models.Index(fields=["user", "created_at"]),
        ]
        
    def __str__(self):
        return f"{self.user.email} saved {self.restaurant.name}"


class SavedDeal(TimeStampedModel):
    """User saved deals"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_deals")
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="saved_by")
    
    class Meta:
        unique_together = [["user", "deal"]]
        indexes = [
            models.Index(fields=["user", "created_at"]),
        ]
        
    def __str__(self):
        return f"{self.user.email} saved {self.deal.title}"


class DealUse(TimeStampedModel):
    """
    Track when a deal is claimed/used by a user.

    This model also acts as the redemption record for a single user/deal pair,
    holding the 6‑digit redemption code and QR code used at the restaurant.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="deal_uses")
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="deal_uses")
    used_at = models.DateTimeField(default=timezone.now)
    restaurant_confirmed = models.BooleanField(
        default=False,
        help_text="Whether restaurant has confirmed the use",
    )
    notes = models.TextField(blank=True)

    # Redemption-related fields
    redemption_code = models.CharField(
        max_length=6,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        help_text="Unique 6-digit numeric code used for in-restaurant redemption",
    )
    qr_code = models.ImageField(
        upload_to="deal_redemptions/%Y/%m/%d/",
        null=True,
        blank=True,
        help_text="QR code image encoding the redemption reference",
    )
    is_redeemed = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this redemption has been completed in the restaurant",
    )
    redeemed_at = models.DateTimeField(null=True, blank=True)
    redeemed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="redeemed_deal_uses",
        help_text="Restaurant staff user who performed the redemption",
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    people_count = models.PositiveIntegerField(null=True, blank=True)
    discount_amount_saved = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    final_bill_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "deal"]),
            models.Index(fields=["used_at"]),
            models.Index(fields=["redemption_code"]),
            models.Index(fields=["is_redeemed", "redeemed_at"]),
        ]

    def __str__(self):
        return f"{self.user.email} used {self.deal.title} at {self.used_at}"


class Cuisine(TimeStampedModel):
    """Cuisine type (e.g., Italian, Chinese, Indian) - separate from RestaurantCategory"""
    name = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(max_length=120, unique=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon name or emoji")
    is_active = models.BooleanField(default=True, db_index=True)
    
    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active", "name"]),
        ]
        
    def __str__(self):
        return self.name


class Review(TimeStampedModel):
    """User reviews for restaurants"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5"
    )
    comment = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False, help_text="Whether review is verified")
    
    class Meta:
        unique_together = [["user", "restaurant"]]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["restaurant", "rating"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["restaurant", "created_at"]),
        ]
        
    def __str__(self):
        return f"{self.user.email} - {self.restaurant.name} ({self.rating} stars)"


class Booking(TimeStampedModel):
    """Restaurant bookings/reservations"""
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"
    STATUS_COMPLETED = "completed"
    
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_COMPLETED, "Completed"),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="bookings")
    booking_date = models.DateTimeField(db_index=True)
    number_of_guests = models.PositiveIntegerField(default=2, validators=[MinValueValidator(1)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    special_requests = models.TextField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_name = models.CharField(max_length=255, blank=True)
    
    class Meta:
        ordering = ["-booking_date"]
        indexes = [
            models.Index(fields=["user", "booking_date"]),
            models.Index(fields=["restaurant", "booking_date"]),
            models.Index(fields=["status", "booking_date"]),
        ]
        
    def __str__(self):
        return f"{self.user.email} - {self.restaurant.name} on {self.booking_date}"
    
    def can_cancel(self):
        """Check if booking can be cancelled"""
        return self.status in [self.STATUS_PENDING, self.STATUS_CONFIRMED]


class MenuCategory(TimeStampedModel):
    """Menu categories (e.g., Appetizers, Main Course, Desserts)"""
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="menu_categories"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ["order", "name"]
        unique_together = [["restaurant", "name"]]
        indexes = [
            models.Index(fields=["restaurant", "is_active", "order"]),
        ]
        
    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"


class MenuItem(TimeStampedModel):
    """Menu items"""
    category = models.ForeignKey(
        MenuCategory,
        on_delete=models.CASCADE,
        related_name="items"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_vegetarian = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_gluten_free = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True, db_index=True)
    image = models.ImageField(upload_to="menu/%Y/%m/%d/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ["order", "name"]
        indexes = [
            models.Index(fields=["category", "is_available"]),
        ]
        
    def __str__(self):
        return f"{self.category.restaurant.name} - {self.name}"


class OpeningSlot(TimeStampedModel):
    """Restaurant opening time slots"""
    DAY_CHOICES = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]
    
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="opening_slots"
    )
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    is_closed = models.BooleanField(default=False, help_text="If true, restaurant is closed on this day")
    
    class Meta:
        unique_together = [["restaurant", "day_of_week"]]
        ordering = ["day_of_week", "opening_time"]
        indexes = [
            models.Index(fields=["restaurant", "day_of_week"]),
        ]
        
    def __str__(self):
        day_name = dict(self.DAY_CHOICES)[self.day_of_week]
        if self.is_closed:
            return f"{self.restaurant.name} - {day_name} (Closed)"
        return f"{self.restaurant.name} - {day_name} ({self.opening_time} - {self.closing_time})"
    
    def is_open_now(self):
        """Check if restaurant is currently open (simplified - doesn't check time)"""
        from datetime import datetime
        if self.is_closed:
            return False
        current_day = datetime.now().weekday()
        return current_day == self.day_of_week


class RestaurantProfile(TimeStampedModel):
    """Extended profile for restaurant owners/managers"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="restaurant_profile"
    )
    restaurant = models.OneToOneField(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="owner_profile"
    )
    is_primary_owner = models.BooleanField(default=True)
    
    class Meta:
        indexes = [
            models.Index(fields=["user", "restaurant"]),
        ]
        
    def __str__(self):
        return f"{self.user.email} - {self.restaurant.name}"


class MysteryVisit(TimeStampedModel):
    """Mystery Guest visit assignment and report."""

    STATUS_ASSIGNED = "assigned"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_SUBMITTED = "submitted"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_ASSIGNED, "Assigned"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    mystery_guest = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="mystery_visits",
        help_text="Mystery Guest assigned to perform this visit.",
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="mystery_visits",
    )
    scheduled_for = models.DateTimeField(
        help_text="Planned date/time for the visit.",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ASSIGNED,
        db_index=True,
    )
    overall_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Final weighted mystery score (0–100).",
    )
    is_risk_flagged = models.BooleanField(
        default=False,
        help_text="Flag for restaurants requiring quality follow-up.",
    )
    comments = models.TextField(blank=True)

    class Meta:
        ordering = ["-scheduled_for"]
        indexes = [
            models.Index(fields=["restaurant", "scheduled_for"]),
            models.Index(fields=["mystery_guest", "scheduled_for"]),
            models.Index(fields=["status", "scheduled_for"]),
        ]

    def __str__(self):
        return f"Mystery visit to {self.restaurant.name} by {self.mystery_guest.email}"


class MysteryScore(TimeStampedModel):
    """Section-wise scores for a mystery visit."""

    SECTION_PRE_VISIT = "pre_visit"
    SECTION_AMBIENCE = "ambience"
    SECTION_SERVICE = "service"
    SECTION_FOOD = "food"
    SECTION_DISCOUNT_EXPERIENCE = "discount_experience"
    SECTION_HYGIENE = "hygiene"

    SECTION_CHOICES = [
        (SECTION_PRE_VISIT, "Pre-Visit"),
        (SECTION_AMBIENCE, "Ambience"),
        (SECTION_SERVICE, "Service"),
        (SECTION_FOOD, "Food"),
        (SECTION_DISCOUNT_EXPERIENCE, "Discount Experience"),
        (SECTION_HYGIENE, "Hygiene"),
    ]

    visit = models.ForeignKey(
        MysteryVisit,
        on_delete=models.CASCADE,
        related_name="scores",
    )
    section = models.CharField(max_length=50, choices=SECTION_CHOICES, db_index=True)
    score = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Section score on a 0–10 scale.",
    )
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = [["visit", "section"]]
        indexes = [
            models.Index(fields=["visit", "section"]),
        ]

    def __str__(self):
        return f"{self.visit} - {self.get_section_display()}: {self.score}"


class MysteryEvidence(TimeStampedModel):
    """Evidence uploaded by Mystery Guests: photos, receipts, etc."""

    visit = models.ForeignKey(
        MysteryVisit,
        on_delete=models.CASCADE,
        related_name="evidence",
    )
    file = models.FileField(upload_to="mystery_evidence/%Y/%m/%d/")
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["visit", "created_at"]),
        ]

    def __str__(self):
        return f"Evidence for visit {self.visit_id}"


# Alias models for clarity (using existing models)
# FavouriteRestaurant = SavedRestaurant (already exists)
# ClaimedDeal = DealUse (already exists)

class RestaurantPartnerRequest(TimeStampedModel):
    """
    Model to store 'Join as Restaurant Partner' inquiries from the mobile app.
    """
    STATUS_PENDING = "pending"
    STATUS_CONTACTED = "contacted"
    STATUS_REJECTED = "rejected"
    STATUS_APPROVED = "approved"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONTACTED, "Contacted"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_APPROVED, "Approved"),
    ]

    restaurant_name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    city_name = models.CharField(max_length=100)
    website = models.URLField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Restaurant Partner Request"
        verbose_name_plural = "Restaurant Partner Requests"

    def __str__(self):
        return f"{self.restaurant_name} - {self.contact_name}"