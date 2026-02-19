# Firebase Setup Checklist

## 📋 When You Provide Firebase Credentials

Follow these steps to complete the notification system setup:

### Step 1: Add Firebase Credentials

#### Option A: Using JSON File (Recommended)

1. Save your Firebase service account JSON file as:
   ```
   /Users/priyansuchavda/Documents/Discount-Buddy/firebase-credentials.json
   ```

2. Add this line to `settings.py` (after line 290, in the Firebase section):
   ```python
   FIREBASE_CREDENTIALS_PATH = BASE_DIR / "firebase-credentials.json"
   ```

3. Add to `.gitignore` (to avoid committing credentials):
   ```
   firebase-credentials.json
   ```

#### Option B: Using Environment Variable

1. Add to your `.env` file:
   ```
   FIREBASE_CREDENTIALS='{"type": "service_account", "project_id": "...", ...}'
   ```

### Step 2: Install and Start Redis

```bash
# Install Redis (if not already installed)
brew install redis

# Start Redis
brew services start redis

# Verify Redis is running
redis-cli ping
# Should output: PONG
```

### Step 3: Start Celery Worker

Open a **new terminal window** and run:

```bash
cd /Users/priyansuchavda/Documents/Discount-Buddy
source .venv/bin/activate
celery -A discount_buddy worker --loglevel=info
```

**Keep this terminal running!** You should see output like:
```
[tasks]
  . notifications.tasks.send_bulk_push_notifications
  . notifications.tasks.send_push_notification

[2026-02-13 16:00:00,000: INFO/MainProcess] Connected to redis://localhost:6379/0
[2026-02-13 16:00:00,000: INFO/MainProcess] celery@hostname ready.
```

### Step 4: Test Firebase Connection

In another terminal:

```bash
cd /Users/priyansuchavda/Documents/Discount-Buddy
source .venv/bin/activate
python manage.py shell
```

Then run:
```python
from notifications.fcm import initialize_firebase

app = initialize_firebase()
if app:
    print("✅ Firebase initialized successfully!")
else:
    print("❌ Firebase initialization failed - check credentials")
```

### Step 5: Test Push Notification

Still in the Django shell:

```python
from users.models import User
from notifications.models import DeviceToken, Notification
from notifications.services import NotificationService

# Get a user
user = User.objects.first()

# Register a test device token (use a real FCM token from your mobile app)
device_token = DeviceToken.objects.create(
    user=user,
    token="YOUR_REAL_FCM_TOKEN_HERE",  # Replace with actual token
    device_type="android"
)

# Create a notification with push
notification = NotificationService.create_notification(
    user=user,
    title="Test Push Notification 🚀",
    message="If you see this on your device, push notifications are working!",
    notification_type="SYSTEM",
    send_push=True  # This will trigger the Celery task
)

print(f"Notification created: {notification.id}")
print("Check your Celery worker terminal for push notification logs")
print("Check your mobile device for the push notification")
```

### Step 6: Verify Everything Works

#### Check Celery Logs

In the Celery worker terminal, you should see:
```
[INFO/MainProcess] Task notifications.tasks.send_push_notification[...] received
[INFO/ForkPoolWorker-1] Successfully sent FCM message: ...
[INFO/ForkPoolWorker-1] Task notifications.tasks.send_push_notification[...] succeeded
```

#### Check Notifications in API

```bash
# Get your JWT token
curl -X POST http://192.168.29.221:8000/user/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}'

# Get notifications
curl http://192.168.29.221:8000/user/api/notifications/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Step 7: Test Automatic Triggers

#### Test Booking Confirmation

```python
from restaurants.models import Booking, Restaurant
from users.models import User
from django.utils import timezone

user = User.objects.first()
restaurant = Restaurant.objects.first()

# Create a booking
booking = Booking.objects.create(
    user=user,
    restaurant=restaurant,
    booking_date=timezone.now() + timezone.timedelta(days=1),
    number_of_guests=2,
    status='pending'
)

# Change status to confirmed (this should trigger notification)
booking.status = 'confirmed'
booking.save()

# Check if notification was created
from notifications.models import Notification
Notification.objects.filter(
    user=user,
    notification_type='BOOKING_CONFIRMED'
).exists()  # Should return True
```

## ✅ Final Verification Checklist

- [ ] Firebase credentials added to settings
- [ ] Redis installed and running (`redis-cli ping` returns PONG)
- [ ] Celery worker running (terminal shows "celery@hostname ready")
- [ ] Firebase initializes successfully (test in Django shell)
- [ ] Test notification created successfully
- [ ] Push notification sent (check Celery logs)
- [ ] Push notification received on mobile device
- [ ] API endpoints return notifications
- [ ] Automatic triggers work (booking confirmation)
- [ ] Device tokens can be registered via API
- [ ] Unread count endpoint works

## 🎯 Production Deployment

Once everything works in development:

### 1. Update Environment Variables

Add to your production `.env`:
```bash
# Firebase
FIREBASE_CREDENTIALS='{"type": "service_account", ...}'

# Redis (use production Redis URL)
CELERY_BROKER_URL=redis://your-production-redis:6379/0
CELERY_RESULT_BACKEND=redis://your-production-redis:6379/0
```

### 2. Run Celery as a Service

Use Supervisor or systemd to keep Celery running:

**Supervisor config** (`/etc/supervisor/conf.d/celery.conf`):
```ini
[program:celery]
command=/path/to/venv/bin/celery -A discount_buddy worker --loglevel=info
directory=/path/to/Discount-Buddy
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/celery/celery.err.log
stdout_logfile=/var/log/celery/celery.out.log
```

Then:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start celery
```

### 3. Monitor Celery

Install Flower for monitoring:
```bash
pip install flower
celery -A discount_buddy flower
```

Access at: http://localhost:5555

## 🆘 Troubleshooting

### Firebase Not Initializing

**Error:** "Firebase credentials not configured"

**Solution:**
1. Check `settings.py` has `FIREBASE_CREDENTIALS_PATH` or environment variable set
2. Verify the JSON file exists and is valid JSON
3. Check file permissions (should be readable)

### Celery Not Connecting to Redis

**Error:** "Error connecting to redis://localhost:6379/0"

**Solution:**
1. Check Redis is running: `redis-cli ping`
2. Check Redis port: `lsof -i :6379`
3. Check firewall settings
4. Verify `CELERY_BROKER_URL` in settings

### Push Notifications Not Sending

**Error:** "Failed to send FCM message"

**Solution:**
1. Verify Firebase credentials are correct
2. Check device token is valid and active
3. Check Celery worker logs for detailed error
4. Verify FCM is enabled in Firebase Console
5. Check device token hasn't expired

### Notifications Not Triggering Automatically

**Solution:**
1. Verify signals are registered (check `apps.py`)
2. Check Django logs for signal errors
3. Verify the triggering conditions are met
4. Test signals manually in Django shell

## 📞 Support

If you encounter issues:

1. Check the logs:
   - Django server logs
   - Celery worker logs
   - Redis logs (`redis-cli monitor`)

2. Review documentation:
   - `NOTIFICATION_SYSTEM_README.md`
   - `NOTIFICATION_QUICK_START.md`
   - `NOTIFICATION_IMPLEMENTATION_SUMMARY.md`

3. Test components individually:
   - Database (notifications stored?)
   - API (endpoints working?)
   - Celery (tasks executing?)
   - Firebase (credentials valid?)

---

**Ready to go!** Once you provide the Firebase credentials and complete these steps, your notification system will be fully operational! 🚀
