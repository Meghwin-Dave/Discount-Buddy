# Notification System - Quick Start Guide

## ✅ What's Been Implemented

The complete notification system has been implemented with:

1. **Database Models** - Notification and DeviceToken tables created
2. **API Endpoints** - Full REST API for notifications and device tokens
3. **Service Layer** - Business logic for creating and managing notifications
4. **Celery Tasks** - Async processing for push notifications
5. **Django Signals** - Automatic notification triggers for:
   - Booking confirmations
   - New deals for favorited restaurants
   - Deal redemptions
6. **Firebase Integration** - Ready for FCM push notifications
7. **Admin Interface** - Django admin for managing notifications

## 🚀 Next Steps - What You Need to Do

### Step 1: Provide Firebase Credentials

You mentioned you'll provide Firebase credentials. Here's what to do:

#### Option A: Using JSON File (Recommended)

1. Download your Firebase service account JSON file from Firebase Console
2. Save it in your project root as `firebase-credentials.json`
3. Add this line to `settings.py` (around line 290):
   ```python
   FIREBASE_CREDENTIALS_PATH = BASE_DIR / "firebase-credentials.json"
   ```

#### Option B: Using Environment Variable

Add to your `.env` file:
```
FIREBASE_CREDENTIALS='{"type": "service_account", "project_id": "your-project", ...}'
```

### Step 2: Install and Start Redis

Redis is required for Celery to work.

**On macOS:**
```bash
# Install Redis
brew install redis

# Start Redis
brew services start redis

# Verify it's running
redis-cli ping  # Should return "PONG"
```

**On Linux:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

**Using Docker:**
```bash
docker run -d -p 6379:6379 redis:latest
```

### Step 3: Start Celery Worker

Open a new terminal and run:

```bash
cd /Users/priyansuchavda/Documents/Discount-Buddy
source .venv/bin/activate
celery -A discount_buddy worker --loglevel=info
```

Keep this terminal running. You should see:
```
[tasks]
  . notifications.tasks.send_bulk_push_notifications
  . notifications.tasks.send_push_notification
```

### Step 4: Test the System

#### Test 1: Check API Endpoints

The server is already running. Test the notification endpoints:

```bash
# Get your JWT token first (login)
curl -X POST http://192.168.29.221:8000/user/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}'

# Get notifications (replace TOKEN with your JWT)
curl http://192.168.29.221:8000/user/api/notifications/ \
  -H "Authorization: Bearer TOKEN"

# Get unread count
curl http://192.168.29.221:8000/user/api/notifications/unread-count/ \
  -H "Authorization: Bearer TOKEN"
```

#### Test 2: Create a Test Notification

```bash
source .venv/bin/activate
python manage.py shell
```

Then in the Python shell:
```python
from users.models import User
from notifications.services import NotificationService

# Get a user
user = User.objects.first()

# Create a test notification
notification = NotificationService.create_notification(
    user=user,
    title="Test Notification 🎉",
    message="This is a test notification from the system",
    notification_type="SYSTEM",
    send_push=False  # Set to True once Firebase is configured
)

print(f"Created notification: {notification.id}")
```

#### Test 3: Trigger Automatic Notifications

**Test Booking Confirmation:**
```python
from restaurants.models import Booking
from notifications.models import Notification

# Find a booking and change status to confirmed
booking = Booking.objects.first()
booking.status = 'confirmed'
booking.save()

# Check if notification was created
Notification.objects.filter(
    notification_type='BOOKING_CONFIRMED',
    user=booking.user
).exists()  # Should return True
```

**Test Deal Creation (Favorite Restaurant):**
```python
from restaurants.models import Restaurant, Deal, SavedRestaurant
from django.utils import timezone
from datetime import timedelta

# Create a saved restaurant first
restaurant = Restaurant.objects.first()
user = User.objects.first()
SavedRestaurant.objects.get_or_create(user=user, restaurant=restaurant)

# Create a new deal
deal = Deal.objects.create(
    restaurant=restaurant,
    title="Test Deal",
    description="50% off",
    deal_type="percentage",
    discount_percentage=50,
    start_date=timezone.now(),
    end_date=timezone.now() + timedelta(days=7)
)

# Check if notification was created
Notification.objects.filter(
    notification_type='FAV_DEAL',
    user=user
).exists()  # Should return True
```

## 📱 Mobile App Integration

To receive push notifications in your mobile app:

### 1. Register Device Token

When a user logs in to your mobile app, register their FCM token:

```javascript
// Example for React Native / Flutter
const registerDeviceToken = async (fcmToken) => {
  const response = await fetch('http://your-api/user/api/notifications/devices/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${jwtToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      token: fcmToken,
      device_type: 'android', // or 'ios'
    }),
  });
  return response.json();
};
```

### 2. Handle Push Notifications

Configure your mobile app to handle incoming FCM messages with the payload structure:

```json
{
  "notification": {
    "title": "Booking Confirmed 🎉",
    "body": "Your table at Pizza Palace has been confirmed..."
  },
  "data": {
    "booking_id": "uuid",
    "restaurant_id": "uuid"
  }
}
```

## 🔍 Monitoring & Debugging

### Check Notification Count
```bash
source .venv/bin/activate
python manage.py shell
```

```python
from notifications.models import Notification, DeviceToken

print(f"Total notifications: {Notification.objects.count()}")
print(f"Unread notifications: {Notification.objects.filter(is_read=False).count()}")
print(f"Active device tokens: {DeviceToken.objects.filter(is_active=True).count()}")
```

### View Logs

**Django logs:**
Check your terminal where `python manage.py runserver` is running

**Celery logs:**
Check the terminal where Celery worker is running

### Test Firebase Connection

```python
from notifications.fcm import initialize_firebase

app = initialize_firebase()
if app:
    print("✅ Firebase initialized successfully")
else:
    print("❌ Firebase initialization failed - check credentials")
```

## 📊 Admin Interface

Access the Django admin to manage notifications:

1. Go to: http://192.168.29.221:8000/admin/
2. Navigate to "Notifications" section
3. You can view, filter, and manage:
   - All notifications
   - Device tokens
   - User notification history

## 🎯 Common Use Cases

### Send System-Wide Announcement

```python
from users.models import User
from notifications.services import NotificationService

users = User.objects.filter(is_active=True)

for user in users:
    NotificationService.create_notification(
        user=user,
        title="Important Announcement 📢",
        message="We have exciting new features!",
        notification_type="SYSTEM",
        send_push=True
    )
```

### Check User's Notification Preferences

```python
from notifications.models import DeviceToken

user = User.objects.get(email='user@example.com')
tokens = DeviceToken.objects.filter(user=user, is_active=True)

print(f"User has {tokens.count()} active devices")
for token in tokens:
    print(f"  - {token.device_type}: {token.token[:20]}...")
```

## ⚠️ Important Notes

1. **Celery Must Be Running** - Push notifications won't send without Celery worker
2. **Redis Must Be Running** - Celery requires Redis as message broker
3. **Firebase Credentials Required** - Push notifications need valid Firebase credentials
4. **In-App Notifications Work Without Push** - Even without Firebase/Celery, in-app notifications are stored and accessible via API

## 📚 Full Documentation

For complete documentation, see:
- `NOTIFICATION_SYSTEM_README.md` - Full implementation guide
- `notifications.md` - Original specification

## ✅ Checklist

Before going to production:

- [ ] Firebase credentials configured
- [ ] Redis installed and running
- [ ] Celery worker running
- [ ] Test notifications created successfully
- [ ] Mobile app registers device tokens
- [ ] Push notifications received on mobile
- [ ] Admin interface accessible
- [ ] Monitoring/logging configured

## 🆘 Need Help?

If something isn't working:

1. Check the "Troubleshooting" section in `NOTIFICATION_SYSTEM_README.md`
2. Verify all services are running (Django, Redis, Celery)
3. Check logs for error messages
4. Test each component individually

---

**Ready to provide Firebase credentials?** Once you do, just update the settings and restart the Celery worker!
