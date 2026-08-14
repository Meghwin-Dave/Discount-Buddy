import random
import threading
from datetime import timedelta

from typing import Optional, Tuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.utils import timezone

from .models import PasswordResetOTP, RegistrationOTP

User = get_user_model()

OTP_EXPIRY_MINUTES = 10
DELETION_OTP_SUBJECT = "Account Deletion OTP - Discount Buddy"


def send_account_deletion_otp(email: str) -> bool:
    """
    Send the same account-deletion OTP used by the in-app API.

    Returns True if an account exists and an OTP was queued. Callers should
    not reveal that result to unauthenticated users.
    """
    email = (email or "").strip()
    if not email:
        return False

    user = User.objects.filter(email__iexact=email).first()
    if not user:
        return False

    email = user.email

    RegistrationOTP.objects.filter(email=email, is_verified=False).update(
        is_verified=True, verified_at=timezone.now()
    )

    otp_code = f"{random.randint(0, 9999):04d}"
    expires_at = timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    RegistrationOTP.objects.create(
        email=email,
        otp_code=otp_code,
        expires_at=expires_at,
    )

    from_email = settings.DEFAULT_FROM_EMAIL
    message = (
        f"Your verification code for account deletion is {otp_code}. "
        f"It expires in {OTP_EXPIRY_MINUTES} minutes. "
        "If you did not request this, please ignore this email."
    )

    def send_otp_email():
        try:
            send_mail(
                DELETION_OTP_SUBJECT,
                message,
                from_email,
                [email],
                fail_silently=False,
            )
        except Exception:
            pass

    threading.Thread(target=send_otp_email).start()
    return True


def delete_account_with_otp(email: str, otp: str) -> Tuple[bool, Optional[str]]:
    """
    Verify the deletion OTP and permanently delete the user.

    Associated data (profile, wallet, bookings, reviews, saved items,
    notifications, device tokens) is removed via CASCADE on User.delete().
    """
    email = (email or "").strip()
    otp = (otp or "").strip()

    if not otp:
        return False, "A verification code is required."

    user = User.objects.filter(email__iexact=email).first()
    if not user:
        return False, "Invalid or expired verification code."

    email = user.email
    otp_obj = (
        RegistrationOTP.objects.filter(
            email=email, is_verified=False, otp_code=otp
        )
        .order_by("-created_at")
        .first()
    )

    if not otp_obj:
        return False, "Invalid or expired verification code."

    if otp_obj.is_expired:
        return False, "Verification code has expired."

    otp_obj.is_verified = True
    otp_obj.verified_at = timezone.now()
    otp_obj.save(update_fields=["is_verified", "verified_at", "updated_at"])

    user.delete()
    RegistrationOTP.objects.filter(email=email).delete()
    PasswordResetOTP.objects.filter(email=email).delete()
    return True, None
