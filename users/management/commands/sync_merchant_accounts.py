from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Q

from users.merchant_utils import ensure_merchant_account, user_is_merchant
from users.models import UserProfile

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Fix merchant users created from Django admin by ensuring UserProfile.role "
        "and vouchers.Merchant records exist."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            help="Sync a single user by email instead of scanning all merchant users.",
        )

    def handle(self, *args, **options):
        email = options.get("email")

        if email:
            users = User.objects.filter(email__iexact=email)
            if not users.exists():
                self.stderr.write(self.style.ERROR(f"No user found for email: {email}"))
                return
        else:
            users = User.objects.filter(
                Q(is_merchant=True) | Q(profile__role=UserProfile.ROLE_MERCHANT)
            ).distinct()

        fixed = 0
        for user in users:
            if not user_is_merchant(user):
                continue
            ensure_merchant_account(user)
            fixed += 1
            self.stdout.write(self.style.SUCCESS(f"Synced merchant account: {user.email}"))

        self.stdout.write(self.style.SUCCESS(f"Done. Synced {fixed} merchant account(s)."))
