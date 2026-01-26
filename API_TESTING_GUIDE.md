# API Testing Guide

## Dummy Data Created

The following dummy data has been created for testing:

### Users
- **Superuser**: `admin@discountbuddy.com` / `admin123`
- **Merchant**: `merchant@test.com` / `test123`
- **Regular Users**: `user1@test.com` to `user5@test.com` / `test123`

### Data Summary
- ✅ 3 Countries (UK, US, India)
- ✅ 4 Cities (London, Manchester, New York, Mumbai)
- ✅ 5 Restaurant Categories
- ✅ 6 Cuisines (Italian, Chinese, Indian, Mexican, Japanese, American)
- ✅ 5 Restaurants (with images, opening slots, menus)
- ✅ 13 Deals (various types: percentage, fixed, two-for-one)
- ✅ Reviews (multiple reviews per restaurant)
- ✅ Bookings (past and upcoming)
- ✅ Saved Restaurants (favourites)
- ✅ Saved Deals
- ✅ Deal Uses (claimed deals)
- ✅ Menu Categories & Items (for each restaurant)
- ✅ Restaurant Profile (merchant linked to restaurant)

---

## Testing APIs

### 1. Get JWT Token (Authentication)

**Endpoint**: `POST /api/users/token/`

**Request**:
```json
{
  "email": "user1@test.com",
  "password": "test123"
}
```

**Response**:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "username": "user1",
  "role": "customer"
}
```

**Use the `access` token in subsequent requests:**
```
Authorization: Bearer <access_token>
```

---

### 2. Home Screen API

**Endpoint**: `GET /api/restaurants/home/`

**Query Parameters** (all optional):
- `q` - Search query
- `cuisine` - Cuisine ID
- `city` - City ID
- `latitude` - User latitude
- `longitude` - User longitude
- `radius` - Search radius in km (default: 10)
- `now_open` - Filter open restaurants (true/false)

**Example**:
```
GET /api/restaurants/home/?city=1&now_open=true
```

**Response includes**:
- `now_open` - Currently open restaurants
- `nearby` - Nearby restaurants (if lat/lng provided)
- `cuisines` - Restaurants grouped by cuisine
- `top_10` - Top 10 restaurants in city
- `all_restaurants` - All restaurants in card format

---

### 3. Restaurant Detail API

**Endpoint**: `GET /api/restaurants/restaurant-detail/{slug}/`

**Example**:
```
GET /api/restaurants/restaurant-detail/the-golden-fork/
```

**Response includes**:
- Restaurant info
- Location (lat/lng)
- Open/close status
- Opening slots
- Reviews (with ratings)
- Active offers
- Photo carousel
- Menu (categories with items)
- Average rating
- Is favourite status

**Toggle Favourite**:
- `POST /api/restaurants/restaurant-detail/{slug}/favourite/` - Add to favourites
- `DELETE /api/restaurants/restaurant-detail/{slug}/favourite/` - Remove from favourites

**Share**:
- `GET /api/restaurants/restaurant-detail/{slug}/share/` - Get shareable link

---

### 4. Reviews API

**List Reviews**:
```
GET /api/restaurants/reviews/?restaurant=1&rating=5
```

**Add Review** (User only):
```
POST /api/restaurants/reviews/
Authorization: Bearer <token>

{
  "restaurant": 1,
  "rating": 5,
  "comment": "Excellent food and service!"
}
```

**Update Review**:
```
PUT /api/restaurants/reviews/{id}/
Authorization: Bearer <token>

{
  "restaurant": 1,
  "rating": 4,
  "comment": "Updated review"
}
```

---

### 5. Bookings API

**List Bookings** (User's bookings):
```
GET /api/restaurants/bookings/
Authorization: Bearer <token>
```

**Create Booking**:
```
POST /api/restaurants/bookings/
Authorization: Bearer <token>

{
  "restaurant": 1,
  "booking_date": "2024-02-15T19:00:00Z",
  "number_of_guests": 4,
  "special_requests": "Window seat please",
  "contact_name": "John Doe",
  "contact_phone": "+44 7123456789"
}
```

**Cancel Booking**:
```
POST /api/restaurants/bookings/{id}/cancel/
Authorization: Bearer <token>
```

---

### 6. Profile Stats API

**Endpoint**: `GET /api/restaurants/profile/stats/`
**Auth**: Bearer token required

**Response**:
```json
{
  "deals_claimed": 3,
  "money_saved": 45.50,
  "user_level": "Silver",
  "restaurants_visited": 5,
  "cities_visited": 2,
  "favourite_restaurants": 3,
  "reviews_written": 4
}
```

---

### 7. Cuisines API

**Endpoint**: `GET /api/restaurants/cuisines/`

**Response**: List of all active cuisines

---

### 8. Restaurant Management APIs (Merchant/Restaurant Owner)

**Login as Merchant**:
```
POST /api/users/token/
{
  "email": "merchant@test.com",
  "password": "test123"
}
```

**List Owned Restaurants**:
```
GET /api/restaurants/restaurant/manage/
Authorization: Bearer <merchant_token>
```

**View Restaurant Reviews**:
```
GET /api/restaurants/restaurant/reviews/
Authorization: Bearer <merchant_token>
```

**View Restaurant Bookings**:
```
GET /api/restaurants/restaurant/bookings/?status=confirmed
Authorization: Bearer <merchant_token>
```

**Manage Menu**:
```
GET /api/restaurants/restaurant/menu/
POST /api/restaurants/restaurant/menu/
PUT /api/restaurants/restaurant/menu/{id}/
Authorization: Bearer <merchant_token>
```

**Manage Opening Slots**:
```
GET /api/restaurants/restaurant/opening-slots/
POST /api/restaurants/restaurant/opening-slots/
Authorization: Bearer <merchant_token>

{
  "restaurant": 1,
  "day_of_week": 0,
  "opening_time": "09:00",
  "closing_time": "22:00",
  "is_closed": false
}
```

---

## Testing with Django Admin

1. **Start the server**:
   ```bash
   python manage.py runserver
   ```

2. **Access Admin**: http://127.0.0.1:8000/admin/

3. **Login**: `admin@discountbuddy.com` / `admin123`

4. **Browse all models**:
   - Countries & Cities
   - Restaurants (with images, menus, opening slots)
   - Deals
   - Reviews
   - Bookings
   - Users
   - Cuisines
   - Menu Categories & Items

---

## Testing with API Tools

### Using Postman/Insomnia:

1. **Get Token**:
   - Method: POST
   - URL: `http://127.0.0.1:8000/api/users/token/`
   - Body (JSON):
     ```json
     {
       "email": "user1@test.com",
       "password": "test123"
     }
     ```

2. **Use Token**:
   - Add Header: `Authorization: Bearer <access_token>`

3. **Test Endpoints**:
   - Home Screen: `GET http://127.0.0.1:8000/api/restaurants/home/`
   - Restaurant Detail: `GET http://127.0.0.1:8000/api/restaurants/restaurant-detail/the-golden-fork/`
   - Create Review: `POST http://127.0.0.1:8000/api/restaurants/reviews/`
   - Create Booking: `POST http://127.0.0.1:8000/api/restaurants/bookings/`
   - Profile Stats: `GET http://127.0.0.1:8000/api/restaurants/profile/stats/`

---

## Testing with Swagger/OpenAPI

1. **Start the server**: `python manage.py runserver`

2. **Access Swagger**: http://127.0.0.1:8000/api/docs/swagger/

3. **Access ReDoc**: http://127.0.0.1:8000/api/docs/redoc/

4. **Authenticate**: Click "Authorize" button and enter:
   ```
   Bearer <your_access_token>
   ```

---

## Sample Restaurant Slugs

- `the-golden-fork`
- `spice-garden`
- `bella-italia`
- `dragon-palace`
- `mumbai-spice`

---

## Notes

- All user passwords: `test123`
- Superuser password: `admin123`
- Merchant password: `test123`
- JWT tokens expire after 30 minutes (refresh token valid for 7 days)
- Some endpoints require authentication (check permissions in code)
- Image fields may be empty (no actual image files uploaded, but structure is ready)

---

## Quick Test Checklist

- [ ] Get JWT token
- [ ] Home screen API (with filters)
- [ ] Restaurant detail API
- [ ] Add/update review
- [ ] Create booking
- [ ] Cancel booking
- [ ] Profile stats
- [ ] Toggle favourite
- [ ] Merchant login
- [ ] View restaurant reviews (as merchant)
- [ ] View restaurant bookings (as merchant)
- [ ] Admin interface access

---

**Happy Testing!** 🚀
