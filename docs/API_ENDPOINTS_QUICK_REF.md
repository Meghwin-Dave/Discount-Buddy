# ⚠️ IMPORTANT: Correct API Endpoints

## URL Format Note

Django REST Framework uses **underscores** in custom action URLs, not hyphens.

### ✅ Correct URLs

```
GET    /user/api/notifications/unread_count         ← Use underscore
PATCH  /user/api/notifications/{id}/mark_read       ← Use underscore  
PATCH  /user/api/notifications/read_all             ← Use underscore
```

### ❌ Incorrect URLs (will return 404)

```
GET    /user/api/notifications/unread-count         ← Hyphen doesn't work
PATCH  /user/api/notifications/{id}/mark-read       ← Hyphen doesn't work
PATCH  /user/api/notifications/read-all             ← Hyphen doesn't work
```

## Complete Endpoint List

### Device Token Management
```
POST   /user/api/notifications/devices              - Register device token
GET    /user/api/notifications/devices              - List device tokens
PATCH  /user/api/notifications/devices/{id}/deactivate - Deactivate token
DELETE /user/api/notifications/devices/{id}          - Delete token
```

### Notifications
```
GET    /user/api/notifications                      - List notifications (paginated)
GET    /user/api/notifications/{id}                 - Get single notification
GET    /user/api/notifications/unread_count         - Get unread count ⚠️ underscore
PATCH  /user/api/notifications/{id}/mark_read       - Mark as read ⚠️ underscore
PATCH  /user/api/notifications/read_all             - Mark all as read ⚠️ underscore
```

## Testing

Test the correct endpoint:

```bash
# ✅ Correct
curl -X GET http://192.168.29.221:8000/user/api/notifications/unread_count \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# ❌ Wrong (404 error)
curl -X GET http://192.168.29.221:8000/user/api/notifications/unread-count \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

**See [NOTIFICATION_API_REFERENCE.md](./NOTIFICATION_API_REFERENCE.md) for complete documentation with code examples.**
