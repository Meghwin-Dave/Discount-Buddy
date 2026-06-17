from datetime import timedelta

from celery import shared_task
from django.db.models import Max
from django.utils import timezone

from users.models import UserProfile
from .models import Restaurant, MysteryVisit, Booking


@shared_task
def assign_monthly_mystery_visits():
    """
    Periodic task to ensure each active restaurant has at least one
    scheduled mystery visit within its configured required_visit_gap.

    - Picks from users with ROLE_MYSTERY_GUEST
    - Skips restaurants with no eligible guests configured
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    now = timezone.now()

    guests = User.objects.filter(profile__role=UserProfile.ROLE_MYSTERY_GUEST).order_by(
        "id"
    )
    if not guests.exists():
        return

    guest_cycle = list(guests)
    guest_index = 0

    restaurants = Restaurant.objects.filter(is_active=True, verified=True)

    for restaurant in restaurants:
        gap_days = restaurant.required_visit_gap or 30
        cutoff = now - timedelta(days=gap_days)

        # Last submitted or scheduled visit
        last_visit_info = (
            MysteryVisit.objects.filter(restaurant=restaurant)
            .aggregate(last_date=Max("scheduled_for"))
        )
        last_date = last_visit_info["last_date"]

        if last_date and last_date > cutoff:
            continue  # already within required_visit_gap

        # Assign next visit for upcoming week
        scheduled_for = now + timedelta(days=7)
        guest = guest_cycle[guest_index]
        guest_index = (guest_index + 1) % len(guest_cycle)

        MysteryVisit.objects.create(
            restaurant=restaurant,
            mystery_guest=guest,
            scheduled_for=scheduled_for,
        )


@shared_task
def send_booking_reminders():
    """
    Send 1-hour reminders to merchants for upcoming confirmed bookings.

    Runs periodically (every 5 minutes) and targets bookings whose
    booking_date falls between 50 and 60 minutes from now.
    """
    from notifications.services import NotificationService

    now = timezone.now()
    window_start = now + timedelta(minutes=50)
    window_end = now + timedelta(minutes=60)

    bookings = (
        Booking.objects.filter(
            status=Booking.STATUS_CONFIRMED,
            reminder_sent=False,
            booking_date__gte=window_start,
            booking_date__lte=window_end,
        )
        .select_related("restaurant", "user")
    )

    for booking in bookings:
        try:
            NotificationService.notify_merchant_booking_reminder(booking)
            booking.reminder_sent = True
            booking.save(update_fields=["reminder_sent", "updated_at"])
        except Exception:
            continue

