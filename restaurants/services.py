import math
import random
from dataclasses import dataclass
from io import BytesIO

import qrcode
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.utils import timezone

from decimal import Decimal
from .models import Deal, DealUse, Restaurant, UserRestaurantLoyalty, LoyaltyRedemptionRecord
from users.models import User


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula (in km)"""
    try:
        if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
            return None
        
        # Convert to float just in case they are Decimals or strings
        f_lat1, f_lon1, f_lat2, f_lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
        
        R = 6371  # Earth's radius in kilometers
        dlat = math.radians(f_lat2 - f_lat1)
        dlon = math.radians(f_lon2 - f_lon1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(f_lat1)) * math.cos(math.radians(f_lat2)) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))
        result = R * c
        # print(f"DEBUG: calculate_distance inputs({lat1}, {lon1}, {lat2}, {lon2}) -> {result}")
        return result
    except (ValueError, TypeError) as e:
        # print(f"DEBUG: calculate_distance error: {e}")
        return None


def km_to_miles(km):
    """Convert kilometers to miles"""
    if km is None:
        return None
    return km * 0.621371


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
class LoyaltyUpdateResult:
    loyalty: UserRestaurantLoyalty | None = None
    reward_just_earned: bool = False


def build_loyalty_progress_payload(
    *, restaurant: Restaurant, loyalty: UserRestaurantLoyalty | None
) -> dict | None:
    """Build a customer-facing loyalty progress dict for API responses."""
    if not restaurant.loyalty_card_enabled:
        return None

    required = restaurant.loyalty_required_redemptions or 0
    completed = loyalty.current_cycle_redemptions if loyalty else 0
    remaining = max(required - completed, 0) if required else 0
    progress_percentage = (
        round((completed / required) * 100, 1) if required else 0.0
    )

    payload = {
        "loyalty_card_enabled": True,
        "required_redemptions": required,
        "reward_description": restaurant.loyalty_reward_description,
        "completed_redemptions": completed,
        "remaining_redemptions": remaining,
        "progress_text": f"{completed} of {required} redemptions completed" if required else "",
        "progress_percentage": progress_percentage,
        "is_reward_eligible": loyalty.is_reward_eligible if loyalty else False,
        "reward_eligible_at": (
            loyalty.reward_eligible_at.isoformat() if loyalty and loyalty.reward_eligible_at else None
        ),
        "total_lifetime_redemptions": loyalty.total_lifetime_redemptions if loyalty else 0,
        "rewards_earned": loyalty.rewards_earned if loyalty else 0,
        "last_reward_claimed_at": (
            loyalty.last_reward_claimed_at.isoformat() if loyalty and loyalty.last_reward_claimed_at else None
        ),
    }
    return payload


@transaction.atomic
def update_loyalty_on_redemption(*, deal_use: DealUse) -> LoyaltyUpdateResult:
    """
    Increment loyalty progress when a deal is successfully redeemed.
    Creates audit records and awards eligibility when the threshold is reached.
    """
    restaurant = deal_use.deal.restaurant
    if not restaurant.loyalty_card_enabled or not restaurant.loyalty_required_redemptions:
        return LoyaltyUpdateResult()

    required = restaurant.loyalty_required_redemptions
    user = deal_use.user

    loyalty, _ = UserRestaurantLoyalty.objects.select_for_update().get_or_create(
        user=user,
        restaurant=restaurant,
        defaults={
            "current_cycle_redemptions": 0,
            "total_lifetime_redemptions": 0,
        },
    )

    # Skip if this deal_use was already counted (idempotency guard).
    if LoyaltyRedemptionRecord.objects.filter(
        deal_use=deal_use,
        status=LoyaltyRedemptionRecord.STATUS_COUNTED,
    ).exists():
        return LoyaltyUpdateResult(loyalty=loyalty)

    loyalty.current_cycle_redemptions += 1
    loyalty.total_lifetime_redemptions += 1
    reward_just_earned = False

    record_status = LoyaltyRedemptionRecord.STATUS_COUNTED
    if loyalty.current_cycle_redemptions >= required and not loyalty.is_reward_eligible:
        loyalty.is_reward_eligible = True
        loyalty.reward_eligible_at = timezone.now()
        record_status = LoyaltyRedemptionRecord.STATUS_REWARD_EARNED
        reward_just_earned = True

    loyalty.save(
        update_fields=[
            "current_cycle_redemptions",
            "total_lifetime_redemptions",
            "is_reward_eligible",
            "reward_eligible_at",
            "updated_at",
        ]
    )

    LoyaltyRedemptionRecord.objects.create(
        user=user,
        restaurant=restaurant,
        deal_use=deal_use,
        status=record_status,
        cycle_redemption_number=loyalty.current_cycle_redemptions,
        total_lifetime_redemptions=loyalty.total_lifetime_redemptions,
    )

    return LoyaltyUpdateResult(loyalty=loyalty, reward_just_earned=reward_just_earned)


@transaction.atomic
def claim_loyalty_reward(
    *, actor: User, restaurant: Restaurant, customer_user: User
) -> tuple[bool, str, UserRestaurantLoyalty | None]:
    """
    Mark a customer's loyalty reward as claimed (merchant action).
    Resets the current cycle, carrying over excess redemptions if any.
    """
    if not restaurant.loyalty_card_enabled:
        return False, "Loyalty card is not enabled for this restaurant.", None

    required = restaurant.loyalty_required_redemptions
    if not required:
        return False, "Loyalty card is not configured for this restaurant.", None

    owns_restaurant = False
    if hasattr(actor, "restaurant_profile") and actor.restaurant_profile.restaurant_id == restaurant.id:
        owns_restaurant = True
    elif hasattr(actor, "merchant") and restaurant.merchant_id == actor.merchant.id:
        owns_restaurant = True

    if not owns_restaurant:
        return False, "You are not allowed to manage loyalty for this restaurant.", None

    try:
        loyalty = UserRestaurantLoyalty.objects.select_for_update().get(
            user=customer_user,
            restaurant=restaurant,
        )
    except UserRestaurantLoyalty.DoesNotExist:
        return False, "No loyalty record found for this customer.", None

    if not loyalty.is_reward_eligible:
        return False, "This customer is not eligible for a loyalty reward.", None

    excess = loyalty.current_cycle_redemptions - required
    loyalty.current_cycle_redemptions = max(excess, 0)
    loyalty.is_reward_eligible = False
    loyalty.rewards_earned += 1
    loyalty.last_reward_claimed_at = timezone.now()
    loyalty.reward_eligible_at = None
    loyalty.save(
        update_fields=[
            "current_cycle_redemptions",
            "is_reward_eligible",
            "rewards_earned",
            "last_reward_claimed_at",
            "reward_eligible_at",
            "updated_at",
        ]
    )

    LoyaltyRedemptionRecord.objects.create(
        user=customer_user,
        restaurant=restaurant,
        deal_use=None,
        status=LoyaltyRedemptionRecord.STATUS_REWARD_CLAIMED,
        cycle_redemption_number=loyalty.current_cycle_redemptions,
        total_lifetime_redemptions=loyalty.total_lifetime_redemptions,
        notes=f"Reward claimed by {actor.email}",
    )

    # Re-check eligibility if excess redemptions already meet threshold.
    if loyalty.current_cycle_redemptions >= required:
        loyalty.is_reward_eligible = True
        loyalty.reward_eligible_at = timezone.now()
        loyalty.save(update_fields=["is_reward_eligible", "reward_eligible_at", "updated_at"])

    return True, "Loyalty reward claimed successfully.", loyalty


@dataclass
class RedemptionResult:
    success: bool
    reason: str
    deal_use: DealUse | None = None
    loyalty_result: LoyaltyUpdateResult | None = None


@transaction.atomic
def redeem_deal(
    *,
    actor: User,
    redemption_code: str | None = None,
    qr_data: str | None = None,
    price: float | None = None,
    people_count: int | None = None,
    restaurant_id: int | None = None,
) -> RedemptionResult:
    """
    Redeem a deal either by 6-digit code or by QR payload.

    Validates:
    - redemption exists
    - not already redeemed
    - deal is still active
    - actor owns the restaurant for which the deal applies
    - (Optional) restaurant_id matches the deal's restaurant
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

    # Validate restaurant_id if provided
    if restaurant_id and restaurant.id != int(restaurant_id):
        return RedemptionResult(False, f"This deal belongs to '{restaurant.name}' and cannot be redeemed at the selected restaurant.", deal_use)

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
    
    if price is not None:
        price_dec = Decimal(str(price))
        deal_use.price = price_dec
        
        # Calculate discount breakdown
        discount_amount_saved = Decimal("0.00")
        final_bill_amount = price_dec
        
        if deal.deal_type == Deal.DEAL_TYPE_PERCENTAGE:
            if deal.discount_percentage:
                discount_amount_saved = price_dec * (Decimal(str(deal.discount_percentage)) / Decimal("100"))
                final_bill_amount = price_dec - discount_amount_saved
        elif deal.deal_type == Deal.DEAL_TYPE_FIXED:
            if deal.discount_amount:
                discount_amount_saved = min(price_dec, Decimal(str(deal.discount_amount)))
                final_bill_amount = price_dec - discount_amount_saved
        elif deal.deal_type == Deal.DEAL_TYPE_TWO_FOR_ONE:
            # Assume 50% discount if 2 or more people
            p_count = people_count or deal_use.people_count or 1
            if p_count >= 2:
                discount_amount_saved = price_dec / Decimal("2")
                final_bill_amount = price_dec - discount_amount_saved
        elif deal.deal_type == Deal.DEAL_TYPE_COMBO:
            # Combo deals have a fixed price, savings aren't easily calculated 
            # without a base price, so we just track it.
            discount_amount_saved = Decimal("0.00")
            # If the user enters the bill, we don't automatically subtract anything 
            # because the 'price' entered is usually the final bill already.
            final_bill_amount = price_dec
        
        deal_use.discount_amount_saved = discount_amount_saved
        deal_use.final_bill_amount = final_bill_amount

    if people_count is not None:
        deal_use.people_count = people_count
        
    deal_use.save(update_fields=[
        "is_redeemed", "redeemed_at", "redeemed_by", 
        "restaurant_confirmed", "price", "people_count", 
        "discount_amount_saved", "final_bill_amount", "updated_at"
    ])

    loyalty_result = update_loyalty_on_redemption(deal_use=deal_use)

    return RedemptionResult(True, "Deal redeemed successfully.", deal_use, loyalty_result)


