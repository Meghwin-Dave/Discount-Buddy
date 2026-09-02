"""Sync OpeningSlot rows from Restaurant.opening_hours JSON."""

from datetime import datetime, time
from typing import Any

from django.db import transaction

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

# Separators allowed between multiple windows inside a single string value,
# so "11:00-15:00, 19:00-22:45" authors two slots.
RANGE_SEPARATORS = (",", ";", "&", "|")


def _parse_time(value: str) -> time | None:
    value = value.strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def _parse_single_range(value: Any) -> tuple[time, time] | None:
    """Parse one window from either ``"11:00-15:00"`` or ``{"open":..., "close":...}``."""
    if isinstance(value, dict):
        open_str = value.get("open") or value.get("opening") or ""
        close_str = value.get("close") or value.get("closing") or ""
        opening = _parse_time(str(open_str))
        closing = _parse_time(str(close_str))
    elif isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in CLOSED_MARKERS or "-" not in value:
            return None
        open_str, close_str = value.split("-", 1)
        opening = _parse_time(open_str)
        closing = _parse_time(close_str)
    else:
        return None

    if opening is None or closing is None:
        return None
    return opening, closing


def _split_range_string(value: str) -> list[str]:
    parts = [value]
    for separator in RANGE_SEPARATORS:
        parts = [chunk for part in parts for chunk in part.split(separator)]
    return [part for part in (chunk.strip() for chunk in parts) if part]


def parse_day_ranges(day_value: Any) -> list[tuple[time, time]]:
    """
    Parse every opening window for one day.

    Supports, in addition to the original single-window formats:
      - ``["11:00-15:00", "19:00-22:45"]``
      - ``[{"open": "11:00", "close": "15:00"}, {"open": "19:00", "close": "22:45"}]``
      - ``"11:00-15:00, 19:00-22:45"``

    A window whose closing time precedes its opening time crosses midnight and is
    kept as-is; equal times mean open all day. Returns an empty list when closed.
    """
    if day_value is None:
        return []

    if isinstance(day_value, str):
        candidates: list[Any] = _split_range_string(day_value)
    elif isinstance(day_value, (list, tuple)):
        candidates = list(day_value)
    else:
        candidates = [day_value]

    ranges: list[tuple[time, time]] = []
    for candidate in candidates:
        parsed = _parse_single_range(candidate)
        if parsed and parsed not in ranges:
            ranges.append(parsed)

    return sorted(ranges, key=lambda window: window[0])


def parse_day_hours(day_value: Any) -> tuple[time | None, time | None, bool]:
    """
    Parse one day's hours, returning only the first window.

    Retained for callers that predate split shifts; prefer :func:`parse_day_ranges`.
    """
    ranges = parse_day_ranges(day_value)
    if not ranges:
        return None, None, True
    opening, closing = ranges[0]
    return opening, closing, False


def sync_opening_slots_from_opening_hours(
    restaurant: Restaurant,
    opening_hours: dict | None = None,
) -> int:
    """
    Replace OpeningSlot rows for every day present in opening_hours.

    Days are rewritten wholesale rather than updated in place because a day can
    now map to several slots. Days absent from the JSON are left untouched.

    Returns the number of days synced.
    """
    hours = opening_hours if opening_hours is not None else (restaurant.opening_hours or {})
    if not hours:
        return 0

    synced = 0
    with transaction.atomic():
        for day_name, day_value in hours.items():
            day_key = str(day_name).strip().lower()
            day_index = DAY_NAME_TO_INDEX.get(day_key)
            if day_index is None:
                continue

            ranges = parse_day_ranges(day_value)
            OpeningSlot.objects.filter(
                restaurant=restaurant, day_of_week=day_index
            ).delete()

            if ranges:
                OpeningSlot.objects.bulk_create(
                    [
                        OpeningSlot(
                            restaurant=restaurant,
                            day_of_week=day_index,
                            opening_time=opening,
                            closing_time=closing,
                            is_closed=False,
                        )
                        for opening, closing in ranges
                    ]
                )
            else:
                OpeningSlot.objects.create(
                    restaurant=restaurant,
                    day_of_week=day_index,
                    opening_time=time(0, 0),
                    closing_time=time(0, 0),
                    is_closed=True,
                )

            synced += 1

    return synced
