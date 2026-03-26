# Discount Buddy – Notification System Technical Specification

> **Version:** 2.0  
> **Last Updated:** 2026-03-26  
> **Scope:** Backend (Django), Push (FCM), Async (Celery + Redis)

---

## 1. Architecture Overview

```
User / Merchant Action
        │
        ▼
  Django Signal (post_save)
        │
        ▼
  NotificationService  ──► Notification row (DB)
        │
        ▼
  Celery Task (async)
        │
        ▼
  FCM module  ──► Firebase Cloud Messaging  ──► Device
```

All notification creation flows through `notifications/services.py → NotificationService`.
Push delivery is **always asynchronous** via Celery so the primary API response is never
blocked.

---

## 2. Django App Structure

```
notifications/
├── admin.py          – Django admin with list filters and search
├── apps.py           – AppConfig; imports signals on ready()
├── fcm.py            – Firebase Admin SDK wrapper (lazy-init)
├── models.py         – Notification, DeviceToken
├── serializers.py    – DRF serializers
├── services.py       – Business logic / notification factory
├── signals.py        – Django signal receivers (auto-triggers)
├── tasks.py          – Celery tasks for async push delivery
├── urls.py           – Router registration
└── views.py          – REST API viewsets (NotificationViewSet, DeviceTokenViewSet)
```

---

## 3. Database Models

### 3.1 Notification

| Field               | Type       | Notes                                             |
|---------------------|------------|---------------------------------------------------|
| `id`                | UUID (PK)  | Auto-generated                                    |
| `user`              | FK → User  | Recipient (customer **or** merchant user)         |
| `title`             | CharField  | Short notification heading                        |
| `message`           | TextField  | Full notification body                            |
| `notification_type` | CharField  | See §4 for full enum                              |
| `is_read`           | BooleanField | Defaults `False`; updated by mark-read endpoint |
| `payload`           | JSONField  | Extra data for deep-linking                       |
| `source_id`         | UUIDField  | PK of the triggering object (booking, deal, …)   |
| `source_type`       | CharField  | Model name: `booking`, `deal`, `deal_use`, etc.  |
| `created_at`        | DateTime   | Auto                                              |

**DB Indexes:** `(user, is_read)`, `(notification_type)`, `(user, created_at)`

### 3.2 DeviceToken

| Field         | Type      | Notes                             |
|---------------|-----------|-----------------------------------|
| `id`          | UUID (PK) | Auto-generated                    |
| `user`        | FK → User | Owner of the device               |
| `token`       | CharField | FCM registration token (unique)   |
| `device_type` | CharField | `android` / `ios` / `web`        |
| `is_active`   | Boolean   | Soft-deactivated on logout        |

---

## 4. Notification Types Enum

```python
# Customer-facing
"BOOKING_CONFIRMED"      – booking status → CONFIRMED
"FAV_DEAL"               – new deal at a favourite restaurant
"DEAL_REDEEMED"          – customer redeemed a deal
"SYSTEM"                 – manual / admin broadcast

# Merchant-facing
"NEW_BOOKING"            – customer made a new booking request
"MERCHANT_DEAL_REDEEMED" – a deal was redeemed at their restaurant
"MILESTONE_EARNINGS"     – cumulative earnings crossed a threshold
"NEW_REVIEW"             – customer posted a new review
```

---

## 5. Signal Handlers (`notifications/signals.py`)

| Signal Handler                  | Sender Model       | Trigger Condition                             | Notification Type(s)                     |
|---------------------------------|--------------------|-----------------------------------------------|------------------------------------------|
| `notify_booking_confirmed`      | `restaurants.Booking` | `status == CONFIRMED`                      | `BOOKING_CONFIRMED` → customer           |
| `notify_merchant_new_booking`   | `restaurants.Booking` | `created == True`                          | `NEW_BOOKING` → all restaurant owners   |
| `notify_favorite_restaurant_deal` | `restaurants.Deal` | `created == True` and `is_active == True` | `FAV_DEAL` → all favouriting users      |
| `notify_deal_redeemed`          | `restaurants.DealUse` | `is_redeemed == True`                     | `DEAL_REDEEMED` → customer              |
| ↳ (same handler)                | `restaurants.DealUse` | `is_redeemed == True`                     | `MERCHANT_DEAL_REDEEMED` → owners       |
| ↳ (same handler)                | `restaurants.DealUse` | triggers `_check_merchant_earnings_milestone` | `MILESTONE_EARNINGS` (if new milestone) |
| `notify_merchant_new_review`    | `restaurants.Review` | `created == True`                          | `NEW_REVIEW` → all restaurant owners    |

**Duplicate-prevention:** Every handler queries the `Notification` table using
`source_id + source_type + notification_type` (+ `user` where applicable) before
creating a new row, ensuring exactly-once delivery.

**Transaction safety:** Handlers that create objects use `transaction.on_commit()`
to guarantee the triggering row is fully committed before notifications are sent.

---

## 6. Service Layer (`NotificationService`)

### Customer-side methods

```python
NotificationService.create_notification(user, title, message, notification_type,
                                        payload=None, source_id=None,
                                        source_type=None, send_push=True)

NotificationService.send_booking_confirmed(user, booking)
NotificationService.notify_favorite_deal(restaurant, deal) -> int
NotificationService.send_deal_redeemed(user, deal, restaurant)
NotificationService.mark_as_read(notification_id, user) -> bool
NotificationService.mark_all_as_read(user) -> int
NotificationService.get_unread_count(user) -> int
```

### Merchant-side methods (new in v2)

```python
NotificationService.notify_merchant_new_booking(booking) -> int
NotificationService.notify_merchant_deal_redeemed(deal_use) -> int
NotificationService.notify_merchant_milestone(restaurant, milestone_amount) -> int
NotificationService.notify_merchant_new_review(review) -> int
```

### Helper

```python
NotificationService._get_restaurant_owners(restaurant) -> list[User]
```

Resolves owners via **both** `RestaurantProfile.owner_profile` and
`vouchers.Merchant.user` so the system covers every merchant setup pattern.

---

## 7. Milestone Earnings Logic

Checked inside `_check_merchant_earnings_milestone(restaurant)` after every
successful deal redemption:

```
MILESTONES = [£100, £500, £1,000, £5,000, £10,000, £50,000]

total = SUM(DealUse.final_bill_amount)
        WHERE deal__restaurant = restaurant
          AND is_redeemed = True
          AND final_bill_amount IS NOT NULL

For each milestone M in MILESTONES:
    if total >= M AND no MILESTONE_EARNINGS notification exists with payload.milestone_amount == M:
        send MILESTONE_EARNINGS to all restaurant owners
```

**Note:** `final_bill_amount` is the amount the customer paid **after** the
discount.  If you want "total savings" instead, switch to `discount_amount_saved`.
Update the field in `_check_merchant_earnings_milestone` accordingly.

---

## 8. API Endpoints

Both prefixes share the **same** `notifications/urls.py` router.

| Method | URL                                              | Description                   |
|--------|--------------------------------------------------|-------------------------------|
| GET    | `/user/api/notifications/`                        | List (paginated, 20/page)     |
| GET    | `/user/api/notifications/{id}/`                   | Single notification           |
| GET    | `/user/api/notifications/unread_count`            | `{"count": N}`                |
| PATCH  | `/user/api/notifications/{id}/mark_read`          | Mark one as read              |
| PATCH  | `/user/api/notifications/read_all`                | Mark all as read              |
| POST   | `/user/api/notifications/send_test`               | Dev: create test notification |
| POST   | `/user/api/notifications/devices`                 | Register FCM token            |
| GET    | `/user/api/notifications/devices`                 | List tokens                   |
| PATCH  | `/user/api/notifications/devices/{id}/deactivate` | Soft-deactivate token         |
| DELETE | `/user/api/notifications/devices/{id}`            | Hard-delete token             |

**Merchant URLs** are identical but prefixed with `/merchant/api/notifications/`.

All endpoints require `Authorization: Bearer <JWT>`.

---

## 9. Async Push Delivery

### Celery tasks (`notifications/tasks.py`)

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def send_push_notification(self, notification_id: str): ...

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def send_bulk_push_notifications(self, notification_ids: list[str]): ...
```

Retries: 3 attempts, 5-second back-off.

### Required services

| Service         | Purpose                      | Default              |
|-----------------|------------------------------|----------------------|
| Redis           | Celery message broker        | `localhost:6379`     |
| Celery Worker   | Task consumer                | `celery -A discount_buddy worker --loglevel=info` |
| Firebase Admin  | Push delivery                | `FIREBASE_CREDENTIALS_PATH` setting |

---

## 10. Firebase Configuration

```python
# settings.py
FIREBASE_CREDENTIALS_PATH = BASE_DIR / "firebase-credentials.json"
# OR
FIREBASE_CREDENTIALS = os.environ.get("FIREBASE_CREDENTIALS")  # JSON string
```

The `fcm.py` module lazily initialises Firebase on first use.  If credentials are
absent the push step is silently skipped—in-app notifications still persist.

---

## 11. Push Payload Structure (FCM)

```json
{
  "notification": {
    "title": "New Table Booking Request 📅",
    "body": "John Doe has requested a table for 2 guests..."
  },
  "data": {
    "booking_id": "uuid",
    "restaurant_id": "uuid",
    "customer_name": "John Doe",
    "number_of_guests": 2,
    "booking_date": "2026-04-01T19:30:00Z"
  }
}
```

The `data` block mirrors the `payload` JSON field stored in the `Notification` row.

---

## 12. Admin Interface

Available at `/admin/notifications/`:
- Filter by `notification_type`, `is_read`, `user`
- Search by user email, title, message
- Inline DeviceToken management

---

## 13. Security

- All endpoints require **JWT authentication** (`IsAuthenticated`)
- Users can **only** read/modify their own notifications (queryset is always
  filtered by `request.user`)
- Device tokens are scoped per-user
- No bulk-write endpoints are exposed publicly

---

## 14. Running the Full Stack

```bash
# 1. Django (already running)
python manage.py runserver 0.0.0.0:8000

# 2. Redis
brew services start redis        # macOS
# OR: docker run -d -p 6379:6379 redis:latest

# 3. Celery worker
celery -A discount_buddy worker --loglevel=info
```
