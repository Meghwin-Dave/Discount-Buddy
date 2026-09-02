# Test Notification API - Quick Guide

## 🚀 New Test Endpoint Added!

**Endpoint:** `POST /user/api/notifications/send_test`

This endpoint allows you to send a test notification to yourself to verify the notification system is working.

## 📋 Step-by-Step Testing

### Step 1: Login to Get JWT Token

```bash
curl -X POST http://192.168.29.221:8000/user/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your@email.com",
    "password": "yourpassword"
  }'
```

**Response:**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "uuid",
    "email": "your@email.com",
    ...
  }
}
```

**Copy the `access` token for the next steps.**

---

### Step 2: Send Test Notification

```bash
curl -X POST http://192.168.29.221:8000/user/api/notifications/send_test \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Notification 🚀",
    "message": "This is a test! Notifications are working!",
    "send_push": true
  }'
```

**Response:**
```json
{
  "success": true,
  "notification_id": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
  "message": "Test notification sent successfully",
  "push_sent": true,
  "device_count": 2
}
```

**What happens:**
- ✅ Creates an in-app notification
- ✅ Sends push notification to all your registered devices (if `send_push: true`)
- ✅ Returns the notification ID and device count

---

### Step 3: Check Unread Count

```bash
curl -X GET http://192.168.29.221:8000/user/api/notifications/unread_count \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response:**
```json
{
  "count": 1
}
```

---

### Step 4: List Notifications

```bash
curl -X GET "http://192.168.29.221:8000/user/api/notifications/?page=1&page_size=5" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response:**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
      "title": "Test Notification 🚀",
      "message": "This is a test! Notifications are working!",
      "notification_type": "SYSTEM",
      "is_read": false,
      "payload": {
        "test": true,
        "timestamp": "..."
      },
      "created_at": "2026-02-13T13:25:00Z"
    }
  ]
}
```

---

## 🎯 Test Endpoint Options

### Default Test (No Body Required)

```bash
curl -X POST http://192.168.29.221:8000/user/api/notifications/send_test \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

Sends a default test notification with:
- Title: "Test Notification 🧪"
- Message: "This is a test notification from Discount Buddy..."
- Push: Enabled

### Custom Test

```bash
curl -X POST http://192.168.29.221:8000/user/api/notifications/send_test \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My Custom Title",
    "message": "My custom message here!",
    "send_push": false
  }'
```

**Parameters:**
- `title` (optional): Custom notification title
- `message` (optional): Custom notification message
- `send_push` (optional, default: true): Whether to send push notification

---

## 🧪 Using the Test Script

We've created an interactive test script for you:

```bash
cd /Users/priyansuchavda/Documents/Discount-Buddy
./testing_scripts/test_notification_api.sh
```

The script will:
1. Ask for your email and password
2. Login and get JWT token
3. Send a test notification
4. Check unread count
5. List recent notifications

---

## 📱 Mobile App Testing

After sending a test notification:

1. **Check In-App Notifications:**
   - Open your app's notifications screen
   - You should see the test notification

2. **Check Push Notification:**
   - If you have a device token registered
   - You should receive a push notification
   - The response shows `device_count` - number of devices that will receive the push

3. **Verify Badge Count:**
   - The unread count should increase
   - Your app's notification badge should update

---

## ✅ Success Indicators

| Check | Expected Result |
|-------|----------------|
| API Response | `"success": true` |
| Notification ID | Valid UUID returned |
| Device Count | Number of your registered devices |
| Unread Count | Increases by 1 |
| In-App List | Test notification appears |
| Push Notification | Received on device (if token registered) |

---

## 🔧 Troubleshooting

### "Token not valid" Error
- Your JWT token has expired
- Login again to get a new token
- Tokens typically expire after 1 hour

### "device_count": 0
- No device tokens registered for your account
- Register a device token first using `/user/api/notifications/devices/`
- See `MOBILE_NOTIFICATION_IMPLEMENTATION.md` for device registration

### No Push Notification Received
1. Check `device_count` in response (should be > 0)
2. Verify Celery worker is running
3. Check Celery logs for errors
4. Verify Firebase credentials are correct

---

## 📚 Related Documentation

- **API Reference:** `NOTIFICATION_API_REFERENCE.md`
- **Mobile Integration:** `MOBILE_NOTIFICATION_IMPLEMENTATION.md`
- **Setup Guide:** `SETUP_COMPLETE.md`
- **Fix Summary:** `NOTIFICATION_API_FIX_SUMMARY.md`

---

## 🎉 Quick Test Command

Replace `YOUR_EMAIL` and `YOUR_PASSWORD` with your credentials:

```bash
# Get token and send test in one command
TOKEN=$(curl -s -X POST http://192.168.29.221:8000/user/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"YOUR_EMAIL","password":"YOUR_PASSWORD"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])") && \
curl -X POST http://192.168.29.221:8000/user/api/notifications/send_test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Quick Test 🚀","message":"Testing notifications!"}' | python3 -m json.tool
```

This will login, get the token, and send a test notification in one command!
