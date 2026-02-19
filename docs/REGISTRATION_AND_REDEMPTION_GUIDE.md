# Registration & Deal Redemption Guide

## Email configuration

OTP emails are sent via Gmail SMTP. Configure your `.env`:

```env
# Gmail – use App Password (not your regular password)
# Create one at: https://myaccount.google.com/apppasswords
EMAIL_HOST_USER=meghwindave04@gmail.com
EMAIL_HOST_PASSWORD=your-16-char-app-password
DEFAULT_FROM_EMAIL=Discount Buddy <meghwindave04@gmail.com>
```

Settings in `settings.py` already use these variables. Ensure 2-Step Verification is enabled on the Gmail account before generating an App Password.

---

## Two-stage OTP registration

Registration has two steps: (1) request OTP, (2) verify OTP and set password.

### Stage 1 – Request OTP

**Endpoint:** `POST /user/api/users/register/init`  
**Auth:** None

**Request:**
```json
{
  "email": "user@example.com",
  "role": "customer"
}
```

- `role`: `"customer"` (default) or `"merchant"`
- `email`: used as both login identifier and username

**Response (200):**
```json
{
  "detail": "Verification code sent to your email."
}
```

A 4-digit OTP is emailed and expires in 10 minutes. Previous pending OTPs for that email are invalidated.

---

### Stage 2 – Verify OTP and complete registration

**Endpoint:** `POST /user/api/users/register/complete`  
**Auth:** None

**Request:**
```json
{
  "email": "user@example.com",
  "otp": "0423",
  "password": "SecurePass123"
}
```

- `otp`: 4-digit code from email
- `password`: minimum 6 characters

**Response (201):**
```json
{
  "id": 5,
  "email": "user@example.com",
  "username": "user",
  "is_merchant": false,
  "is_customer": true,
  "profile": { "role": "customer", "phone_number": "", "marketing_opt_in": true }
}
```

**Errors:**
- `400` – Invalid/expired OTP, email already registered, or validation error

---

## Deal claim (customer)

When a customer claims a deal, a redemption record is created with a 6-digit code and QR image.

**Endpoint:** `POST /user/api/restaurants/deals/{deal_id}/use`  
**Auth:** Bearer token (customer)

**Request:**
```json
{
  "notes": "Will use on Friday"
}
```

**Response (201):**
```json
{
  "id": 12,
  "deal": { "id": 1, "title": "20% off", "restaurant_name": "...", ... },
  "used_at": "2026-02-05T14:30:00Z",
  "restaurant_confirmed": false,
  "notes": "Will use on Friday",
  "redemption_code": "847291",
  "qr_code": "/media/deal_redemptions/2026/02/05/qr.png",
  "qr_code_url": "http://127.0.0.1:8000/media/deal_redemptions/2026/02/05/qr.png",
  "is_redeemed": false,
  "redeemed_at": null,
  "created_at": "2026-02-05T14:30:00Z"
}
```

- `redemption_code`: 6-digit numeric code for manual entry at the restaurant
- `qr_code` / `qr_code_url`: QR image encoding `DEALUSE:{id}:{code}` (e.g. `DEALUSE:12:847291`)
- Either the QR scan or the 6-digit code can be used for redemption

---

## Deal redemption (restaurant/merchant)

Restaurant staff redeem a deal via QR scan or manual code entry.

**Endpoint:** `POST /merchant/api/restaurants/deals/redeem`  
**Auth:** Bearer token (restaurant owner/merchant)

**Request (by code):**
```json
{
  "redemption_code": "847291"
}
```

**Request (by QR payload):**
```json
{
  "qr_data": "DEALUSE:12:847291"
}
```

Provide either `redemption_code` or `qr_data`; both reference the same redemption.

**Success (200):**
```json
{
  "success": true,
  "reason": "Deal redeemed successfully.",
  "id": 12,
  "deal": { ... },
  "redemption_code": "847291",
  "is_redeemed": true,
  "redeemed_at": "2026-02-05T15:00:00Z",
  ...
}
```

**Failure (400):**
```json
{
  "success": false,
  "reason": "Invalid verification code."
}
```

**Already redeemed (409):**
```json
{
  "success": false,
  "reason": "This deal has already been redeemed."
}
```

**Validation rules:**
- Code/QR must exist
- Deal must not already be redeemed
- Deal must still be active (within validity dates)
- Actor must own the restaurant (RestaurantProfile or Merchant)

---

## Quick reference

| Action | Endpoint | Method |
|--------|----------|--------|
| Request OTP | `/user/api/users/register/init` | POST |
| Complete registration | `/user/api/users/register/complete` | POST |
| Claim deal | `/user/api/restaurants/deals/{id}/use` | POST |
| Redeem deal | `/merchant/api/restaurants/deals/redeem` | POST |
