"""
Google-Maps-style opening hours evaluation.

A restaurant can have any number of :class:`~restaurants.models.OpeningSlot` rows
per weekday, which is what makes split shifts ("11 am-3 pm, 7-10:45 pm") possible.
This module turns those rows into the single status line the apps render, e.g.
``Open . Closes 3 pm``.

Two edge cases drive most of the logic here:

* A slot whose ``closing_time`` is not after its ``opening_time`` crosses midnight,
  so "is it open now" has to consider yesterday's slots as well as today's.
* A slot whose ``opening_time`` equals its ``closing_time`` means open all day.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta

from django.utils import timezone

from core.utils.datetime_format import format_clock_label, format_time_range, to_iso_utc

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_ABBREVIATIONS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# How close to closing time before the status downgrades to "Closes soon".
CLOSING_SOON = timedelta(minutes=30)

STATE_OPEN = "open"
STATE_CLOSING_SOON = "closing_soon"
STATE_CLOSED = "closed"


def spans_midnight(slot) -> bool:
    """True when the slot runs past midnight into the following day."""
    return not slot.is_open_all_day and slot.closing_time < slot.opening_time


def is_open_all_day(slot) -> bool:
    """A slot with identical open and close times is treated as 24 hours."""
    return slot.opening_time == slot.closing_time


def slot_contains(slot, moment: time, *, started_yesterday: bool = False) -> bool:
    """
    Whether ``moment`` falls inside this slot's window.

    ``started_yesterday`` evaluates only the portion of an overnight slot that
    spills past midnight, which is how a Tuesday 22:00-02:00 slot can keep a
    restaurant open at 00:30 on Wednesday.
    """
    if slot.is_closed:
        return False
    if slot.is_open_all_day:
        return not started_yesterday

    if slot.spans_midnight:
        if started_yesterday:
            return moment < slot.closing_time
        return moment >= slot.opening_time

    if started_yesterday:
        return False
    return slot.opening_time <= moment < slot.closing_time


def _to_minutes(value: time) -> int:
    return value.hour * 60 + value.minute


def _as_intervals(opening: time, closing: time) -> list[tuple[int, int]]:
    """
    Express a window as minute intervals within a single day.

    An overnight window is split in two so it can be compared on a flat timeline,
    and an all-day window covers the whole range.
    """
    start, end = _to_minutes(opening), _to_minutes(closing)
    if start == end:
        return [(0, 24 * 60)]
    if end < start:
        return [(start, 24 * 60), (0, end)]
    return [(start, end)]


def windows_overlap(a_open: time, a_close: time, b_open: time, b_close: time) -> bool:
    """Whether two opening windows on the same weekday intersect."""
    return any(
        a_start < b_end and b_start < a_end
        for a_start, a_end in _as_intervals(a_open, a_close)
        for b_start, b_end in _as_intervals(b_open, b_close)
    )


def _bookable_slots(slots) -> list:
    return [slot for slot in slots if not slot.is_closed]


def _slots_for_day(slots, day_of_week: int) -> list:
    return sorted(
        (slot for slot in _bookable_slots(slots) if slot.day_of_week == day_of_week),
        key=lambda slot: slot.opening_time,
    )


def find_active_slot(slots, now_local: datetime):
    """Return the slot currently in progress, or None when closed."""
    moment = now_local.time()
    today = now_local.weekday()
    yesterday = (today - 1) % 7

    for slot in _slots_for_day(slots, today):
        if slot_contains(slot, moment):
            return slot

    for slot in _slots_for_day(slots, yesterday):
        if slot_contains(slot, moment, started_yesterday=True):
            return slot

    return None


def find_next_slot(slots, now_local: datetime) -> tuple[object, datetime] | None:
    """
    Return the next slot that opens and the local datetime it opens at.

    Searches the coming week so a restaurant open only on weekends still reports
    a sensible "Opens 11 am Sat".
    """
    moment = now_local.time()
    today = now_local.weekday()

    for slot in _slots_for_day(slots, today):
        if slot.opening_time > moment:
            return slot, datetime.combine(now_local.date(), slot.opening_time, tzinfo=now_local.tzinfo)

    for offset in range(1, 8):
        day = (today + offset) % 7
        day_slots = _slots_for_day(slots, day)
        if day_slots:
            slot = day_slots[0]
            opens_on = now_local.date() + timedelta(days=offset)
            return slot, datetime.combine(opens_on, slot.opening_time, tzinfo=now_local.tzinfo)

    return None


def _closing_datetime(slot, now_local: datetime) -> datetime:
    """Local datetime at which the in-progress slot ends."""
    if slot.is_open_all_day:
        return datetime.combine(
            now_local.date() + timedelta(days=1), time(0, 0), tzinfo=now_local.tzinfo
        )

    closes_on = now_local.date()
    if slot.spans_midnight and now_local.time() >= slot.opening_time:
        closes_on += timedelta(days=1)
    return datetime.combine(closes_on, slot.closing_time, tzinfo=now_local.tzinfo)


def _opens_suffix(opens_at: datetime, now_local: datetime) -> str:
    """``Opens 7 pm`` for today, ``Opens 11 am Thu`` for any later day."""
    label = f"Opens {format_clock_label(opens_at.time())}"
    if opens_at.date() != now_local.date():
        label = f"{label} {DAY_ABBREVIATIONS[opens_at.weekday()]}"
    return label


def build_opening_status(slots, now=None) -> dict | None:
    """
    Build the status line shown next to a restaurant name.

    Returns None when the restaurant has no usable hours, so clients can hide the
    row entirely rather than render a misleading "Closed".
    """
    slots = list(slots)
    if not _bookable_slots(slots):
        return None

    now_local = timezone.localtime(now or timezone.now())
    active = find_active_slot(slots, now_local)
    upcoming = find_next_slot(slots, now_local)

    if active is not None:
        if active.is_open_all_day:
            return {
                "is_open": True,
                "state": STATE_OPEN,
                "short_label": "Open 24 hours",
                "detail": "",
                "label": "Open 24 hours",
                "open_24_hours": True,
                "next_change_at": None,
            }

        closes_at = _closing_datetime(active, now_local)
        detail = f"Closes {format_clock_label(active.closing_time)}"
        closing_soon = closes_at - now_local <= CLOSING_SOON
        short_label = "Closes soon" if closing_soon else "Open"

        return {
            "is_open": True,
            "state": STATE_CLOSING_SOON if closing_soon else STATE_OPEN,
            "short_label": short_label,
            "detail": detail,
            "label": f"{short_label} \u00b7 {detail}",
            "open_24_hours": False,
            "next_change_at": to_iso_utc(closes_at),
        }

    if upcoming is None:
        return {
            "is_open": False,
            "state": STATE_CLOSED,
            "short_label": "Closed",
            "detail": "",
            "label": "Closed",
            "open_24_hours": False,
            "next_change_at": None,
        }

    _, opens_at = upcoming
    detail = _opens_suffix(opens_at, now_local)
    return {
        "is_open": False,
        "state": STATE_CLOSED,
        "short_label": "Closed",
        "detail": detail,
        "label": f"Closed \u00b7 {detail}",
        "open_24_hours": False,
        "next_change_at": to_iso_utc(opens_at),
    }


def build_weekly_hours(slots, now=None) -> list[dict]:
    """
    Group slots into one entry per weekday for the detail screen.

    Days are ordered starting from today to match how Google Maps presents the
    week, and each day carries its ranges already formatted for display.
    """
    slots = list(slots)
    now_local = timezone.localtime(now or timezone.now())
    today = now_local.weekday()

    week = []
    for offset in range(7):
        day = (today + offset) % 7
        day_slots = _slots_for_day(slots, day)

        if not day_slots:
            ranges, label = [], "Closed"
        elif len(day_slots) == 1 and day_slots[0].is_open_all_day:
            ranges, label = ["Open 24 hours"], "Open 24 hours"
        else:
            ranges = [
                format_time_range(slot.opening_time, slot.closing_time) for slot in day_slots
            ]
            label = ", ".join(ranges)

        week.append(
            {
                "day_of_week": day,
                "day_name": DAY_NAMES[day],
                "day_short": DAY_ABBREVIATIONS[day],
                "is_today": offset == 0,
                "is_closed": not day_slots,
                "ranges": ranges,
                "label": label,
            }
        )

    return week
