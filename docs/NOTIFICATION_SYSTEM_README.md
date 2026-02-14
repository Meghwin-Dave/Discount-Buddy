# Notification System - Implementation Guide

## Overview

The notification system has been successfully implemented following the specifications in `notifications.md`. This system supports:

- ✅ **In-app notifications** (stored in PostgreSQL/SQLite)
- ✅ **Push notifications** (via Firebase Cloud Messaging)
- ✅ **Event-driven triggers** (Booking confirmed, Deal creation, Deal redemption)

## Architecture

The system follows a clean, decoupled architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (DRF)                        │
│  - NotificationViewSet (list, retrieve, mark_read, etc.)   │
│  - DeviceTokenViewSet (register/manage FCM tokens)         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   Service Layer                             │
│  - NotificationService (business logic)                     │
│  - Template selection & data injection                      │
│  - Notification creation                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Async Processing Layer (Celery)                │
│  - send_push_notification task                              │
│  - send_bulk_push_notifications task                        │
│  - Firebase Cloud Messaging integration                     │
└─────────────────────────────────────────────────────────────┘
```

## API Endpoints

All endpoints are available under both user and merchant paths:
- `user/api/notifications/`
- `merchant/api/notifications/`

### Notification Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List user's notifications (paginated) |
| GET | `/{id}/` | Get specific notification |
| GET | `/unread-count/` | Get count of unread notifications |
| PATCH | `/{id}/mark-read/` | Mark specific notification as read |
| PATCH | `/read-all/` | Mark all notifications as read |

### Device Token Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/devices/` | List user's device tokens |
| POST | `/devices/` | Register a new FCM device token |
| DELETE | `/devices/{id}/` | Remove a device token |
| PATCH | `/devices/{id}/deactivate/` | Deactivate a device token |

## Setup Instructions

### 1. Database Migration

Run the migrations to create the notification tables:

```bash
source .venv/bin/activate
python manage.py migrate notifications
```

### 2. Firebase Configuration (Required for Push Notifications)

#### Option 1: Using Service Account JSON File

1. Download your Firebase service account JSON file from [Firebase Console](https://console.firebase.google.com/)
   - Go to Project Settings → Service Accounts
   - Click "Generate New Private Key"

2. Save the file in your project (e.g., `firebase-credentials.json`)

3. Add to `settings.py`:
```python
FIREBASE_CREDENTIALS_PATH = BASE_DIR / "firebase-credentials.json"
```

#### Option 2: Using Environment Variable

Set the `FIREBASE_CREDENTIALS` environment variable with the JSON content:

```bash
export FIREBASE_CREDENTIALS='{"type": "service_account", "project_id": "...", ...}'
```

### 3. Redis Setup (Required for Celery)

#### For Development (macOS):

```bash
# Install Redis
brew install redis

# Start Redis
brew services start redis

# Or run Redis in foreground
redis-server
```

#### For Production:

Use a managed Redis service (AWS ElastiCache, Redis Cloud, etc.) or run Redis in Docker.

Update `.env` with your Redis URL:
```
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 4. Running Celery Worker

Celery is required for async push notifications. Start the worker:

```bash
source .venv/bin/activate
celery -A discount_buddy worker --loglevel=info
```

For development, you can run both worker and beat together:
```bash
celery -A discount_buddy worker --beat --loglevel=info
```

## Notification Triggers

The system automatically sends notifications when these events occur:

### 1. Booking Confirmed

**Trigger:** When a `Booking` status changes to `CONFIRMED`

**Notification:**
- Title: "Booking Confirmed 🎉"
- Message: "Your table at {restaurant_name} has been confirmed for {date}."
- Type: `BOOKING_CONFIRMED`

**Implementation:** Signal handler in `notifications/signals.py`

### 2. Favorite Restaurant Deal Created

**Trigger:** When a new `Deal` is created for a restaurant

**Notification:**
- Title: "New Deal Available 🔥"
- Message: "{restaurant_name} has launched a new offer: {deal_title}. Check it out!"
- Type: `FAV_DEAL`
- Recipients: All users who have favorited the restaurant

**Implementation:** Signal handler in `notifications/signals.py` with bulk creation for performance

### 3. Deal Redeemed Successfully

**Trigger:** When a `DealUse` is marked as `is_redeemed=True`

**Notification:**
- Title: "Deal Redeemed Successfully ✅"
- Message: "Enjoy your offer at {restaurant_name}. Bon appétit!"
- Type: `DEAL_REDEEMED`

**Implementation:** Signal handler in `notifications/signals.py`

## Usage Examples

### Creating a Custom Notification

```python
from notifications.services import NotificationService

# Send a custom notification
NotificationService.create_notification(
    user=user,
    title="Welcome!",
    message="Thanks for joining our platform",
    notification_type="SYSTEM",
    payload={"action": "welcome"},
    send_push=True
)
```

### Registering a Device Token (Mobile App)

```bash
POST /user/api/notifications/devices/
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "token": "FCM_DEVICE_TOKEN_HERE",
  "device_type": "android"  # or "ios" or "web"
}
```

### Fetching Notifications

```bash
GET /user/api/notifications/?page=1&page_size=20
Authorization: Bearer {jwt_token}
```

Response:
```json
{
  "count": 45,
  "next": "http://localhost:8000/user/api/notifications/?page=2",
  "previous": null,
  "results": [
    {
      "id": "uuid-here",
      "title": "Booking Confirmed 🎉",
      "message": "Your table at Pizza Palace has been confirmed...",
      "notification_type": "BOOKING_CONFIRMED",
      "is_read": false,
      "payload": {
        "booking_id": "uuid",
        "restaurant_id": "uuid"
      },
      "created_at": "2026-02-13T10:30:00Z"
    }
  ]
}
```

### Getting Unread Count

```bash
GET /user/api/notifications/unread-count/
Authorization: Bearer {jwt_token}
```

Response:
```json
{
  "count": 5
}
```

### Marking Notification as Read

```bash
PATCH /user/api/notifications/{notification_id}/mark-read/
Authorization: Bearer {jwt_token}
```

### Marking All as Read

```bash
PATCH /user/api/notifications/read-all/
Authorization: Bearer {jwt_token}
```

## Performance Optimizations

### 1. Database Indexes

The following indexes are automatically created:
- `(user, is_read)` - Fast unread count queries
- `(notification_type)` - Filter by type
- `(user, created_at)` - Ordered user notifications
- `(user, is_active)` - Active device tokens

### 2. Bulk Operations

For favorite deal notifications (potentially thousands of users):
- Uses `bulk_create()` for notification creation
- Processes push notifications in chunks via Celery

### 3. Async Push Notifications

All push notifications are sent asynchronously via Celery:
- API responses are fast (no waiting for FCM)
- Automatic retries on failure
- Horizontal scaling support

## Testing

### Test Notification Creation

```bash
python manage.py shell
```

```python
from users.models import User
from notifications.services import NotificationService

user = User.objects.first()

# Create a test notification
NotificationService.create_notification(
    user=user,
    title="Test Notification",
    message="This is a test",
    notification_type="SYSTEM",
    send_push=False  # Set to True to test push
)
```

### Test Celery Task

```python
from notifications.tasks import send_push_notification
from notifications.models import Notification

notification = Notification.objects.first()
send_push_notification.delay(str(notification.id))
```

## Troubleshooting

### Push Notifications Not Sending

1. **Check Firebase credentials:**
   ```python
   from notifications.fcm import initialize_firebase
   app = initialize_firebase()
   print(app)  # Should not be None
   ```

2. **Check Celery is running:**
   ```bash
   celery -A discount_buddy inspect active
   ```

3. **Check Redis connection:**
   ```bash
   redis-cli ping  # Should return PONG
   ```

4. **Check device tokens:**
   ```python
   from notifications.models import DeviceToken
   DeviceToken.objects.filter(is_active=True).count()
   ```

### Notifications Not Triggering

1. **Check signals are registered:**
   ```python
   from django.db.models.signals import post_save
   print(post_save.receivers)  # Should show notification signals
   ```

2. **Check logs:**
   ```bash
   # In Django logs
   tail -f logs/django.log
   
   # In Celery logs
   # Check the celery worker terminal output
   ```

## Production Deployment

### Environment Variables

Add to your `.env` or environment:

```bash
# Firebase (choose one option)
FIREBASE_CREDENTIALS_PATH=/path/to/firebase-credentials.json
# OR
FIREBASE_CREDENTIALS='{"type": "service_account", ...}'

# Redis/Celery
CELERY_BROKER_URL=redis://your-redis-host:6379/0
CELERY_RESULT_BACKEND=redis://your-redis-host:6379/0
```

### Running Celery in Production

Use a process manager like Supervisor or systemd:

```ini
# /etc/supervisor/conf.d/celery.conf
[program:celery]
command=/path/to/venv/bin/celery -A discount_buddy worker --loglevel=info
directory=/path/to/project
user=www-data
autostart=true
autorestart=true
```

### Scaling

- **Multiple Celery workers:** Run multiple worker instances for higher throughput
- **Redis cluster:** Use Redis cluster for high availability
- **Database optimization:** Monitor and optimize notification queries
- **Archive old notifications:** Implement periodic cleanup of old notifications

## Next Steps

Now that the notification system is implemented, you need to:

1. ✅ Provide Firebase credentials (see Setup Instructions above)
2. ✅ Start Redis server
3. ✅ Start Celery worker
4. ✅ Test the notification endpoints
5. ✅ Integrate with your mobile app to register device tokens
6. ✅ Test push notifications end-to-end

## Files Created

```
notifications/
├── __init__.py
├── admin.py              # Django admin configuration
├── apps.py               # App configuration with signal registration
├── fcm.py                # Firebase Cloud Messaging helper
├── models.py             # Notification and DeviceToken models
├── serializers.py        # DRF serializers
├── services.py           # Business logic layer
├── signals.py            # Django signal handlers
├── tasks.py              # Celery tasks for async push
├── urls.py               # URL routing
├── views.py              # API ViewSets
└── migrations/
    └── 0001_initial.py   # Database migrations

discount_buddy/
├── celery.py             # Celery configuration
└── __init__.py           # Updated to load Celery

Updated files:
├── settings.py           # Added notifications app, Celery, Firebase config
├── urls.py               # Added notification endpoints
└── requirements.txt      # Added celery, redis, firebase-admin
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the original `notifications.md` specification
3. Check Django and Celery logs for errors
