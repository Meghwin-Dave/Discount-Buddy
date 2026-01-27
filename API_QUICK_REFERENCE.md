# API Quick Reference Guide

## 🔐 Authentication

```bash
# Register
POST /api/users/register/
Body: {"email": "...", "username": "...", "password": "...", "role": "customer"}

# Login
POST /api/users/token/
Body: {"email": "...", "password": "..."}
Response: {"access": "...", "refresh": "..."}

# Use Token
Header: Authorization: Bearer <access_token>
```

---

## 👤 User Flow

| Step | Method | Endpoint | Auth |
|------|--------|----------|------|
| 1. Register | POST | `/api/users/register/` | No |
| 2. Login | POST | `/api/users/token/` | No |
| 3. Home Screen | GET | `/api/restaurants/home/` | Optional |
| 4. Restaurant Detail | GET | `/api/restaurants/restaurant-detail/{slug}/` | No |
| 5. Add Favourite | POST | `/api/restaurants/restaurant-detail/{slug}/favourite/` | Yes |
| 6. Create Booking | POST | `/api/restaurants/bookings/` | Yes |
| 7. Add Review | POST | `/api/restaurants/reviews/` | Yes |
| 8. View Deals | GET | `/api/restaurants/deals/` | No |
| 9. Claim Deal | POST | `/api/restaurants/deals/{id}/use/` | Yes |
| 10. Profile Stats | GET | `/api/restaurants/profile/stats/` | Yes |

---

## 🏪 Restaurant Flow

| Step | Method | Endpoint | Auth |
|------|--------|----------|------|
| 1. Register (Merchant) | POST | `/api/users/register/` (role: "merchant") | No |
| 2. Login | POST | `/api/users/token/` | No |
| 3. Create Restaurant | POST | `/api/restaurants/restaurant/manage/` | Yes |
| 4. Add Opening Slots | POST | `/api/restaurants/restaurant/opening-slots/` | Yes |
| 5. Add Menu Category | POST | `/api/restaurants/restaurant/menu/` | Yes |
| 6. Create Deal | POST | `/api/restaurants/merchant/deals/` | Yes |
| 7. View Reviews | GET | `/api/restaurants/restaurant/reviews/` | Yes |
| 8. View Bookings | GET | `/api/restaurants/restaurant/bookings/` | Yes |

---

## 📋 All Endpoints

### Authentication
- `POST /api/users/register/` - Register user/restaurant
- `POST /api/users/token/` - Login (get JWT)
- `POST /api/users/token/refresh/` - Refresh token
- `GET /api/users/me/` - Get profile

### Public
- `GET /api/restaurants/home/` - Home screen
- `GET /api/restaurants/restaurants/` - List restaurants
- `GET /api/restaurants/restaurant-detail/{slug}/` - Restaurant detail
- `GET /api/restaurants/deals/` - List deals
- `GET /api/restaurants/cities/` - List cities
- `GET /api/restaurants/countries/` - List countries
- `GET /api/restaurants/cuisines/` - List cuisines
- `GET /api/restaurants/categories/` - List categories
- `GET /api/restaurants/reviews/` - List reviews

### User (Authenticated)
- `POST /api/restaurants/reviews/` - Add review
- `GET /api/restaurants/bookings/` - List bookings
- `POST /api/restaurants/bookings/` - Create booking
- `POST /api/restaurants/bookings/{id}/cancel/` - Cancel booking
- `POST /api/restaurants/deals/{id}/use/` - Claim deal
- `GET /api/restaurants/deal-uses/` - View claimed deals
- `GET /api/restaurants/profile/stats/` - Profile stats
- `POST /api/restaurants/restaurant-detail/{slug}/favourite/` - Add favourite
- `DELETE /api/restaurants/restaurant-detail/{slug}/favourite/` - Remove favourite

### Restaurant Management (Merchant)
- `GET /api/restaurants/restaurant/manage/` - List restaurants
- `POST /api/restaurants/restaurant/manage/` - Create restaurant
- `PUT /api/restaurants/restaurant/manage/{id}/` - Update restaurant
- `DELETE /api/restaurants/restaurant/manage/{id}/` - Delete restaurant
- `GET /api/restaurants/restaurant/menu/` - List menu categories
- `POST /api/restaurants/restaurant/menu/` - Create menu category
- `GET /api/restaurants/restaurant/opening-slots/` - List opening slots
- `POST /api/restaurants/restaurant/opening-slots/` - Create opening slot
- `GET /api/restaurants/merchant/deals/` - List deals
- `POST /api/restaurants/merchant/deals/` - Create deal
- `GET /api/restaurants/restaurant/reviews/` - View reviews
- `GET /api/restaurants/restaurant/bookings/` - View bookings

---

## 🧪 Test Credentials

**Superuser**: `admin@discountbuddy.com` / `admin123`  
**Test User**: `user1@test.com` / `test123`  
**Test Merchant**: `merchant@test.com` / `test123`

---

## 📝 Example cURL Commands

```bash
# Register
curl -X POST http://127.0.0.1:8000/api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"test","password":"test123","role":"customer"}'

# Login
curl -X POST http://127.0.0.1:8000/api/users/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Home Screen (with token)
curl -X GET "http://127.0.0.1:8000/api/restaurants/home/?city=1" \
  -H "Authorization: Bearer <token>"

# Restaurant Detail
curl -X GET http://127.0.0.1:8000/api/restaurants/restaurant-detail/the-golden-fork/ \
  -H "Authorization: Bearer <token>"

# Claim Deal
curl -X POST http://127.0.0.1:8000/api/restaurants/deals/1/use/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"notes":"Will use on Friday"}'
```

---

## ✅ Status

**All 23 APIs Tested and Verified Working!**

See `COMPLETE_API_DOCUMENTATION.md` for detailed documentation with request/response examples.
