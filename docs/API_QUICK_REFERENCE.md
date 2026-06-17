# API Quick Reference Guide

## 🔐 Authentication

```bash
# User Register
POST /user/api/users/register/
Body: {"email": "...", "username": "...", "password": "...", "role": "customer"}

# User Login
POST /user/api/users/token/
Body: {"email": "...", "password": "..."}
Response: {"access": "...", "refresh": "..."}

# Merchant Register
POST /merchant/api/users/register/
Body: {"email": "...", "username": "...", "password": "...", "role": "merchant"}

# Merchant Login
POST /merchant/api/users/token/
Body: {"email": "...", "password": "..."}
Response: {"access": "...", "refresh": "..."}

# Use Token
Header: Authorization: Bearer <access_token>
```

---

## 👤 User Flow

| Step | Method | Endpoint | Auth |
|------|--------|----------|------|
| 1. Register | POST | `/user/api/users/register/` | No |
| 2. Login | POST | `/user/api/users/token/` | No |
| 3. Home Screen | GET | `/user/api/restaurants/home/` | Optional |
| 4. Restaurant Detail | GET | `/user/api/restaurants/restaurant-detail/{slug}/` | No |
| 5. Add Favourite | POST | `/user/api/restaurants/restaurant-detail/{slug}/favourite/` | Yes |
| 6. Create Booking | POST | `/user/api/restaurants/bookings/` | Yes |
| 7. Add Review | POST | `/user/api/restaurants/reviews/` | Yes |
| 8. View Deals | GET | `/user/api/restaurants/deals/` | No |
| 9. Claim Deal | POST | `/user/api/restaurants/deals/{id}/use/` | Yes |
| 10. Profile Stats | GET | `/user/api/restaurants/profile/stats/` | Yes |

---

## 🏪 Restaurant Flow

| Step | Method | Endpoint | Auth |
|------|--------|----------|------|
| 1. Register (Merchant) | POST | `/merchant/api/users/register/` (role: "merchant") | No |
| 2. Login | POST | `/merchant/api/users/token/` | No |
| 3. Create Restaurant | POST | `/merchant/api/restaurants/restaurant/manage/` | Yes |
| 4. Add Opening Slots | POST | `/merchant/api/restaurants/restaurant/opening-slots/` | Yes |
| 5. Add Menu Category | POST | `/merchant/api/restaurants/restaurant/menu/` | Yes |
| 5a. Add Menu Item | POST | `/merchant/api/restaurants/restaurant/menu-items/` | Yes |
| 6. Create Deal | POST | `/merchant/api/restaurants/merchant/deals/` | Yes |
| 7. View Reviews | GET | `/merchant/api/restaurants/restaurant/reviews/` | Yes |
| 8. View Bookings | GET | `/merchant/api/restaurants/restaurant/bookings` | Yes |
| 8a. Mark Arrived | POST/PATCH | `/merchant/api/restaurants/restaurant/bookings/{id}/arrive` | Yes |
| 8b. Mark No-Show | POST/PATCH | `/merchant/api/restaurants/restaurant/bookings/{id}/no-show` | Yes |

---

## 📋 All Endpoints

### Authentication
- `POST /user/api/users/register/` - Register user
- `POST /user/api/users/token/` - User login (get JWT)
- `POST /user/api/users/token/refresh/` - Refresh token
- `GET /user/api/users/me/` - Get user profile
- `POST /merchant/api/users/register/` - Register merchant
- `POST /merchant/api/users/token/` - Merchant login (get JWT)
- `POST /merchant/api/users/token/refresh/` - Refresh token
- `GET /merchant/api/users/me/` - Get merchant profile

### Public (User-facing)
- `GET /user/api/restaurants/home/` - Home screen
- `GET /user/api/restaurants/restaurants/` - List restaurants
- `GET /user/api/restaurants/restaurant-detail/{slug}/` - Restaurant detail
- `GET /user/api/restaurants/deals/` - List deals
- `GET /user/api/restaurants/cities/` - List cities
- `GET /user/api/restaurants/countries/` - List countries
- `GET /user/api/restaurants/cuisines/` - List cuisines
- `GET /user/api/restaurants/categories/` - List categories
- `GET /user/api/restaurants/reviews/` - List reviews

### User (Authenticated)
- `POST /user/api/restaurants/reviews/` - Add review
- `GET /user/api/restaurants/bookings/` - List bookings
- `POST /user/api/restaurants/bookings/` - Create booking
- `POST /user/api/restaurants/bookings/{id}/cancel/` - Cancel booking
- `POST /user/api/restaurants/deals/{id}/use/` - Claim deal
- `GET /user/api/restaurants/deal-uses/` - View claimed deals
- `GET /user/api/restaurants/profile/stats/` - Profile stats
- `POST /user/api/restaurants/restaurant-detail/{slug}/favourite/` - Add favourite
- `DELETE /user/api/restaurants/restaurant-detail/{slug}/favourite/` - Remove favourite

### Restaurant Management (Merchant)
- `GET /merchant/api/restaurants/restaurant/manage/` - List restaurants
- `POST /merchant/api/restaurants/restaurant/manage/` - Create restaurant
- `PUT /merchant/api/restaurants/restaurant/manage/{id}/` - Update restaurant
- `DELETE /merchant/api/restaurants/restaurant/manage/{id}/` - Delete restaurant
- `GET /merchant/api/restaurants/restaurant/menu/` - List menu categories
- `POST /merchant/api/restaurants/restaurant/menu/` - Create menu category
- `GET /merchant/api/restaurants/restaurant/menu-items/` - List menu items
- `POST /merchant/api/restaurants/restaurant/menu-items/` - Create menu item
- `GET /merchant/api/restaurants/restaurant/opening-slots/` - List opening slots
- `POST /merchant/api/restaurants/restaurant/opening-slots/` - Create opening slot
- `GET /merchant/api/restaurants/merchant/deals/` - List deals
- `POST /merchant/api/restaurants/merchant/deals/` - Create deal
- `GET /merchant/api/restaurants/restaurant/reviews/` - View reviews
- `GET /merchant/api/restaurants/restaurant/bookings` - View bookings (calendar; `?start_date=&end_date=&restaurant_id=`)
- `POST /merchant/api/restaurants/restaurant/bookings/{id}/arrive` - Mark guest arrived
- `POST /merchant/api/restaurants/restaurant/bookings/{id}/no-show` - Mark no-show

> **Full merchant booking guide:** see `docs/MERCHANT_BOOKING_API.md`

---

## 🧪 Test Credentials

**Superuser**: `admin@discountbuddy.com` / `admin123`  
**Test User**: `user1@test.com` / `test123`  
**Test Merchant**: `merchant@test.com` / `test123`

---

## 📝 Example cURL Commands

```bash
# User Register
curl -X POST http://127.0.0.1:8000/user/api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"test","password":"test123","role":"customer"}'

# User Login
curl -X POST http://127.0.0.1:8000/user/api/users/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Home Screen (with token)
curl -X GET "http://127.0.0.1:8000/user/api/restaurants/home/?city=1" \
  -H "Authorization: Bearer <token>"

# Restaurant Detail
curl -X GET http://127.0.0.1:8000/user/api/restaurants/restaurant-detail/the-golden-fork/ \
  -H "Authorization: Bearer <token>"

# Claim Deal
curl -X POST http://127.0.0.1:8000/user/api/restaurants/deals/1/use/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"notes":"Will use on Friday"}'
```

---

## ✅ Status

**All 23 APIs Tested and Verified Working!**

See `COMPLETE_API_DOCUMENTATION.md` for detailed documentation with request/response examples.
