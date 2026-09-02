# Discount Buddy — Backend Performance & Architecture Audit

**Stack:** Django + DRF  
**Date:** 2026-07-20  
**Scope:** `restaurants`, `users`, `wallet`, `vouchers`, `notifications`, `configs`, settings  
**Tone:** Production-scale review (10k–100k users). No soft padding.

---

## 1. Top 5 Critical Issues (fix immediately)

### 1.1 `HomeScreenView` will melt under real traffic

**Where:** `restaurants/views.py` (~912–1156) + `Restaurant.get_leaderboard_score()`

**What it does wrong:**

- Materializes the **entire** geo/city queryset into memory: `restaurants_for_top = list(queryset)`
- Calls `r.get_leaderboard_score()` per restaurant → each hits `get_latest_mystery_visit()` → **1 MysteryVisit query per restaurant**
- Builds `restaurants_dict` by serializing every encountered restaurant; `HomeScreenRestaurantSerializer` then does **per-row** `SavedRestaurant.exists()`, `images.filter(...)`, `deals.filter(...)` (`.filter()` on a related manager **bypasses prefetch cache**)
- `nearby` / `discount_buddy` same pattern: load bounding box → Python Haversine → sort in process

**Estimated DB hits** (city with 500 restaurants, authenticated user):  
~1 heavy annotated query + **500 mystery visits** + **500 favourite checks** + **500 image lookups** + **500 deal filters** + section re-evaluations ≈ **2,000+ queries / request**.

**What breaks:** Home is the app’s hottest endpoint. At a few hundred concurrent opens you get multi-second P95, worker pool exhaustion, DB connection saturation. This does not survive 10k DAU.

---

### 1.2 `RestaurantListSerializer` turns every list into an N×(3–8) query bomb

**Where:** `restaurants/serializers.py` (307–384)

Per restaurant in a page of 20:

| Method | Extra queries |
|--------|----------------|
| `get_is_favourite` | 1 `EXISTS` |
| `get_leaderboard_score` → mystery visit | 1 |
| `get_active_deals` | 1 (+ nested deal image lookups) |
| `_get_primary_restaurant_image_url` via `.filter().first()` | 1 (prefetch bypassed) |
| Nested `RestaurantCategorySerializer.get_restaurants_count` | 1 **COUNT** per category |

**List of 20 ≈ 80–150+ queries** after the already-expensive annotated base queryset.  
`nearby` has **no pagination** — if the box returns 200 restaurants, multiply that by 5–8.

**What breaks:** Browse/nearby/list are unusable past a few hundred restaurants in a metro.

---

### 1.3 Deal claim has a TOCTOU race; inventory can be oversold

**Where:** `Deal.can_user_use` + `DealViewSet.use` + `create_deal_use_with_redemption`

**Flow:**

1. `is_active_now()` / `can_user_use()` read `used_count` and `deal_uses.count()` with **no row lock**
2. Create `DealUse`
3. `used_count = F("used_count") + 1` (atomic increment only)

Two concurrent claims both pass `max_per_user` / `max_uses` checks. You oversell limited deals. There is also **no idempotency key** — double-tap creates two codes + two QR files.

Redeem path (`select_for_update`) is fine. **Claim path is not.** That asymmetry is how fraud and support tickets happen.

---

### 1.4 Authorization holes that are production-blocking

| Issue | Location | Impact |
|-------|----------|--------|
| `ReviewViewSet.get_queryset()` returns **all** reviews; update/destroy only require `IsUser` | `restaurants/views.py` 1251–1270 | Any customer can edit/delete **any** review |
| `WalletTopUpView` credits balance with no payment/webhook | `wallet/views.py` 29–41 | Authenticated user prints money: `POST amount=99999` |
| OTP is **4 digits**, no attempt lockout, no throttle | `users/views.py` | ~10k brute-force space; email sprayable |
| Zero `DEFAULT_THROTTLE_CLASSES` | `discount_buddy/settings.py` | Auth, OTP, partner-request, claim all abuseable |
| `SECRET_KEY` default `"change-me-in-production"`, `DEBUG` default `True`, `ALLOWED_HOSTS=["*"]` | `settings.py` | Classic footguns if env mis-set |

---

### 1.5 `MerchantAnalyticsView` is O(deals × queries) inside the request

**Where:** `restaurants/views.py` (2187–2398)

Per deal in `deals_qs`:

```python
d_uses = deal_uses_qs.filter(deal=deal)  # new queryset
d_uses.count(); d_redemptions.count(); bookings_qs.filter(...).count(); aggregate(...)
```

Plus Python loops over **all** `deal_uses` / bookings for heatmaps, competitor scans with heavy annotations, and `.extra(select={'day': "date(redeemed_at)"})` (SQLite-ish; fragile on Postgres).

**50 deals → 200+ queries.** Merchant dashboards under load will time out. Fake “traffic sources” and `total_views = clicks * 12` mean the product is also lying with confidence.

---

## 2. Performance Analysis Per API

Estimates assume `PAGE_SIZE=20`, moderate city data, authenticated user where relevant.

| API | Est. DB queries | Major inefficiencies | Risk |
|-----|-----------------|----------------------|------|
| `GET .../home` | **500–2000+** | Full queryset materialize; leaderboard N+1; serializer N+1; deals `.filter` bypasses prefetch | **Critical** |
| `GET .../restaurants` (list) | **80–150** | List serializer N+1; category COUNT nested; no deals prefetch but `active_deals` fetched | **High** |
| `GET .../restaurants/nearby` | **N×5–8, N uncapped** | No pagination; Python distance sort; full serializer | **Critical** |
| `GET .../restaurants/discount-buddy` | **Same as list × N** | Materializes filtered set then sorts in Python | **High** |
| `GET .../restaurants/{slug}` / detail | **15–40** | Detail serializer ignores annotations; `get_average_rating`, `get_reviews_count`, `is_open_now` each hit DB; City→Country nested counts | **Medium–High** |
| `GET .../deals` list | **~5–25** | Mostly OK (`select_related`/`prefetch`); image `.filter` may still N+1 | **Medium** |
| `GET .../deals/active` | **1 + serialize** | Caches model instances in LocMem/Redis — OK for size; **no pagination**; cache key by date only | **Medium** |
| `GET .../deals/flash` | **1 + N** | Loads all flash deals then Python distance | **Medium** |
| `POST .../deals/{id}/use` (claim) | **8–15 + CPU** | Race on limits; **QR PNG generation sync** in request | **High** (correctness + latency) |
| `POST .../deals/redeem` | **5–12** | `select_for_update` good; QR loyalty gen sync when reward earned | **Low–Medium** |
| `GET .../bookings` | **~2–4** | Scoped + `select_related` | **Low** |
| `POST .../bookings` | **3–8** | Fine; notifications may block if Celery eager | **Medium** |
| `GET/POST .../reviews` | list OK; mutations **broken auth** | Unscoped queryset for write | **High** (security) |
| `GET .../profile/stats` | **10–15** | Many separate counts; acceptable at user scale | **Low** |
| `GET merchant/.../dashboard` | **8–20** | Multiple aggregates; OK if scoped | **Low–Medium** |
| `GET merchant/.../analytics` | **50–300+** | Per-deal loop queries; heatmap Python scans | **Critical** |
| `GET .../countries\|cities\|categories` | **1 + N counts** | `SerializerMethodField` COUNT per row | **Medium** |
| `GET vouchers/` | **1** | Caches **unevaluated QuerySet** (`cache.set(cache_key, qs)`) — broken/fragile | **Medium** |
| `POST wallet/top-up` | **2–3** | Free money; race on `balance = balance + amount` without `select_for_update`/`F()` | **Critical** (security) |
| Auth OTP init/resend | **2–4** | Thread email; no rate limit; 4-digit OTP | **High** |

---

## 3. Architecture Review

### What’s poorly designed

1. **`restaurants/views.py` (~2.8k lines) is a god module**  
   User browse, merchant CRUD, analytics, loyalty, mystery visits, partner intake — one file. Untestable, unreviewable, every change risks regressions.

2. **Business logic lives in serializers and model methods called from serializers**  
   - `RestaurantListSerializer.get_leaderboard_score()` → model method that queries  
   - `DealUseCreateSerializer` correctly delegates to services (good)  
   - Everything else (home, analytics, favourite checks, open-now) stays in views/serializers  

3. **Services layer is incomplete**  
   `services.py` covers redemption/loyalty/QR well (`select_for_update`, idempotent loyalty record). Listing, ranking, geo, home composition have **no** service/query layer — copied bounding-box + Haversine appears 4+ times.

4. **Serializer nesting is hostile to scale**  
   `DealSerializer.restaurant = RestaurantListSerializer` nests the heavy list serializer inside deal detail. `CitySerializer` embeds `CountrySerializer` which does `cities.count()`. List cards should never nest “full” serializers with COUNT method fields.

5. **Permissions duplicated and soft**  
   `IsUser` / `IsRestaurant` / `IsRestaurantOwner` defined twice in `users/permissions.py`. Object-level ownership is inconsistently applied (reviews: missing; menu create: checked ad hoc).

6. **Config is not production-ready**  
   Postgres block uses `os.environ.get("discountbuddy", ...)` / `get("admin")` / `get("1234")` — env **key names are wrong**; you’ll silently use defaults.  
   `CELERY_TASK_ALWAYS_EAGER` defaults to `"True"` even on the Redis path → push/notifications still run **inline** unless someone remembers to set the env. That defeats Celery.

7. **Wallet is a stub pretending to be money**  
   Top-up without payment provider + non-atomic balance update = not a wallet, a vulnerability.

### What should be refactored

- Split apps/modules: `catalog` (list/detail/home), `redemptions`, `merchant_ops`, `analytics` (read models / materialized tables).
- Query layer: annotated restaurant cards queryset once; serializers only read annotated attrs / prefetched caches (never `.filter()` on relations).
- Persist `leaderboard_score` (or nightly Celery job + indexed column); never compute decay per request per row.
- Geo: PostGIS / `earthdistance` / DB-side Haversine + `ORDER BY` + `LIMIT`; never load full bbox into Python.
- Enforce object permissions with `get_queryset()` scoping for all write ViewSets.
- Kill `WalletTopUpView` or wire Stripe/webhook + ledger with `select_for_update`.

---

## 4. Optimization Suggestions (high-impact only)

1. **Rewrite home + list serializers to annotated fields only**  
   Drop `get_leaderboard_score`, `get_active_deals`, `get_is_favourite` per row. Prefetch favourites once:  
   `SavedRestaurant.objects.filter(user=u, restaurant_id__in=ids)` → set.  
   Prefetch active deals with `Prefetch(..., queryset=..., to_attr="active_deals_list")`.  
   Primary image: `to_attr="primary_images"` or denormalize `primary_image_url`.

2. **Cap + paginate `nearby` / home sections**  
   Hard `[:50]` at SQL after distance expression; never `list(queryset)`.

3. **Claim deals under lock**  
   ```python
   with transaction.atomic():
       deal = Deal.objects.select_for_update().get(pk=...)
       # re-check max_uses / max_per_user
       create_deal_use...
   ```  
   Move QR generation to Celery; return code immediately, QR URL when ready (or pre-generate).

4. **Replace analytics deal loop with one aggregated query**  
   `DealUse.objects.filter(...).values("deal_id").annotate(clicks=Count(...), redemptions=Count(..., filter=Q(is_redeemed=True)), revenue=Sum(...))`  
   Join titles in Python. Delete simulated traffic math or label it as such.

5. **Fix auth abuse surface**  
   DRF `AnonRateThrottle` / `UserRateThrottle` on OTP, login, claim, partner-request. OTP → 6 digits + attempt counter + lockout. Scope `ReviewViewSet` queryset to `user=request.user` for mutating actions (or use `IsOwner`).

6. **Fix settings before any deploy**  
   Real `SECRET_KEY`, `DEBUG=False`, explicit `ALLOWED_HOSTS`, correct DB env keys (`DB_NAME`/`DB_USER`/…), `CELERY_TASK_ALWAYS_EAGER=False` in prod, Redis cache required for multi-worker (LocMem is per-process and useless under Gunicorn).

7. **Stop caching QuerySets** (`vouchers/views.py`) — cache `list(qs.values(...))` or IDs only.

---

## 5. Scalability Snapshot

| Scale | What happens with current code |
|-------|--------------------------------|
| **10k users** | Home/nearby start degrading; DB CPU spikes on browse |
| **50k users** | Need emergency caching + query rewrites or DB dies first |
| **100k users** | Stack does not hold without structural refactors above |

Concurrency hotspots: deal claim race, wallet credit, OTP spam, uncapped nearby.

Missing async where it matters: QR generation on claim/reward, email via bare `threading.Thread` (fragile under WSGI), Celery default-eager in prod config.

---

## 6. Final Rating

### **3.5 / 10**

**Why that low:**  
There are islands of competent code (`redeem_deal` locking, loyalty idempotency via `LoyaltyRedemptionRecord`, some `select_related`/`annotate` on list querysets, Celery beat for reminders). Those do not offset:

- Home/list/nearby query patterns that are **structurally O(n) DB**, not “needs tuning”
- Deal claim race + free wallet top-up + open review mutation = **correctness and security failures**
- 2.8k-line view module + serializer-driven queries = this will not be safely evolved at 50k–100k users
- Defaults that treat production as optional (`DEBUG`, eager Celery, broken Postgres env keys, no throttles)

**Brief credit:** redemption + loyalty service design is the one part that looks like someone who has shipped commerce before. Everything that feeds the feed does not.

---

## Appendix — Key file map

| Area | Path |
|------|------|
| User restaurant APIs | `restaurants/user_urls.py`, `restaurants/views.py` |
| Merchant APIs | `restaurants/merchant_urls.py` |
| Serializers | `restaurants/serializers.py` |
| Redemption / loyalty | `restaurants/services.py` |
| Models / indexes | `restaurants/models.py` |
| Auth / OTP | `users/views.py`, `users/permissions.py` |
| Wallet | `wallet/views.py`, `wallet/models.py` |
| Settings | `discount_buddy/settings.py` |
| Root URLs | `discount_buddy/urls.py` |
