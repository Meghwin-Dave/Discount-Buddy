from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

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
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
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
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Contact
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    
    # Details
    categories = models.ManyToManyField(RestaurantCategory, related_name="restaurants", blank=True)
    price_range = models.PositiveIntegerField(
        default=2,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        help_text="Price range from 1 (budget) to 4 (expensive)"
    )
    
    # Status
    verified = models.BooleanField(default=False, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    
    # Hours (simple JSON field - can be extended later)
    opening_hours = models.JSONField(default=dict, blank=True)
    
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


class Deal(TimeStampedModel, SoftDeleteModel):
    """Deal model - different types of deals"""
    DEAL_TYPE_TWO_FOR_ONE = "two_for_one"
    DEAL_TYPE_PERCENTAGE = "percentage"
    DEAL_TYPE_FIXED = "fixed"
    DEAL_TYPE_OTHER = "other"
    
    DEAL_TYPE_CHOICES = [
        (DEAL_TYPE_TWO_FOR_ONE, "2-for-1"),
        (DEAL_TYPE_PERCENTAGE, "Percentage Discount"),
        (DEAL_TYPE_FIXED, "Fixed Discount"),
        (DEAL_TYPE_OTHER, "Other"),
    ]
    
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name="deals"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
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
    """Track when a deal is used by a user"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="deal_uses")
    deal = models.ForeignKey(Deal, on_delete=models.CASCADE, related_name="deal_uses")
    used_at = models.DateTimeField(default=timezone.now)
    restaurant_confirmed = models.BooleanField(
        default=False,
        help_text="Whether restaurant has confirmed the use"
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=["user", "deal"]),
            models.Index(fields=["used_at"]),
        ]
        
    def __str__(self):
        return f"{self.user.email} used {self.deal.title} at {self.used_at}"
