# ✅ Test Notification API Created!

## 🎯 New Endpoint

**POST /user/api/notifications/send_test**

Send a test notification to yourself to verify the notification system is working.

## 📋 Quick Start

### 1. Login
```bash
curl -X POST http://192.168.29.221:8000/user/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"yourpassword"}'
```

### 2. Send Test Notification
```bash
curl -X POST http://192.168.29.221:8000/user/api/notifications/send_test \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test 🚀",
    "message": "Testing notifications!",
    "send_push": true
  }'
```

### 3. Response
```json
{
  "success": true,
  "notification_id": "uuid-here",
  "message": "Test notification sent successfully",
  "push_sent": true,
  "device_count": 2
}
```

## 🎨 Features

✅ **Customizable** - Set custom title and message  
✅ **Push Notifications** - Optionally send push to devices  
✅ **Device Count** - Shows how many devices will receive push  
✅ **Instant Feedback** - Returns notification ID immediately  
✅ **In-App + Push** - Creates both in-app and push notifications  

## 📱 What Gets Created

When you call this endpoint:

1. **In-App Notification**
   - Stored in database
   - Visible in `/user/api/notifications/` list
   - Increases unread count
   - Type: `SYSTEM`

2. **Push Notification** (if `send_push: true`)
   - Sent to all active device tokens
   - Delivered via Firebase Cloud Messaging
   - Processed asynchronously by Celery

## 🧪 Testing Tools

### Interactive Script
```bash
./testing_scripts/test_notification_api.sh
```
Guides you through the entire testing process.

### One-Line Test
```bash
TOKEN=$(curl -s -X POST http://192.168.29.221:8000/user/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"YOUR_EMAIL","password":"YOUR_PASSWORD"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access'])") && \
curl -X POST http://192.168.29.221:8000/user/api/notifications/send_test \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

## 📚 Documentation

- **Complete Guide:** `TEST_NOTIFICATION_API.md`
- **API Reference:** `NOTIFICATION_API_REFERENCE.md`
- **Mobile Integration:** `MOBILE_NOTIFICATION_IMPLEMENTATION.md`

## ✨ Example Use Cases

### 1. Quick System Check
```bash
POST /user/api/notifications/send_test
# No body needed - uses defaults
```

### 2. Custom Message
```json
{
  "title": "Welcome! 👋",
  "message": "Thanks for joining Discount Buddy!",
  "send_push": true
}
```

### 3. In-App Only (No Push)
```json
{
  "title": "Reminder",
  "message": "Check out today's deals!",
  "send_push": false
}
```

## 🔍 Verification Steps

After sending a test notification:

1. ✅ Check API response has `"success": true`
2. ✅ Verify `notification_id` is returned
3. ✅ Check `device_count` matches your registered devices
4. ✅ Call `/unread_count` - should increase by 1
5. ✅ List notifications - test should appear
6. ✅ Check mobile app for push notification

## 🎉 Status

**Endpoint:** ✅ Working  
**Server:** ✅ Running on http://0.0.0.0:8000/  
**Authentication:** ✅ JWT Required  
**Push Notifications:** ✅ Enabled (requires Celery + Redis)  

---

**Ready to test!** See `TEST_NOTIFICATION_API.md` for detailed instructions.
