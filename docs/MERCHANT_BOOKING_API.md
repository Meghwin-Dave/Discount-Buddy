# Merchant Booking API — Frontend Integration Guide

**Version:** 1.0  
**Last updated:** June 2026  
**Base URL:** `http://<host>:8000` (replace with your environment)

This document covers merchant-facing booking APIs for **calendar views**, **arrival check-in**, **no-show tracking**, and **1-hour push reminders**.

---

## Authentication

All endpoints require a merchant JWT.

```http
POST /merchant/api/users/token
Content-Type: application/json

{
  "email": "merchant@example.com",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>"
}
```

Include the access token on every request:

```http
Authorization: Bearer <jwt_access_token>
```

**Permission:** Merchant role (`IsRestaurant`) — user must own or manage the restaurant linked to the booking.

---

## URL Convention

This API uses **no trailing slashes** (`APPEND_SLASH = False`).

| Correct | Incorrect |
|---------|-----------|
| `/merchant/api/restaurants/restaurant/bookings` | `/merchant/api/restaurants/restaurant/bookings/` |

---

## Booking Status Values

| Status | Description |
|--------|-------------|
| `pending` | Awaiting merchant confirmation |
| `confirmed` | Confirmed by merchant |
| `cancelled` | Cancelled by customer or merchant |
| `completed` | Booking completed (legacy) |
| `arrived` | Guest checked in by merchant |
| `no_show` | Guest did not show up |

**Attendance rules:** Only `pending` or `confirmed` bookings can be marked as `arrived` or `no_show`. Attempts on other statuses return `400 Bad Request`.

---

## 1. List Bookings (Calendar Support)

Fetch bookings for day, week, or month views.

```http
GET /merchant/api/restaurants/restaurant/bookings
Authorization: Bearer <token>
```

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_date` | `YYYY-MM-DD` | No | Include bookings on or after this date |
| `end_date` | `YYYY-MM-DD` | No | Include bookings on or before this date |
| `restaurant_id` | integer | No | Filter by restaurant ID (`all` = no filter) |
| `status` | string | No | Filter by status (e.g. `confirmed`, `arrived`) |
| `ordering` | string | No | Sort field; prefix `-` for descending (default: `-booking_date`) |
| `page` | integer | No | Page number (pagination, 20 per page) |

### Example — Week View

```http
GET /merchant/api/restaurants/restaurant/bookings?start_date=2026-06-16&end_date=2026-06-22&restaurant_id=4
```

### Response `200 OK`

Paginated response:

```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1254,
      "restaurant_name": "Pizza 4 You",
      "contact_name": "John Smith",
      "contact_phone": "9876543210",
      "number_of_guests": 50,
      "booking_date": "2026-06-16T12:10:00Z",
      "status": "confirmed",
      "arrived_time": null,
      "no_show_reason": null,
      "no_show_notes": null,
      "updated_at": "2026-06-16T10:00:00Z"
    },
    {
      "id": 1255,
      "restaurant_name": "Pizza 4 You",
      "contact_name": "Rajan",
      "contact_phone": "9876543210",
      "number_of_guests": 2,
      "booking_date": "2026-06-16T14:00:00Z",
      "status": "arrived",
      "arrived_time": "2026-06-16T14:15:00Z",
      "no_show_reason": null,
      "no_show_notes": null,
      "updated_at": "2026-06-16T14:15:00Z"
    }
  ]
}
```

### cURL

```bash
curl -X GET "http://127.0.0.1:8000/merchant/api/restaurants/restaurant/bookings?start_date=2026-06-16&end_date=2026-06-22" \
  -H "Authorization: Bearer <token>"
```

---

## 2. Get Single Booking

```http
GET /merchant/api/restaurants/restaurant/bookings/{booking_id}
Authorization: Bearer <token>
```

Returns the same object shape as a single item in the `results` array above.

---

## 3. Confirm Booking Arrival

Record that a guest has arrived.

```http
POST /merchant/api/restaurants/restaurant/bookings/{booking_id}/arrive
Authorization: Bearer <token>
Content-Type: application/json
```

`PATCH` is also accepted.

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `arrival_time` | ISO 8601 datetime | No | Check-in time (UTC). Defaults to server time if omitted. Cannot be in the future. |

```json
{
  "arrival_time": "2026-06-16T22:30:00Z"
}
```

### Response `200 OK`

```json
{
  "booking_id": 1254,
  "status": "arrived",
  "arrived_time": "2026-06-16T22:30:00Z",
  "updated_at": "2026-06-16T22:31:05Z"
}
```

### Error `400 Bad Request`

```json
{
  "error": "Cannot update attendance for a booking with status 'cancelled'."
}
```

### cURL

```bash
curl -X POST "http://127.0.0.1:8000/merchant/api/restaurants/restaurant/bookings/1254/arrive" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"arrival_time": "2026-06-16T22:30:00Z"}'
```

---

## 4. Mark Booking as No-Show

Record that the customer did not show up.

```http
POST /merchant/api/restaurants/restaurant/bookings/{booking_id}/no-show
Authorization: Bearer <token>
Content-Type: application/json
```

`PATCH` is also accepted.

### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `no_show_reason` | string (max 255) | Yes | Reason code or free-text label |
| `no_show_notes` | string | No | Additional merchant notes |

**Suggested reason codes** (free text also accepted):

| Code | Label |
|------|-------|
| `no_show_no_call` | Did not show up / no call |
| `cancelled_late` | Cancelled late |
| `invalid_booking` | Invalid booking |

```json
{
  "no_show_reason": "no_show_no_call",
  "no_show_notes": "We tried to call the customer but there was no response."
}
```

### Response `200 OK`

```json
{
  "booking_id": 1254,
  "status": "no_show",
  "no_show_reason": "no_show_no_call",
  "no_show_notes": "We tried to call the customer but there was no response.",
  "updated_at": "2026-06-16T22:32:00Z"
}
```

### cURL

```bash
curl -X POST "http://127.0.0.1:8000/merchant/api/restaurants/restaurant/bookings/1254/no-show" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"no_show_reason": "no_show_no_call", "no_show_notes": "No response to calls."}'
```

---

## 5. Update Booking Status (Existing)

Merchants can still PATCH booking status directly (e.g. `pending` → `confirmed`):

```http
PATCH /merchant/api/restaurants/restaurant/bookings/{booking_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "status": "confirmed"
}
```

Use the dedicated `/arrive` and `/no-show` endpoints for attendance tracking — they also set `arrived_time`, `no_show_reason`, and `no_show_notes`.

---

## 6. Push Notification — 1-Hour Booking Reminder

The backend sends reminders automatically. **No frontend API call is required.**

| Detail | Value |
|--------|-------|
| Trigger | Celery Beat task every 5 minutes |
| Condition | `status = confirmed`, `booking_date` is 50–60 minutes away, `reminder_sent = false` |
| Recipient | Merchant user(s) linked to the restaurant |
| Channel | Firebase Cloud Messaging (FCM) |

### FCM Data Payload (handle in Flutter)

When the merchant taps the notification, read these fields from the `data` payload:

```json
{
  "click_action": "FLUTTER_NOTIFICATION_CLICK",
  "type": "merchant_reminder",
  "booking_id": "1254",
  "restaurant_id": "4",
  "customer_name": "John Smith",
  "number_of_guests": "50",
  "booking_date": "2026-06-16T12:10:00Z",
  "notification_type": "BOOKING_REMINDER"
}
```

**Suggested Flutter handling:**

```dart
if (message.data['type'] == 'merchant_reminder') {
  final bookingId = message.data['booking_id'];
  // Navigate to booking detail / calendar for that booking
}
```

### Notification Display

| Field | Example |
|-------|---------|
| Title | `Upcoming Booking Reminder` |
| Body | `Booking for customer 'John Smith' (50 guests) starts in 1 hour.` |

---

## Error Responses

| Status | Meaning |
|--------|---------|
| `400` | Validation error or invalid attendance transition |
| `401` | Missing or expired JWT |
| `403` | User is not a merchant or does not own this restaurant |
| `404` | Booking not found or not accessible to this merchant |

**Validation error example:**
```json
{
  "arrival_time": ["Arrival time cannot be in the future."]
}
```

---

## Quick Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/merchant/api/restaurants/restaurant/bookings` | List bookings (calendar) |
| `GET` | `/merchant/api/restaurants/restaurant/bookings/{id}` | Get single booking |
| `PATCH` | `/merchant/api/restaurants/restaurant/bookings/{id}` | Update booking (e.g. confirm) |
| `POST` / `PATCH` | `/merchant/api/restaurants/restaurant/bookings/{id}/arrive` | Mark guest arrived |
| `POST` / `PATCH` | `/merchant/api/restaurants/restaurant/bookings/{id}/no-show` | Mark no-show |

---

## Interactive API Docs

Swagger UI (merchant): `http://<host>:8000/merchant/api/docs/swagger`  
ReDoc (merchant): `http://<host>:8000/merchant/api/docs/redoc`

---

## Frontend Integration Checklist

- [ ] Merchant login → store JWT access token
- [ ] Calendar screen → `GET .../bookings?start_date=&end_date=&restaurant_id=`
- [ ] Booking detail → show `status`, `arrived_time`, `no_show_reason`, `no_show_notes`
- [ ] Check-in button → `POST .../bookings/{id}/arrive` (only when `pending` or `confirmed`)
- [ ] No-show button → `POST .../bookings/{id}/no-show` with reason picker
- [ ] FCM handler → listen for `type: merchant_reminder` and deep-link to booking
- [ ] Use ISO 8601 UTC datetimes for all date/time fields
- [ ] Do not append trailing slashes to URLs
