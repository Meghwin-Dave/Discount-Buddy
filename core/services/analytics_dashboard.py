from datetime import datetime, time, timedelta

from django.core.cache import cache
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date

from configs.models import SpinToWinCampaign
from restaurants.models import Booking, DealClickLog, DealUse, Restaurant, RestaurantViewLog, SavedRestaurant

from .google_analytics import GoogleAnalyticsService

HISTORICAL_CACHE_SECONDS = 600
REALTIME_CACHE_SECONDS = 45

BEHAVIOUR_EVENTS = {
    "restaurant_views": "restaurant_viewed",
    "deal_views": "deal_viewed",
    "redeem_started": "redeem_started",
    "booking_started": "booking_started",
    "first_opens": "first_open",
    "android_app_removes": "app_remove",
}

ENGAGEMENT_EVENTS = [
    ("restaurant_viewed", "Restaurant views"),
    ("restaurant_favorited", "Favourites"),
    ("deal_viewed", "Deal views"),
    ("redeem_started", "Redeems started"),
    ("deal_redeemed", "Deals redeemed"),
    ("booking_started", "Bookings started"),
    ("booking_created", "Bookings created"),
    ("booking_cancelled", "Bookings cancelled"),
    ("loyalty_card_viewed", "Loyalty cards viewed"),
    ("stamp_collected", "Stamps collected"),
    ("reward_redeemed", "Rewards redeemed"),
    ("notification_open", "Notifications opened"),
    ("spin_started", "Spins started"),
    ("spin_completed", "Spins completed"),
    ("search", "Searches"),
    ("sign_up", "Sign ups"),
    ("login", "Logins"),
    ("first_open", "First opens"),
    ("app_remove", "Android app removes"),
]

# Parameters actually sent from Flutter (see DiscountBuddy docs/ANALYTICS_IMPLEMENTATION.md).
# Login/sign_up track method only — not username (no PII).
EVENT_DETAIL_SPECS = {
    "login": {"dimensions": ["method", "customEvent:method"]},
    "sign_up": {"dimensions": ["method", "customEvent:method"]},
    "search": {"dimensions": ["searchTerm", "customEvent:search_term"]},
    "restaurant_viewed": {
        "dimensions": ["customEvent:restaurant_name", "customEvent:restaurant_id"],
        "resolve": "restaurant",
    },
    "restaurant_favorited": {
        "dimensions": ["customEvent:restaurant_id"],
        "resolve": "restaurant",
    },
    "deal_viewed": {
        "dimensions": ["customEvent:restaurant_id"],
        "resolve": "restaurant",
    },
    "redeem_started": {
        "dimensions": ["customEvent:restaurant_id", "customEvent:type", "customEvent:source"],
        "resolve": "restaurant",
    },
    "deal_redeemed": {
        "dimensions": ["customEvent:restaurant_id", "customEvent:type"],
        "resolve": "restaurant",
    },
    "booking_started": {
        "dimensions": ["customEvent:restaurant_id", "customEvent:source"],
        "resolve": "restaurant",
    },
    "booking_created": {
        "dimensions": ["customEvent:restaurant_id", "customEvent:source"],
        "resolve": "restaurant",
    },
    "booking_cancelled": {
        "dimensions": ["customEvent:restaurant_id"],
        "resolve": "restaurant",
    },
    "loyalty_card_viewed": {
        "dimensions": ["customEvent:restaurant_id", "customEvent:source"],
        "resolve": "restaurant",
    },
    "stamp_collected": {"dimensions": ["customEvent:restaurant_id"], "resolve": "restaurant"},
    "reward_redeemed": {"dimensions": ["customEvent:restaurant_id"], "resolve": "restaurant"},
    "notification_open": {"dimensions": ["customEvent:source", "customEvent:notification_type"]},
    "spin_started": {"dimensions": ["customEvent:campaign_id"], "resolve": "campaign"},
    "spin_completed": {"dimensions": ["customEvent:prize_title", "customEvent:is_win", "customEvent:campaign_id"], "resolve": "campaign"},
}


def ga_range_to_datetimes(start_date: str, end_date: str):
    """Map GA4 relative/absolute dates to an aware [start, end] window in TIME_ZONE."""
    now = timezone.localtime()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tz = timezone.get_current_timezone()

    def parse_bound(value, is_end):
        value = (value or "").strip()
        if value == "today":
            return now if is_end else today
        if value.endswith("daysAgo"):
            days = int(value.replace("daysAgo", ""))
            day = today - timedelta(days=days)
            if is_end:
                return day.replace(hour=23, minute=59, second=59, microsecond=999999)
            return day
        parsed = parse_date(value)
        if parsed is None:
            raise ValueError(f"Invalid date: {value}")
        dt = timezone.make_aware(datetime.combine(parsed, time.min), tz)
        if is_end:
            return dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        return dt

    return parse_bound(start_date, False), parse_bound(end_date, True)


def get_dashboard(start_date="30daysAgo", end_date="today"):
    historical_key = f"analytics:dashboard:v3:{start_date}:{end_date}"
    realtime_key = "analytics:realtime"

    historical = cache.get(historical_key)
    if historical is None:
        historical = _build_historical(start_date, end_date)
        cache.set(historical_key, historical, HISTORICAL_CACHE_SECONDS)

    realtime = cache.get(realtime_key)
    if realtime is None:
        analytics = GoogleAnalyticsService()
        realtime = {"active_users": analytics.get_realtime_users()}
        cache.set(realtime_key, realtime, REALTIME_CACHE_SECONDS)

    return {**historical, "realtime": realtime}


def _build_historical(start_date, end_date):
    analytics = GoogleAnalyticsService()
    events = analytics.get_events(start_date=start_date, end_date=end_date)
    counts = {item["event_name"]: item["count"] for item in events}
    window_start, window_end = ga_range_to_datetimes(start_date, end_date)

    return {
        "range": {"start_date": start_date, "end_date": end_date},
        "overview": analytics.get_overview(start_date=start_date, end_date=end_date),
        "platforms": analytics.get_platform_breakdown(start_date=start_date, end_date=end_date),
        "app_versions": analytics.get_app_versions(start_date=start_date, end_date=end_date),
        "daily_users": analytics.get_daily_users(start_date=start_date, end_date=end_date),
        "events": events,
        "engagement": [
            {
                "event_name": event_name,
                "label": label,
                "count": counts.get(event_name, 0),
                "details": _event_details(
                    analytics,
                    event_name,
                    start_date,
                    end_date,
                    window_start,
                    window_end,
                    counts.get(event_name, 0),
                ),
            }
            for event_name, label in ENGAGEMENT_EVENTS
        ],
        "behaviour": {
            key: counts.get(event_name, 0)
            for key, event_name in BEHAVIOUR_EVENTS.items()
        },
        "business": _business_metrics(window_start, window_end),
    }


def _event_details(analytics, event_name, start_date, end_date, window_start, window_end, count):
    if not count:
        return []
    spec = EVENT_DETAIL_SPECS.get(event_name)
    if not spec:
        return []

    resolve = spec.get("resolve")
    for dimension in spec["dimensions"]:
        try:
            rows = analytics.get_event_breakdown(
                event_name=event_name,
                dimension=dimension,
                start_date=start_date,
                end_date=end_date,
            )
        except Exception:
            continue
        if not rows:
            continue
        if resolve == "restaurant" and "restaurant_id" in dimension:
            mapped = _map_restaurant_ids(rows)
            if mapped:
                return mapped
            continue
        if resolve == "campaign" and "campaign_id" in dimension:
            mapped = _map_campaign_ids(rows)
            if mapped:
                return mapped
            continue
        mapped = _named_counts(rows, dimension=dimension)
        if mapped:
            return mapped

    if event_name == "restaurant_viewed":
        return _restaurant_views_from_db(window_start, window_end)
    if event_name == "restaurant_favorited":
        return _favourites_from_db(window_start, window_end)
    if event_name == "deal_viewed":
        return _deal_views_from_db(window_start, window_end)
    return []


def _display_name(value, dimension=""):
    name = (value or "").strip()
    if not name or name.lower() in {"(not set)", "(not provided)", "(none)"}:
        return ""
    if "is_win" in dimension:
        lowered = name.lower()
        if lowered == "true":
            return "Win"
        if lowered == "false":
            return "No win"
    return name


def _named_counts(rows, dimension=""):
    mapped = []
    for item in rows:
        name = _display_name(item.get("value"), dimension)
        if not name:
            continue
        mapped.append({"name": name, "count": item["count"]})
    return mapped[:15]


def _map_restaurant_ids(rows):
    ids = []
    for item in rows:
        try:
            ids.append(int(item["value"]))
        except (TypeError, ValueError):
            continue
    names = dict(Restaurant.objects.filter(pk__in=ids).values_list("id", "name"))
    mapped = []
    for item in rows:
        try:
            pk = int(item["value"])
        except (TypeError, ValueError):
            continue
        name = _display_name(names.get(pk))
        if not name:
            continue
        mapped.append({"name": name, "count": item["count"]})
    return mapped[:15]


def _map_campaign_ids(rows):
    ids = []
    for item in rows:
        try:
            ids.append(int(item["value"]))
        except (TypeError, ValueError):
            continue
    titles = dict(SpinToWinCampaign.objects.filter(pk__in=ids).values_list("id", "title"))
    mapped = []
    for item in rows:
        try:
            pk = int(item["value"])
        except (TypeError, ValueError):
            continue
        title = _display_name(titles.get(pk))
        if not title:
            continue
        mapped.append({"name": title, "count": item["count"]})
    return mapped[:15]


def _favourites_from_db(window_start, window_end):
    return [
        {"name": row["restaurant__name"], "count": row["views"]}
        for row in SavedRestaurant.objects.filter(
            created_at__gte=window_start,
            created_at__lte=window_end,
        )
        .values("restaurant__name")
        .annotate(views=Count("id"))
        .order_by("-views")[:15]
        if row["restaurant__name"]
    ]


def _deal_views_from_db(window_start, window_end):
    return [
        {"name": row["restaurant__name"], "count": row["views"]}
        for row in DealClickLog.objects.filter(
            action_type=DealClickLog.ACTION_VIEW,
            created_at__gte=window_start,
            created_at__lte=window_end,
        )
        .values("restaurant__name")
        .annotate(views=Count("id"))
        .order_by("-views")[:15]
        if row["restaurant__name"]
    ]


def _restaurant_views_from_db(window_start, window_end):
    restaurant_views = RestaurantViewLog.objects.filter(
        view_type=RestaurantViewLog.VIEW_TYPE_DETAIL,
        created_at__gte=window_start,
        created_at__lte=window_end,
    )
    return [
        {"name": row["restaurant__name"], "count": row["views"]}
        for row in restaurant_views.values("restaurant__name")
        .annotate(views=Count("id"))
        .order_by("-views")[:15]
        if row["restaurant__name"]
    ]


def _business_metrics(window_start, window_end):
    bookings = Booking.objects.filter(created_at__gte=window_start, created_at__lte=window_end)
    redemptions = DealUse.objects.filter(is_redeemed=True).filter(
        Q(redeemed_at__gte=window_start, redeemed_at__lte=window_end)
        | Q(redeemed_at__isnull=True, used_at__gte=window_start, used_at__lte=window_end)
    )
    savings = redemptions.aggregate(total=Sum("discount_amount_saved"))["total"]
    restaurant_views = RestaurantViewLog.objects.filter(
        view_type=RestaurantViewLog.VIEW_TYPE_DETAIL,
        created_at__gte=window_start,
        created_at__lte=window_end,
    )
    deal_views = DealClickLog.objects.filter(
        action_type=DealClickLog.ACTION_VIEW,
        created_at__gte=window_start,
        created_at__lte=window_end,
    )
    top_restaurants = list(
        restaurant_views.values("restaurant_id", "restaurant__name")
        .annotate(views=Count("id"))
        .order_by("-views")[:10]
    )

    confirmed_statuses = (
        Booking.STATUS_CONFIRMED,
        Booking.STATUS_ARRIVED,
        Booking.STATUS_COMPLETED,
    )
    return {
        "bookings_created": bookings.count(),
        "bookings_confirmed": bookings.filter(status__in=confirmed_statuses).count(),
        "bookings_cancelled": bookings.filter(status=Booking.STATUS_CANCELLED).count(),
        "no_shows": bookings.filter(status=Booking.STATUS_NO_SHOW).count(),
        "redemptions": redemptions.count(),
        "redemption_value": float(savings or 0),
        "restaurant_detail_views": restaurant_views.count(),
        "deal_views": deal_views.count(),
        "top_restaurants": [
            {
                "restaurant_id": row["restaurant_id"],
                "name": row["restaurant__name"],
                "views": row["views"],
            }
            for row in top_restaurants
        ],
    }
