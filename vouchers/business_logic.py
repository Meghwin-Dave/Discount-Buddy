from django.utils import timezone

from .models import Voucher


def is_voucher_valid_for_user(voucher: Voucher, user) -> bool:
    """Check time window, quantity and basic constraints."""
    if not voucher.is_active:
        return False
    now = timezone.now()
    if not (voucher.start_date <= now <= voucher.end_date):
        return False
    if voucher.remaining_quantity <= 0:
        return False
    # Per-user limits & other advanced checks would go here
    return True


def calculate_resale_price(voucher_price, discount_rate: float):
    """Basic resale pricing utility."""
    return voucher_price * (1 - discount_rate)


