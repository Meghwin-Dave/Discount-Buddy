import random
from dataclasses import dataclass
from io import BytesIO

import qrcode
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Deal, DealUse, Restaurant
from users.models import User


def _generate_six_digit_code() -> str:
    """Generate a random 6‑digit numeric code as a zero-padded string."""
    return f"{random.randint(0, 999999):06d}"


def _generate_unique_redemption_code() -> str:
    """
    Generate a collision-safe 6-digit code.

    Rely on the DB unique constraint on DealUse.redemption_code to guard against
    race conditions; this function just minimizes collisions.
    """
    # In practice collisions are extremely unlikely; we still loop defensively.
    for _ in range(10):
        code = _generate_six_digit_code()
        if not DealUse.objects.filter(redemption_code=code).exists():
            return code
    # Fallback: just return a random code and let the DB enforce uniqueness.
    return _generate_six_digit_code()


def _build_qr_image(payload: str) -> ContentFile:
    """Generate a PNG QR code image for the given payload."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return ContentFile(buffer.read(), name="qr.png")


@transaction.atomic
def create_deal_use_with_redemption(
    *, user: User, deal: Deal, notes: str | None = ""
) -> DealUse:
    """
    Create a DealUse record for a user/deal pair, assigning a unique
    6-digit redemption code and generating a QR code image.

    Also increments the Deal.used_count atomically.
    """
    # Create the DealUse with a unique redemption code, retrying on collisions.
    while True:
        redemption_code = _generate_unique_redemption_code()
        try:
            deal_use = DealUse.objects.create(
                user=user,
                deal=deal,
                notes=notes or "",
                redemption_code=redemption_code,
            )
            break
        except IntegrityError:
            # Very unlikely: another row grabbed the same code at the same time.
            continue

    # Encode a stable payload that the restaurant app can scan and send back.
    # Format: DEALUSE:<id>:<code>
    qr_payload = f"DEALUSE:{deal_use.id}:{deal_use.redemption_code}"
    qr_file = _build_qr_image(qr_payload)
    deal_use.qr_code.save(qr_file.name, qr_file, save=True)

    # Increment used_count atomically.
    from django.db.models import F

    Deal.objects.filter(pk=deal.pk).update(used_count=F("used_count") + 1)

    # Refresh used_count on the instance if needed by callers.
    deal.refresh_from_db(fields=["used_count"])

    return deal_use


@dataclass
class RedemptionResult:
    success: bool
    reason: str
    deal_use: DealUse | None = None


@transaction.atomic
def redeem_deal(
    *,
    actor: User,
    redemption_code: str | None = None,
    qr_data: str | None = None,
) -> RedemptionResult:
    """
    Redeem a deal either by 6-digit code or by QR payload.

    Validates:
    - redemption exists
    - not already redeemed
    - deal is still active
    - actor owns the restaurant for which the deal applies
    """
    if not redemption_code and not qr_data:
        return RedemptionResult(False, "Either redemption_code or qr_data is required.")

    # Locate the DealUse row and lock it to avoid double redemption.
    try:
        if qr_data:
            # Expecting payload of the form DEALUSE:<id>:<code>
            parts = qr_data.split(":")
            if len(parts) != 3 or parts[0] != "DEALUSE":
                return RedemptionResult(False, "Invalid QR data format.")
            _, id_str, code = parts
            deal_use = (
                DealUse.objects.select_for_update()
                .select_related("deal", "deal__restaurant", "user")
                .get(id=int(id_str), redemption_code=code)
            )
        else:
            deal_use = (
                DealUse.objects.select_for_update()
                .select_related("deal", "deal__restaurant", "user")
                .get(redemption_code=redemption_code)
            )
    except (ValueError, DealUse.DoesNotExist):
        return RedemptionResult(False, "Redemption not found.")

    # Already redeemed?
    if deal_use.is_redeemed:
        return RedemptionResult(False, "This deal has already been redeemed.", deal_use)

    deal = deal_use.deal

    # Deal still valid?
    if not deal.is_active_now():
        return RedemptionResult(False, "This deal is no longer valid.", deal_use)

    # Verify that the actor is allowed to redeem for this restaurant.
    restaurant: Restaurant = deal.restaurant

    # The actor can be either:
    # - a user linked via RestaurantProfile
    # - a merchant user owning the restaurant via vouchers.Merchant
    owns_restaurant = False
    if hasattr(actor, "restaurant_profile") and actor.restaurant_profile.restaurant_id == restaurant.id:
        owns_restaurant = True
    elif hasattr(actor, "merchant") and restaurant.merchant_id == actor.merchant.id:
        owns_restaurant = True

    if not owns_restaurant:
        return RedemptionResult(False, "You are not allowed to redeem deals for this restaurant.", deal_use)

    # Mark as redeemed atomically.
    deal_use.is_redeemed = True
    deal_use.redeemed_at = timezone.now()
    deal_use.redeemed_by = actor
    deal_use.restaurant_confirmed = True
    deal_use.save(update_fields=["is_redeemed", "redeemed_at", "redeemed_by", "restaurant_confirmed", "updated_at"])

    return RedemptionResult(True, "Deal redeemed successfully.", deal_use)


