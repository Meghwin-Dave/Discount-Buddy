"""Throttles for unauthenticated auth/OTP endpoints.

Per-IP limits slow bulk abuse; per-email limits are what actually stop OTP
guessing, since the 4-digit codes are only safe if guesses are scarce.
"""
import hashlib

from rest_framework.exceptions import Throttled
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle
from rest_framework.views import exception_handler


class AuthIPThrottle(AnonRateThrottle):
    """Per-IP limit for login / registration / reset entry points."""

    scope = "auth_ip"


class UsernameCheckThrottle(AnonRateThrottle):
    scope = "username_check"


class PartnerRequestThrottle(AnonRateThrottle):
    scope = "partner_request"


class _EmailThrottle(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        email = request.data.get("email") if hasattr(request.data, "get") else None
        if not email and request.user and request.user.is_authenticated:
            email = request.user.email
        if not email or not isinstance(email, str):
            return None  # nothing to key on; the IP throttle still applies
        digest = hashlib.sha256(email.strip().lower().encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": digest}


class OTPVerifyEmailThrottle(_EmailThrottle):
    """Caps OTP guesses per email (applies to verify/complete/confirm/delete)."""

    scope = "otp_verify"


class OTPSendEmailThrottle(_EmailThrottle):
    """Caps OTP emails per address (blocks mail-bombing and code re-rolling)."""

    scope = "otp_send"


def friendly_exception_handler(exc, context):
    """DRF's default handler, with a human 429 message.

    The mobile app shows the response's `detail` string verbatim, so the
    default "Expected available in 3412 seconds." would be shown to users.
    """
    response = exception_handler(exc, context)
    if response is not None and isinstance(exc, Throttled):
        wait = exc.wait or 0
        minutes = max(1, -(-int(wait) // 60))
        unit = "minute" if minutes == 1 else "minutes"
        response.data = {
            "detail": f"Too many attempts. Please try again in {minutes} {unit}."
        }
    return response
