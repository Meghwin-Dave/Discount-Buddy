from django.contrib.auth import get_user_model
from rest_framework.exceptions import PermissionDenied

from .models import UserProfile

User = get_user_model()


def user_is_merchant(user) -> bool:
    """True when the user is a merchant via flag or profile role."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_merchant", False):
        return True
    try:
        return user.profile.role == UserProfile.ROLE_MERCHANT
    except UserProfile.DoesNotExist:
        return False


def ensure_merchant_account(user):
    """
    Ensure merchant users have a matching UserProfile and vouchers.Merchant row.

    Admin-created users often have is_merchant=True but no profile/merchant record.
    """
    if not user_is_merchant(user):
        return None

    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"role": UserProfile.ROLE_MERCHANT},
    )
    if profile.role != UserProfile.ROLE_MERCHANT:
        profile.role = UserProfile.ROLE_MERCHANT
        profile.save(update_fields=["role"])

    if not user.is_merchant or user.is_customer:
        User.objects.filter(pk=user.pk).update(is_merchant=True, is_customer=False)

    from vouchers.models import Merchant

    merchant, _ = Merchant.objects.get_or_create(
        user=user,
        defaults={"name": user.username or user.email},
    )
    return merchant


def get_merchant_for_user(user):
    """Return the merchant account for an authorized merchant user."""
    if not user_is_merchant(user):
        raise PermissionDenied("User is not a merchant.")
    return ensure_merchant_account(user)
