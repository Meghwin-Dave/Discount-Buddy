"""
Shared datetime formatting helpers for user-facing copy.

Datetimes are stored in UTC. Anything a human reads (push notification bodies,
emails, opening hours labels) must be rendered in the display timezone from
``settings.TIME_ZONE``, while anything a client parses must stay ISO-8601 UTC.
"""
from __future__ import annotations

from datetime import date, datetime, time, timezone as dt_timezone

from django.utils import timezone
from django.utils.dateparse import parse_datetime


def coerce_datetime(value: datetime | str | None) -> datetime | None:
    """Return an aware datetime for a datetime or ISO string, or None if unparseable."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = parse_datetime(value)
        if parsed is None:
            return None
    else:
        return None

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_default_timezone())
    return parsed


def to_local(value: datetime | str | None) -> datetime | None:
    """Convert to the display timezone declared in settings.TIME_ZONE."""
    parsed = coerce_datetime(value)
    return timezone.localtime(parsed) if parsed is not None else None


def to_iso_utc(value: datetime | str | None) -> str:
    """
    Serialise to ISO-8601 UTC for machine consumers that need an absolute instant.

    Prefer [to_iso_local] for booking times in push payloads — restaurant
    reservations are wall-clock appointments, not device-local instants.
    """
    parsed = coerce_datetime(value)
    if parsed is None:
        return str(value) if value is not None else ""
    return parsed.astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z")


def to_iso_local(value: datetime | str | None) -> str:
    """
    Serialise to ISO-8601 in ``settings.TIME_ZONE`` with offset, e.g.
    ``2026-09-09T17:00:00+01:00``.

    Mobile clients should read the hour/minute from this string directly rather
    than converting the instant to the device timezone (which would show 21:30
    IST for a 17:00 London table).
    """
    parsed = coerce_datetime(value)
    if parsed is None:
        return str(value) if value is not None else ""
    return timezone.localtime(parsed).isoformat()


def format_clock_label(value: time | datetime | None) -> str:
    """
    Google-style compact clock label: ``3 pm``, ``10:45 pm``, ``12 am``.

    Minutes are omitted on the hour, which is what makes "Closes 3 pm" read naturally.
    """
    if isinstance(value, datetime):
        value = value.time()
    if not isinstance(value, time):
        return ""

    hour = value.hour % 12 or 12
    meridiem = "am" if value.hour < 12 else "pm"
    if value.minute:
        return f"{hour}:{value.minute:02d} {meridiem}"
    return f"{hour} {meridiem}"


def format_time_range(start: time, end: time) -> str:
    """
    Render a single opening window the way Google Maps does.

    The meridiem is dropped from the start time when both ends share it, giving
    ``7\u201310:45 pm`` rather than ``7 pm\u201310:45 pm``, while ``11 am\u20133 pm`` keeps both.
    """
    start_label = format_clock_label(start)
    end_label = format_clock_label(end)

    same_meridiem = (start.hour < 12) == (end.hour < 12)
    if same_meridiem:
        start_label = start_label.removesuffix(" am").removesuffix(" pm")

    return f"{start_label}\u2013{end_label}"


def format_datetime_label(value: datetime | str | None) -> str:
    """
    Human booking datetime in the display timezone, e.g. ``August 26, 2026 at 8:30 PM``.

    Falls back to the raw value so a formatting failure can never block a notification.
    """
    local = to_local(value)
    if local is None:
        return str(value) if value is not None else ""

    hour = local.hour % 12 or 12
    meridiem = "AM" if local.hour < 12 else "PM"
    return f"{local:%B} {local.day}, {local.year} at {hour}:{local:%M} {meridiem}"


def format_date_label(value: date | datetime | str | None) -> str:
    """Human date in the display timezone, e.g. ``August 26, 2026``."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return f"{value:%B} {value.day}, {value.year}"

    local = to_local(value)
    if local is None:
        return str(value) if value is not None else ""
    return f"{local:%B} {local.day}, {local.year}"
