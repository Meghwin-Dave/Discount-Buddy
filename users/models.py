from datetime import datetime

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel
from core.mixins.processed_image import ProcessedImageBehaviorMixin
from core.utils.image_paths import processed_large_upload_to, processed_medium_upload_to


def profile_picture_source_upload_to(instance, filename):
    date_path = datetime.now().strftime("%Y/%m/%d")
    return f"profile_pictures/{date_path}/{filename}"


class User(AbstractUser):
    email = models.EmailField(unique=True)
    is_merchant = models.BooleanField(default=False)
    is_customer = models.BooleanField(default=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self) -> str:
        return self.email


class UserProfile(ProcessedImageBehaviorMixin, models.Model):
    ROLE_ADMIN = "admin"
    ROLE_MERCHANT = "merchant"
    ROLE_CUSTOMER = "customer"
    ROLE_MYSTERY_GUEST = "mystery_guest"

    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_MERCHANT, "Merchant"),
        (ROLE_CUSTOMER, "Customer"),
        (ROLE_MYSTERY_GUEST, "Mystery Guest"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CUSTOMER)
    phone_number = models.CharField(max_length=20, blank=True)
    profile_picture = models.ImageField(
        upload_to=profile_picture_source_upload_to,
        null=True,
        blank=True,
        help_text="Upload intake only; cleared after WebP processing.",
    )
    profile_picture_medium = models.ImageField(
        upload_to=processed_medium_upload_to,
        null=True,
        blank=True,
    )
    profile_picture_large = models.ImageField(
        upload_to=processed_large_upload_to,
        null=True,
        blank=True,
    )
    marketing_opt_in = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.user.email} ({self.role})"


class RegistrationOTP(TimeStampedModel):
    """
    Temporary record used for two-stage email OTP registration.

    Stores a 4-digit code sent to the user's email along with the desired role.
    """

    email = models.EmailField(db_index=True)
    role = models.CharField(max_length=20, choices=UserProfile.ROLE_CHOICES, default=UserProfile.ROLE_CUSTOMER)
    otp_code = models.CharField(max_length=4)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["email", "is_verified", "expires_at"]),
        ]

    def __str__(self) -> str:
        return f"OTP for {self.email} ({'verified' if self.is_verified else 'pending'})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at


class PasswordResetOTP(TimeStampedModel):
    """
    Temporary record used for password reset OTP verification.
    """

    email = models.EmailField(db_index=True)
    otp_code = models.CharField(max_length=4)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["email", "is_verified", "otp_code", "expires_at"]),
        ]

    def __str__(self) -> str:
        return f"Reset OTP for {self.email} ({'verified' if self.is_verified else 'pending'})"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at
