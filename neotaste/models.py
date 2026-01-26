from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.utils import timezone
from django.core.validators import RegexValidator
from django.db.models import Q

from core.models import TimeStampedModel, SoftDeleteModel


class NeoTasteUserManager(BaseUserManager):
    """Custom user manager for mobile number authentication"""
    
    def create_user(self, mobile_number, **extra_fields):
        if not mobile_number:
            raise ValueError('The mobile number must be set')
        user = self.model(mobile_number=mobile_number, **extra_fields)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, mobile_number, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(mobile_number, **extra_fields)


class NeoTasteUser(AbstractBaseUser, TimeStampedModel):
    """Custom user model with mobile number authentication"""
    
    MEMBERSHIP_REGULAR = 'regular'
    MEMBERSHIP_PREMIUM = 'premium'
    MEMBERSHIP_CHOICES = [
        (MEMBERSHIP_REGULAR, 'Regular'),
        (MEMBERSHIP_PREMIUM, 'Premium'),
    ]
    
    mobile_number = models.CharField(
        max_length=15,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ],
        db_index=True
    )
    is_active = models.BooleanField(default=True, db_index=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    selected_city = models.ForeignKey(
        'City',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='selected_by_users'
    )
    membership_status = models.CharField(
        max_length=20,
        choices=MEMBERSHIP_CHOICES,
        default=MEMBERSHIP_REGULAR
    )
    
    USERNAME_FIELD = 'mobile_number'
    REQUIRED_FIELDS = []
    
    objects = NeoTasteUserManager()
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['mobile_number']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.mobile_number
    
    def has_perm(self, perm, obj=None):
        return self.is_superuser
    
    def has_module_perms(self, app_label):
        return self.is_superuser


class City(TimeStampedModel):
    """City model for restaurant filtering"""
    
    name = models.CharField(max_length=100, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    class Meta:
        verbose_name_plural = 'Cities'
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return self.name


class Category(TimeStampedModel):
    """Restaurant category model"""
    
    name = models.CharField(max_length=100, unique=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return self.name


class Restaurant(TimeStampedModel, SoftDeleteModel):
    """Restaurant model"""
    
    name = models.CharField(max_length=255)
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name='restaurants'
    )
    categories = models.ManyToManyField(
        Category,
        related_name='restaurants',
        blank=True
    )
    address = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    
    class Meta:
        ordering = ['-is_featured', '-created_at']
        indexes = [
            models.Index(fields=['city', 'is_active']),
            models.Index(fields=['is_featured', 'is_active']),
            models.Index(fields=['latitude', 'longitude']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.city.name})"
    
    def get_active_offers_count(self):
        """Get count of active offers for this restaurant"""
        now = timezone.now()
        return self.offers.filter(
            is_active=True,
            expiry_date__gt=now
        ).count()


class Offer(TimeStampedModel, SoftDeleteModel):
    """Offer/Deal model"""
    
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='offers'
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    max_redemptions_per_user = models.PositiveIntegerField(default=1)
    expiry_date = models.DateTimeField()
    terms_and_conditions = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['restaurant', 'is_active']),
            models.Index(fields=['expiry_date', 'is_active']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.restaurant.name}"
    
    def is_valid(self):
        """Check if offer is currently valid"""
        now = timezone.now()
        return (
            self.is_active and
            self.expiry_date > now
        )
    
    def can_user_redeem(self, user):
        """Check if user can redeem this offer"""
        if not self.is_valid():
            return False
        
        user_redemptions_count = self.redemptions.filter(
            user=user
        ).count()
        
        return user_redemptions_count < self.max_redemptions_per_user


class Redemption(TimeStampedModel):
    """Redemption model to track offer redemptions"""
    
    STATUS_REDEEMED = 'redeemed'
    STATUS_USED = 'used'
    STATUS_EXPIRED = 'expired'
    
    STATUS_CHOICES = [
        (STATUS_REDEEMED, 'Redeemed'),
        (STATUS_USED, 'Used'),
        (STATUS_EXPIRED, 'Expired'),
    ]
    
    user = models.ForeignKey(
        NeoTasteUser,
        on_delete=models.CASCADE,
        related_name='redemptions'
    )
    offer = models.ForeignKey(
        Offer,
        on_delete=models.CASCADE,
        related_name='redemptions'
    )
    redeemed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_REDEEMED,
        db_index=True
    )
    
    class Meta:
        ordering = ['-redeemed_at']
        indexes = [
            models.Index(fields=['user', 'redeemed_at']),
            models.Index(fields=['offer', 'status']),
            models.Index(fields=['status', 'redeemed_at']),
        ]
        unique_together = [['user', 'offer']]
    
    def __str__(self):
        return f"{self.user.mobile_number} - {self.offer.title} ({self.status})"
    
    def mark_as_expired(self):
        """Mark redemption as expired"""
        if self.status == self.STATUS_REDEEMED:
            self.status = self.STATUS_EXPIRED
            self.save(update_fields=['status'])


class OTP(TimeStampedModel):
    """OTP model for authentication"""
    
    mobile_number = models.CharField(max_length=15, db_index=True)
    otp_code = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['mobile_number', 'is_verified']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"OTP for {self.mobile_number}"
    
    def is_valid(self):
        """Check if OTP is still valid"""
        return (
            not self.is_verified and
            timezone.now() < self.expires_at
        )
