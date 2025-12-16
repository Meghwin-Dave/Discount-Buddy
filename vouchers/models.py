from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel, SoftDeleteModel
from users.models import User


class Merchant(TimeStampedModel, SoftDeleteModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="merchant")
    name = models.CharField(max_length=255)
    verified = models.BooleanField(default=False, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["verified"]),
        ]

    def __str__(self) -> str:
        return self.name


class VoucherCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)

    class Meta:
        verbose_name_plural = "Voucher categories"

    def __str__(self) -> str:
        return self.name


class Voucher(TimeStampedModel, SoftDeleteModel):
    code = models.CharField(max_length=50, unique=True, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    merchant = models.ForeignKey(
        Merchant, on_delete=models.CASCADE, related_name="vouchers"
    )
    category = models.ForeignKey(
        VoucherCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vouchers",
    )
    discount_percent = models.FloatField()
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    total_quantity = models.PositiveIntegerField()
    sold_quantity = models.PositiveIntegerField(default=0)
    max_per_user = models.PositiveIntegerField(default=5)

    class Meta:
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["merchant", "category"]),
        ]

    def __str__(self) -> str:
        return self.code

    @property
    def remaining_quantity(self) -> int:
        return max(self.total_quantity - self.sold_quantity, 0)

    def is_active(self) -> bool:
        now = timezone.now()
        return (
            self.is_active
            and self.start_date <= now <= self.end_date
            and self.remaining_quantity > 0
        )


class VoucherRedemption(TimeStampedModel):
    voucher = models.ForeignKey(
        Voucher, on_delete=models.CASCADE, related_name="redemptions"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="voucher_redemptions"
    )
    redeemed_at = models.DateTimeField(default=timezone.now)
    is_successful = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "voucher"]),
            models.Index(fields=["redeemed_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} - {self.voucher.code}"


