from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .merchant_utils import ensure_merchant_account, user_is_merchant
from .models import UserProfile

User = get_user_model()


@receiver(post_save, sender=User)
def sync_merchant_user_on_save(sender, instance, **kwargs):
    if instance.is_merchant:
        ensure_merchant_account(instance)


@receiver(post_save, sender=UserProfile)
def sync_merchant_profile_on_save(sender, instance, **kwargs):
    if instance.role == UserProfile.ROLE_MERCHANT:
        ensure_merchant_account(instance.user)
