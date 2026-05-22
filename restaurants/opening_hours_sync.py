"""Sync OpeningSlot rows from Restaurant.opening_hours JSON."""

from datetime import datetime, time
from typing import Any

from .models import OpeningSlot, Restaurant

DAY_NAME_TO_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

CLOSED_MARKERS = frozenset({"", "closed", "close"})


def _parse_time(value: str) -> time | None:
    value = value.strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def parse_day_hours(day_value: Any) -> tuple[time | None, time | None, bool]:
    """
    Parse one day's hours from opening_hours JSON.

    Supports:
      - "11:00-23:00"
      - {"open": "09:00", "close": "22:00"} (also opening/closing keys)
      - "", null, "closed" -> closed
    """
    if day_value is None:
        return None, None, True

    if isinstance(day_value, str):
        normalized = day_value.strip().lower()
        if normalized in CLOSED_MARKERS:
            return None, None, True
        if "-" not in day_value:
            return None, None, True
        open_str, close_str = day_value.split("-", 1)
        opening = _parse_time(open_str)
        closing = _parse_time(close_str)
        if not opening or not closing or opening >= closing:
            return None, None, True
        return opening, closing, False

    if isinstance(day_value, dict):
        open_str = day_value.get("open") or day_value.get("opening") or ""
        close_str = day_value.get("close") or day_value.get("closing") or ""
        if not str(open_str).strip() or not str(close_str).strip():
            return None, None, True
        opening = _parse_time(str(open_str))
        closing = _parse_time(str(close_str))
        if not opening or not closing or opening >= closing:
            return None, None, True
        return opening, closing, False

    return None, None, True


def sync_opening_slots_from_opening_hours(
    restaurant: Restaurant,
    opening_hours: dict | None = None,
) -> int:
    """
    Create or update OpeningSlot rows from opening_hours.

    Returns the number of days synced.
    """
    hours = opening_hours if opening_hours is not None else (restaurant.opening_hours or {})
    if not hours:
        return 0

    synced = 0
    for day_name, day_value in hours.items():
        day_key = str(day_name).strip().lower()
        day_index = DAY_NAME_TO_INDEX.get(day_key)
        if day_index is None:
            continue

        opening, closing, is_closed = parse_day_hours(day_value)
        if is_closed:
            defaults = {
                "opening_time": time(0, 0),
                "closing_time": time(0, 0),
                "is_closed": True,
            }
        else:
            defaults = {
                "opening_time": opening,
                "closing_time": closing,
                "is_closed": False,
            }

        OpeningSlot.objects.update_or_create(
            restaurant=restaurant,
            day_of_week=day_index,
            defaults=defaults,
        )
        synced += 1

    return synced
