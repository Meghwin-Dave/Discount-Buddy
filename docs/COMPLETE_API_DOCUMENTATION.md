# Complete API Documentation - Discount Buddy

## Table of Contents
1. [Base URL & Authentication](#base-url--authentication)
2. [User Flow - Complete Journey](#user-flow---complete-journey)
3. [Restaurant Flow - Complete Journey](#restaurant-flow---complete-journey)
4. [API Reference](#api-reference)
5. [Error Handling](#error-handling)

---

## Base URL & Authentication

**User Base URL**: `http://127.0.0.1:8000/user/api/`  
**Merchant Base URL**: `http://127.0.0.1:8000/merchant/api/`

**Authentication**: JWT (JSON Web Token)
- Most endpoints require authentication
- Include token in header: `Authorization: Bearer <access_token>`
- Token expires in 30 minutes
- Use refresh token to get new access token

---

## User Flow - Complete Journey

### Step 1: User Registration

**Endpoint**: `POST /user/api/users/register/`

**Request**:
```json
{
  "email": "john.doe@example.com",
  "username": "johndoe",
  "password": "SecurePass123!",
  "role": "customer"
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "email": "john.doe@example.com",
  "username": "johndoe",
  "is_merchant": false,
  "is_customer": true,
  "profile": {
    "role": "customer",
    "phone_number": "",
    "marketing_opt_in": true
  }
}
```

**cURL**:
```bash
curl -X POST http://127.0.0.1:8000/user/api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com",
    "username": "johndoe",
    "password": "SecurePass123!",
    "role": "customer"
  }'
```

---

### Step 2: User Login

**Endpoint**: `POST /user/api/users/token/`

**Request**:
```json
{
  "email": "john.doe@example.com",
  "password": "SecurePass123!"
}
```

**Response** (200 OK):
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "username": "johndoe",
  "role": "customer",
  "current_date": "2024-01-26T12:00:00Z"
}
```

**Save the `access` token for subsequent requests!**

**cURL**:
```bash
curl -X POST http://127.0.0.1:8000/user/api/users/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com",
    "password": "SecurePass123!"
  }'
```

---

### Step 3: Get User Profile

**Endpoint**: `GET /user/api/users/me/`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "id": 1,
  "email": "john.doe@example.com",
  "username": "johndoe",
  "is_merchant": false,
  "is_customer": true,
  "profile": {
    "role": "customer",
    "phone_number": "",
    "marketing_opt_in": true
  }
}
```

**cURL**:
```bash
curl -X GET http://127.0.0.1:8000/user/api/users/me/ \
  -H "Authorization: Bearer <access_token>"
```

---

### Step 4: Browse Restaurants (Home Screen)

**Endpoint**: `GET /user/api/restaurants/home/`

**Query Parameters** (all optional):
- `q` - Search query (restaurant name, cuisine, location)
- `cuisine` - Filter by cuisine ID
- `city` - Filter by city ID
- `latitude` - User's latitude (for nearby search)
- `longitude` - User's longitude (for nearby search)
- `radius` - Search radius in km (default: 10)
- `now_open` - Filter open restaurants (true/false)

**Response** (200 OK):
```json
{
  "search_query": "",
  "now_open": [
    {
      "id": 1,
      "name": "The Golden Fork",
      "slug": "the-golden-fork",
      "city_name": "London",
      "country_name": "United Kingdom",
      "latitude": "51.507400",
      "longitude": "-0.127800",
      "price_range": 4,
      "verified": true,
      "is_featured": true,
      "primary_image": "http://127.0.0.1:8000/media/restaurants/...",
      "active_deals_count": 3
    }
  ],
  "nearby": [],
  "cuisines": [
    {
      "cuisine": {
        "id": 1,
        "name": "Italian",
        "slug": "italian",
        "icon": "🍝",
        "is_active": true,
        "restaurants_count": 2
      },
      "restaurants": [...]
    }
  ],
  "top_10": [...],
  "all_restaurants": [...]
}
```

**cURL**:
```bash
curl -X GET "http://127.0.0.1:8000/user/api/restaurants/home/?city=1&now_open=true" \
  -H "Authorization: Bearer <access_token>"
```

---

### Step 5: View Restaurant Details

**Endpoint**: `GET /user/api/restaurants/restaurant-detail/{slug}/`

**Example**: `GET /api/restaurants/restaurant-detail/the-golden-fork/`

**Query Parameters** (optional):
- `latitude` - User's latitude (for distance calculation)
- `longitude` - User's longitude (for distance calculation)

**Response** (200 OK):
```json
{
  "id": 1,
  "name": "The Golden Fork",
  "slug": "the-golden-fork",
  "description": "Fine dining restaurant serving exquisite European cuisine",
  "city": {
    "id": 1,
    "name": "London",
    "slug": "london",
    "country": {
      "id": 1,
      "name": "United Kingdom",
      "code": "GB",
      "flag_emoji": "🇬🇧"
    },
    "latitude": "51.507400",
    "longitude": "-0.127800"
  },
  "address": "123 High Street, London",
  "postcode": "SW1A 1AA",
  "latitude": "51.507400",
  "longitude": "-0.127800",
  "phone": "+44 20 1234 5678",
  "email": "info@goldenfork.com",
  "website": "https://goldenfork.com",
  "categories": [...],
  "cuisines": [
    {
      "id": 1,
      "name": "Italian",
      "slug": "italian",
      "icon": "🍝"
    }
  ],
  "price_range": 4,
  "verified": true,
  "is_featured": true,
  "images": [
    {
      "id": 1,
      "image_url": "http://127.0.0.1:8000/media/restaurants/...",
      "alt_text": "The Golden Fork - Image 1",
      "is_primary": true,
      "order": 0
    }
  ],
  "reviews": [
    {
      "id": 1,
      "user_email": "user1@test.com",
      "user_name": "user1",
      "rating": 5,
      "comment": "Great food and service!",
      "is_verified": true,
      "created_at": "2024-01-20T10:00:00Z"
    }
  ],
  "menu_categories": [
    {
      "id": 1,
      "name": "Appetizers",
      "description": "Appetizers menu",
      "order": 0,
      "is_active": true,
      "items": [
        {
          "id": 1,
          "name": "Garlic Bread",
          "description": "Fresh baked bread with garlic butter",
          "price": "5.99",
          "is_vegetarian": false,
          "is_vegan": false,
          "is_gluten_free": false,
          "is_available": true,
          "image_url": null
        }
      ],
      "items_count": 2
    }
  ],
  "opening_slots": [
    {
      "id": 1,
      "day_of_week": 0,
      "day_name": "Monday",
      "opening_time": "09:00",
      "closing_time": "22:00",
      "is_closed": false
    }
  ],
  "active_deals": [
    {
      "id": 1,
      "title": "The Golden Fork Special Offer 1",
      "description": "Great deal at The Golden Fork!",
      "deal_type": "percentage",
      "restaurant_name": "The Golden Fork",
      "restaurant_slug": "the-golden-fork",
      "city_name": "London",
      "discount_percentage": 20.0,
      "minimum_spend": "30.00",
      "start_date": "2024-01-20T00:00:00Z",
      "end_date": "2024-02-20T00:00:00Z",
      "is_featured": true,
      "primary_image": null,
      "is_active": true
    }
  ],
  "average_rating": 4.5,
  "reviews_count": 3,
  "is_open_now": true,
  "is_favourite": false,
  "distance": 2.5,
  "created_at": "2024-01-15T10:00:00Z"
}
```

**cURL**:
```bash
curl -X GET "http://127.0.0.1:8000/user/api/restaurants/restaurant-detail/the-golden-fork/?latitude=51.5074&longitude=-0.1278" \
  -H "Authorization: Bearer <access_token>"
```

---

### Step 6: Add Restaurant to Favourites

**Endpoint**: `POST /user/api/restaurants/restaurant-detail/{slug}/favourite/`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (201 Created):
```json
{
  "detail": "Added to favourites"
}
```

**cURL**:
```bash
curl -X POST http://127.0.0.1:8000/user/api/restaurants/restaurant-detail/the-golden-fork/favourite/ \
  -H "Authorization: Bearer <access_token>"
```

**Remove from Favourites**:
```bash
curl -X DELETE http://127.0.0.1:8000/user/api/restaurants/restaurant-detail/the-golden-fork/favourite/ \
  -H "Authorization: Bearer <access_token>"
```

---

### Step 7: Create a Booking

**Endpoint**: `POST /user/api/restaurants/bookings/`

**Headers**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request**:
```json
{
  "restaurant": 1,
  "booking_date": "2024-02-15T19:00:00Z",
  "number_of_guests": 4,
  "special_requests": "Window seat please",
  "contact_name": "John Doe",
  "contact_phone": "+44 7123456789"
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "restaurant": 1,
  "restaurant_name": "The Golden Fork",
  "restaurant_slug": "the-golden-fork",
  "booking_date": "2024-02-15T19:00:00Z",
  "number_of_guests": 4,
  "status": "pending",
  "special_requests": "Window seat please",
  "contact_phone": "+44 7123456789",
  "contact_name": "John Doe",
  "can_cancel": true,
  "created_at": "2024-01-26T12:00:00Z"
}
```

**cURL**:
```bash
curl -X POST http://127.0.0.1:8000/user/api/restaurants/bookings/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant": 1,
    "booking_date": "2024-02-15T19:00:00Z",
    "number_of_guests": 4,
    "special_requests": "Window seat please",
    "contact_name": "John Doe",
    "contact_phone": "+44 7123456789"
  }'
```

---

### Step 8: Add a Review

**Endpoint**: `POST /user/api/restaurants/reviews/`

**Headers**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request**:
```json
{
  "restaurant": 1,
  "rating": 5,
  "comment": "Excellent food and service! Will definitely come back."
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "user": 1,
  "user_email": "john.doe@example.com",
  "user_name": "johndoe",
  "restaurant": 1,
  "rating": 5,
  "comment": "Excellent food and service! Will definitely come back.",
  "is_verified": false,
  "created_at": "2024-01-26T12:00:00Z"
}
```

**cURL**:
```bash
curl -X POST http://127.0.0.1:8000/user/api/restaurants/reviews/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant": 1,
    "rating": 5,
    "comment": "Excellent food and service!"
  }'
```

---

### Step 9: View Available Deals

**Endpoint**: `GET /user/api/restaurants/deals/`

**Query Parameters** (optional):
- `restaurant` - Filter by restaurant ID
- `deal_type` - Filter by deal type (percentage, fixed, two_for_one, other)
- `city` - Filter by city slug
- `country` - Filter by country code
- `search` - Search in title, description, restaurant name

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "title": "The Golden Fork Special Offer 1",
    "description": "Great deal at The Golden Fork!",
    "deal_type": "percentage",
    "restaurant_name": "The Golden Fork",
    "restaurant_slug": "the-golden-fork",
    "city_name": "London",
    "discount_percentage": 20.0,
    "discount_amount": null,
    "minimum_spend": "30.00",
    "start_date": "2024-01-20T00:00:00Z",
    "end_date": "2024-02-20T00:00:00Z",
    "is_featured": true,
    "primary_image": null,
    "is_active": true,
    "created_at": "2024-01-15T10:00:00Z"
  }
]
```

**cURL**:
```bash
curl -X GET "http://127.0.0.1:8000/user/api/restaurants/deals/?restaurant=1" \
  -H "Authorization: Bearer <access_token>"
```

---

### Step 10: Claim/Redeem a Deal

**Endpoint**: `POST /user/api/restaurants/deals/{id}/use/`

**Headers**:
```
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request** (optional notes):
```json
{
  "notes": "Will use this on Friday"
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "deal": {
    "id": 1,
    "title": "The Golden Fork Special Offer 1",
    "description": "Great deal at The Golden Fork!",
    "deal_type": "percentage",
    "restaurant_name": "The Golden Fork",
    "restaurant_slug": "the-golden-fork",
    "city_name": "London",
    "discount_percentage": 20.0,
    "minimum_spend": "30.00",
    "start_date": "2024-01-20T00:00:00Z",
    "end_date": "2024-02-20T00:00:00Z",
    "is_featured": true,
    "primary_image": null,
    "is_active": true
  },
  "used_at": "2024-01-26T12:00:00Z",
  "restaurant_confirmed": false,
  "notes": "Will use this on Friday",
  "created_at": "2024-01-26T12:00:00Z"
}
```

**cURL**:
```bash
curl -X POST http://127.0.0.1:8000/user/api/restaurants/deals/1/use/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Will use this on Friday"
  }'
```

---

### Step 11: View Claimed Deals

**Endpoint**: `GET /user/api/restaurants/deal-uses/`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "deal": {
      "id": 1,
      "title": "The Golden Fork Special Offer 1",
      "deal_type": "percentage",
      "restaurant_name": "The Golden Fork",
      "city_name": "London",
      "discount_percentage": 20.0,
      "start_date": "2024-01-20T00:00:00Z",
      "end_date": "2024-02-20T00:00:00Z",
      "is_active": true
    },
    "used_at": "2024-01-26T12:00:00Z",
    "restaurant_confirmed": false,
    "notes": "Will use this on Friday",
    "created_at": "2024-01-26T12:00:00Z"
  }
]
```

**cURL**:
```bash
curl -X GET http://127.0.0.1:8000/user/api/restaurants/deal-uses/ \
  -H "Authorization: Bearer <access_token>"
```

---

### Step 12: View Profile Stats

**Endpoint**: `GET /user/api/restaurants/profile/stats/`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (200 OK):
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

**cURL**:
```bash
curl -X GET http://127.0.0.1:8000/user/api/restaurants/profile/stats/ \
  -H "Authorization: Bearer <access_token>"
```

---

### Step 13: View My Bookings

**Endpoint**: `GET /user/api/restaurants/bookings/`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Query Parameters** (optional):
- `restaurant` - Filter by restaurant ID
- `status` - Filter by status (pending, confirmed, cancelled, completed)
- `ordering` - Order by (booking_date, created_at)

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "restaurant": 1,
    "restaurant_name": "The Golden Fork",
    "restaurant_slug": "the-golden-fork",
    "booking_date": "2024-02-15T19:00:00Z",
    "number_of_guests": 4,
    "status": "pending",
    "special_requests": "Window seat please",
    "contact_phone": "+44 7123456789",
    "contact_name": "John Doe",
    "can_cancel": true,
    "created_at": "2024-01-26T12:00:00Z"
  }
]
```

**cURL**:
```bash
curl -X GET "http://127.0.0.1:8000/user/api/restaurants/bookings/?status=pending" \
  -H "Authorization: Bearer <access_token>"
```

---

### Step 14: Cancel a Booking

**Endpoint**: `POST /user/api/restaurants/bookings/{id}/cancel/`

**Headers**:
```
Authorization: Bearer <access_token>
```

**Response** (200 OK):
```json
{
  "detail": "Booking cancelled successfully"
}
```

**cURL**:
```bash
curl -X POST http://127.0.0.1:8000/user/api/restaurants/bookings/1/cancel/ \
  -H "Authorization: Bearer <access_token>"
```

---

## Restaurant Flow - Complete Journey

### Step 1: Restaurant Registration

**Endpoint**: `POST /merchant/api/users/register/`

**Request**:
```json
{
  "email": "restaurant@example.com",
  "username": "restaurantowner",
  "password": "SecurePass123!",
  "role": "merchant"
}
```

**Response** (201 Created):
```json
{
  "id": 2,
  "email": "restaurant@example.com",
  "username": "restaurantowner",
  "is_merchant": true,
  "is_customer": false,
  "profile": {
    "role": "merchant",
    "phone_number": "",
    "marketing_opt_in": true
  }
}
```

**cURL**:
```bash
curl -X POST http://127.0.0.1:8000/merchant/api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "restaurant@example.com",
    "username": "restaurantowner",
    "password": "SecurePass123!",
    "role": "merchant"
  }'
```

---

### Step 2: Restaurant Login

**Endpoint**: `POST /merchant/api/users/token/`

**Request**:
```json
{
  "email": "restaurant@example.com",
  "password": "SecurePass123!"
}
```

**Response** (200 OK):
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "username": "restaurantowner",
  "role": "merchant",
  "current_date": "2024-01-26T12:00:00Z"
}
```

**cURL**:
```bash
curl -X POST http://127.0.0.1:8000/merchant/api/users/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "restaurant@example.com",
    "password": "SecurePass123!"
  }'
```

---

### Step 3: Create Restaurant

**Endpoint**: `POST /merchant/api/restaurants/restaurant/manage/`

**Headers**:
```
Authorization: Bearer <merchant_access_token>
Content-Type: application/json
```

**Request**:
```json
{
  "name": "My New Restaurant",
  "slug": "my-new-restaurant",
  "description": "A wonderful restaurant serving great food",
  "city": 1,
  "address": "456 Main Street",
  "postcode": "SW1A 2BB",
  "latitude": "51.5080",
  "longitude": "-0.1280",
  "phone": "+44 20 9876 5432",
  "email": "info@mynewrestaurant.com",
  "website": "https://mynewrestaurant.com",
  "price_range": 3,
  "opening_hours": {
    "monday": {"open": "09:00", "close": "22:00"},
    "tuesday": {"open": "09:00", "close": "22:00"}
  }
}
```

**Response** (201 Created):
```json
{
  "id": 6,
  "name": "My New Restaurant",
  "slug": "my-new-restaurant",
  "description": "A wonderful restaurant serving great food",
  "city": {
    "id": 1,
    "name": "London",
    "slug": "london",
    "country": {
      "id": 1,
      "name": "United Kingdom",
      "code": "GB"
    }
  },
  "address": "456 Main Street",
  "postcode": "SW1A 2BB",
  "latitude": "51.508000",
  "longitude": "-0.128000",
  "phone": "+44 20 9876 5432",
  "email": "info@mynewrestaurant.com",
  "website": "https://mynewrestaurant.com",
  "categories": [],
  "cuisines": [],
  "price_range": 3,
  "verified": false,
  "is_featured": false,
  "opening_hours": {
    "monday": {"open": "09:00", "close": "22:00"},
    "tuesday": {"open": "09:00", "close": "22:00"}
  },
  "images": [],
  "active_deals_count": 0,
  "is_saved": false,
  "created_at": "2024-01-26T12:00:00Z"
}
```

**cURL**:
```bash
curl -X POST http://127.0.0.1:8000/merchant/api/restaurants/restaurant/manage/ \
  -H "Authorization: Bearer <merchant_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My New Restaurant",
    "slug": "my-new-restaurant",
    "description": "A wonderful restaurant",
    "city": 1,
    "address": "456 Main Street",
    "price_range": 3
  }'
```

---

### Step 4: Add Opening Slots

**Endpoint**: `POST /merchant/api/restaurants/restaurant/opening-slots/`

**Headers**:
```
Authorization: Bearer <merchant_access_token>
Content-Type: application/json
```

**Request** (for each day):
```json
{
  "restaurant": 6,
  "day_of_week": 0,
  "opening_time": "09:00",
  "closing_time": "22:00",
  "is_closed": false
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "day_of_week": 0,
  "day_name": "Monday",
  "opening_time": "09:00",
  "closing_time": "22:00",
  "is_closed": false
}
```

**cURL**:
```bash
curl -X POST http://127.0.0.1:8000/merchant/api/restaurants/restaurant/opening-slots/ \
  -H "Authorization: Bearer <merchant_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant": 6,
    "day_of_week": 0,
    "opening_time": "09:00",
    "closing_time": "22:00",
    "is_closed": false
  }'
```

---

### Step 5: Add Menu Categories

**Endpoint**: `POST /merchant/api/restaurants/restaurant/menu/`

**Headers**:
```
Authorization: Bearer <merchant_access_token>
Content-Type: application/json
```

**Request**:
```json
{
  "restaurant": 6,
  "name": "Appetizers",
  "description": "Start your meal with our delicious appetizers",
  "order": 0,
  "is_active": true
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "name": "Appetizers",
  "description": "Start your meal with our delicious appetizers",
  "order": 0,
  "is_active": true,
  "items": [],
  "items_count": 0
}
```

**cURL**:
```bash
curl -X POST http://127.0.0.1:8000/merchant/api/restaurants/restaurant/menu/ \
  -H "Authorization: Bearer <merchant_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant": 6,
    "name": "Appetizers",
    "description": "Start your meal",
    "order": 0,
    "is_active": true
  }'
```

### Step 6: Add Menu Items

**Endpoint**: `POST /merchant/api/restaurants/restaurant/menu-items/`

**Headers**:
```
Authorization: Bearer <merchant_access_token>
Content-Type: application/json
```

**Request**:
```json
{
  "category": 1,
  "name": "Classic Burger",
  "description": "Juicy beef burger with lettuce and tomato",
  "price": "12.50",
  "is_vegetarian": false,
  "is_vegan": false,
  "is_gluten_free": false,
  "is_available": true,
  "order": 0
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "category": 1,
  "name": "Classic Burger",
  "description": "Juicy beef burger with lettuce and tomato",
  "price": "12.50",
  "is_vegetarian": false,
  "is_vegan": false,
  "is_gluten_free": false,
  "is_available": true,
  "image_url": null,
  "order": 0
}
```

**cURL**:
```bash
curl -X POST http://127.0.0.1:8000/merchant/api/restaurants/restaurant/menu-items/ \
  -H "Authorization: Bearer <merchant_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "category": 1,
    "name": "Classic Burger",
    "description": "Beef burger",
    "price": "12.50"
  }'
```

---

### Step 7: Create a Deal/Offer

**Endpoint**: `POST /merchant/api/restaurants/merchant/deals/`

**Headers**:
```
Authorization: Bearer <merchant_access_token>
Content-Type: application/json
```

**Request**:
```json
{
  "restaurant": 6,
  "title": "20% Off All Main Courses",
  "description": "Get 20% discount on all main course items",
  "deal_type": "percentage",
  "discount_percentage": 20.0,
  "minimum_spend": "30.00",
  "start_date": "2024-02-01T00:00:00Z",
  "end_date": "2024-02-28T23:59:59Z",
  "max_uses": 100,
  "max_per_user": 1,
  "terms_and_conditions": "Valid for dine-in only. Cannot be combined with other offers.",
  "is_featured": true
}
```

**Response** (201 Created):
```json
{
  "id": 14,
  "restaurant": {
    "id": 6,
    "name": "My New Restaurant",
    "slug": "my-new-restaurant",
    "city_name": "London",
    "country_name": "United Kingdom",
    "latitude": "51.508000",
    "longitude": "-0.128000",
    "price_range": 3,
    "verified": false,
    "is_featured": false,
    "primary_image": null,
    "active_deals_count": 1
  },
  "title": "20% Off All Main Courses",
  "description": "Get 20% discount on all main course items",
  "deal_type": "percentage",
  "discount_percentage": 20.0,
  "discount_amount": null,
  "minimum_spend": "30.00",
  "terms_and_conditions": "Valid for dine-in only. Cannot be combined with other offers.",
  "start_date": "2024-02-01T00:00:00Z",
  "end_date": "2024-02-28T23:59:59Z",
  "max_uses": 100,
  "used_count": 0,
  "max_per_user": 1,
  "is_featured": true,
  "images": [],
  "is_active": true,
  "can_use": false,
  "is_saved": false,
  "created_at": "2024-01-26T12:00:00Z"
}
```

**cURL**:
```bash
curl -X POST http://127.0.0.1:8000/merchant/api/restaurants/merchant/deals/ \
  -H "Authorization: Bearer <merchant_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant": 6,
    "title": "20% Off All Main Courses",
    "description": "Get 20% discount",
    "deal_type": "percentage",
    "discount_percentage": 20.0,
    "minimum_spend": "30.00",
    "start_date": "2024-02-01T00:00:00Z",
    "end_date": "2024-02-28T23:59:59Z",
    "max_uses": 100,
    "max_per_user": 1
  }'
```

---

### Step 8: View Restaurant Reviews

**Endpoint**: `GET /merchant/api/restaurants/restaurant/reviews/`

**Headers**:
```
Authorization: Bearer <merchant_access_token>
```

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "user": 1,
    "user_email": "john.doe@example.com",
    "user_name": "johndoe",
    "restaurant": 6,
    "rating": 5,
    "comment": "Excellent food and service!",
    "is_verified": false,
    "created_at": "2024-01-26T12:00:00Z"
  }
]
```

**cURL**:
```bash
curl -X GET http://127.0.0.1:8000/merchant/api/restaurants/restaurant/reviews/ \
  -H "Authorization: Bearer <merchant_access_token>"
```

---

### Step 9: View Restaurant Bookings

**Endpoint**: `GET /merchant/api/restaurants/restaurant/bookings/`

**Headers**:
```
Authorization: Bearer <merchant_access_token>
```

**Query Parameters** (optional):
- `status` - Filter by status (pending, confirmed, cancelled, completed)
- `ordering` - Order by (booking_date, created_at)

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "restaurant": 6,
    "restaurant_name": "My New Restaurant",
    "restaurant_slug": "my-new-restaurant",
    "booking_date": "2024-02-15T19:00:00Z",
    "number_of_guests": 4,
    "status": "pending",
    "special_requests": "Window seat please",
    "contact_phone": "+44 7123456789",
    "contact_name": "John Doe",
    "can_cancel": true,
    "created_at": "2024-01-26T12:00:00Z"
  }
]
```

**cURL**:
```bash
curl -X GET "http://127.0.0.1:8000/merchant/api/restaurants/restaurant/bookings/?status=pending" \
  -H "Authorization: Bearer <merchant_access_token>"
```

---

## API Reference

### Authentication Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/user/api/users/register/` | Register new customer | No |
| POST | `/user/api/users/token/` | Customer login (get JWT tokens) | No |
| POST | `/user/api/users/token/refresh/` | Refresh access token | No |
| GET | `/user/api/users/me/` | Get current customer profile | Yes |
| POST | `/merchant/api/users/register/` | Register new merchant | No |
| POST | `/merchant/api/users/token/` | Merchant login (get JWT tokens) | No |
| POST | `/merchant/api/users/token/refresh/` | Refresh access token | No |
| GET | `/merchant/api/users/me/` | Get current merchant profile | Yes |

### Public Restaurant Endpoints (User-facing)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/user/api/restaurants/home/` | Home screen data | No |
| GET | `/user/api/restaurants/restaurants/` | List restaurants | No |
| GET | `/user/api/restaurants/restaurant-detail/{slug}/` | Restaurant details | No |
| GET | `/user/api/restaurants/deals/` | List deals | No |
| GET | `/user/api/restaurants/cities/` | List cities | No |
| GET | `/user/api/restaurants/countries/` | List countries | No |
| GET | `/user/api/restaurants/cuisines/` | List cuisines | No |
| GET | `/user/api/restaurants/categories/` | List categories | No |
| GET | `/user/api/restaurants/reviews/` | List reviews | No |

### User Endpoints (Authenticated)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/user/api/restaurants/reviews/` | Add review | Yes (User) |
| GET | `/user/api/restaurants/bookings/` | List user bookings | Yes (User) |
| POST | `/user/api/restaurants/bookings/` | Create booking | Yes (User) |
| POST | `/user/api/restaurants/bookings/{id}/cancel/` | Cancel booking | Yes (User) |
| POST | `/user/api/restaurants/deals/{id}/use/` | Claim/redeem deal | Yes (User) |
| GET | `/user/api/restaurants/deal-uses/` | View claimed deals | Yes (User) |
| GET | `/user/api/restaurants/profile/stats/` | Profile statistics | Yes (User) |
| POST | `/user/api/restaurants/restaurant-detail/{slug}/favourite/` | Add to favourites | Yes (User) |
| DELETE | `/user/api/restaurants/restaurant-detail/{slug}/favourite/` | Remove from favourites | Yes (User) |

### Restaurant Management Endpoints (Merchant)

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/merchant/api/restaurants/restaurant/manage/` | List owned restaurants | Yes (Merchant) |
| POST | `/merchant/api/restaurants/restaurant/manage/` | Create restaurant | Yes (Merchant) |
| PUT | `/merchant/api/restaurants/restaurant/manage/{id}/` | Update restaurant | Yes (Merchant) |
| DELETE | `/merchant/api/restaurants/restaurant/manage/{id}/` | Delete restaurant | Yes (Merchant) |
| GET | `/merchant/api/restaurants/restaurant/menu/` | List menu categories | Yes (Merchant) |
| POST | `/merchant/api/restaurants/restaurant/menu/` | Create menu category | Yes (Merchant) |
| GET | `/merchant/api/restaurants/restaurant/opening-slots/` | List opening slots | Yes (Merchant) |
| POST | `/merchant/api/restaurants/restaurant/opening-slots/` | Create opening slot | Yes (Merchant) |
| GET | `/merchant/api/restaurants/merchant/deals/` | List restaurant deals | Yes (Merchant) |
| POST | `/merchant/api/restaurants/merchant/deals/` | Create deal | Yes (Merchant) |
| GET | `/merchant/api/restaurants/restaurant/reviews/` | View restaurant reviews | Yes (Merchant) |
| GET | `/merchant/api/restaurants/restaurant/bookings/` | View restaurant bookings | Yes (Merchant) |

---

## Error Handling

### Common HTTP Status Codes

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **204 No Content**: Request successful, no content to return
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Permission denied
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

### Error Response Format

```json
{
  "error": "Error message here",
  "detail": "Detailed error description"
}
```

### Example Error Responses

**400 Bad Request** (Validation Error):
```json
{
  "restaurant": ["This field is required."],
  "rating": ["Rating must be between 1 and 5."]
}
```

**401 Unauthorized**:
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**403 Forbidden**:
```json
{
  "detail": "You do not have permission to perform this action."
}
```

**404 Not Found**:
```json
{
  "detail": "Not found."
}
```

---

## Testing All APIs

### Quick Test Script

You can use the following Python script to test all **user-facing** APIs (customer flows):

```python
import requests

BASE_URL = "http://127.0.0.1:8000/user/api"

# 1. Register User
response = requests.post(f"{BASE_URL}/users/register/", json={
    "email": "test@example.com",
    "username": "testuser",
    "password": "test123",
    "role": "customer"
})
print("Register:", response.status_code)

# 2. Login
response = requests.post(f"{BASE_URL}/users/token/", json={
    "email": "test@example.com",
    "password": "test123"
})
token = response.json()["access"]
print("Login:", response.status_code)

headers = {"Authorization": f"Bearer {token}"}

# 3. Home Screen
response = requests.get(f"{BASE_URL}/restaurants/home/", headers=headers)
print("Home:", response.status_code)

# 4. Restaurant Detail
response = requests.get(f"{BASE_URL}/restaurants/restaurant-detail/the-golden-fork/", headers=headers)
print("Restaurant Detail:", response.status_code)

# 5. Create Booking
response = requests.post(f"{BASE_URL}/restaurants/bookings/", headers=headers, json={
    "restaurant": 1,
    "booking_date": "2024-02-15T19:00:00Z",
    "number_of_guests": 2
})
print("Create Booking:", response.status_code)

# 6. Add Review
response = requests.post(f"{BASE_URL}/restaurants/reviews/", headers=headers, json={
    "restaurant": 1,
    "rating": 5,
    "comment": "Great!"
})
print("Add Review:", response.status_code)

# 7. Claim Deal
response = requests.post(f"{BASE_URL}/restaurants/deals/1/use/", headers=headers, json={
    "notes": "Test"
})
print("Claim Deal:", response.status_code)

# 8. Profile Stats
response = requests.get(f"{BASE_URL}/restaurants/profile/stats/", headers=headers)
print("Profile Stats:", response.status_code)
print(response.json())
```

---

## Notes

1. **Token Expiry**: Access tokens expire in 30 minutes. Use refresh token to get new access token.
2. **Pagination**: List endpoints are paginated (20 items per page by default).
3. **Filtering**: Most list endpoints support filtering via query parameters.
4. **Search**: Many endpoints support search via `?search=query` parameter.
5. **Ordering**: Use `?ordering=field_name` or `?ordering=-field_name` for descending.

---

---

## Complete Flow Summary

### User Journey (End-to-End)
1. ✅ **Register** → `POST /user/api/users/register/`
2. ✅ **Login** → `POST /user/api/users/token/` → Get access token
3. ✅ **Browse** → `GET /user/api/restaurants/home/`
4. ✅ **View Details** → `GET /user/api/restaurants/restaurant-detail/{slug}/`
5. ✅ **Add Favourite** → `POST /user/api/restaurants/restaurant-detail/{slug}/favourite/`
6. ✅ **Create Booking** → `POST /user/api/restaurants/bookings/`
7. ✅ **Add Review** → `POST /user/api/restaurants/reviews/`
8. ✅ **View Deals** → `GET /user/api/restaurants/deals/`
9. ✅ **Claim Deal** → `POST /user/api/restaurants/deals/{id}/use/`
10. ✅ **View Profile Stats** → `GET /user/api/restaurants/profile/stats/`

### Restaurant Journey (End-to-End)
1. ✅ **Register as Merchant** → `POST /merchant/api/users/register/` (role: "merchant")
2. ✅ **Login** → `POST /merchant/api/users/token/` → Get access token
3. ✅ **Create Restaurant** → `POST /merchant/api/restaurants/restaurant/manage/`
4. ✅ **Add Opening Slots** → `POST /merchant/api/restaurants/restaurant/opening-slots/`
5. ✅ **Add Menu** → `POST /merchant/api/restaurants/restaurant/menu/`
6. ✅ **Create Deal** → `POST /merchant/api/restaurants/merchant/deals/`
7. ✅ **View Reviews** → `GET /merchant/api/restaurants/restaurant/reviews/`
8. ✅ **View Bookings** → `GET /merchant/api/restaurants/restaurant/bookings/`

---

## API Testing Results

**All 23 APIs Tested and Verified Working:**
- ✅ User Registration
- ✅ User Login
- ✅ Get User Profile
- ✅ Home Screen API
- ✅ List Restaurants
- ✅ Restaurant Detail
- ✅ Add to Favourites
- ✅ List Deals
- ✅ Claim/Redeem Deal
- ✅ View Claimed Deals
- ✅ Create Booking
- ✅ List Bookings
- ✅ Add Review
- ✅ Profile Stats
- ✅ List Cities (Public)
- ✅ List Countries (Public)
- ✅ List Cuisines (Public)
- ✅ List Categories (Public)
- ✅ Register Merchant
- ✅ Merchant Login
- ✅ List Owned Restaurants
- ✅ View Restaurant Reviews
- ✅ View Restaurant Bookings

**Test Script**: Run `python test_all_apis.py` to test all endpoints automatically.

---

## Mystery Guest & Leaderboard Extensions

### New Role: Mystery Guest

- **Role Key**: `mystery_guest` (stored in `UserProfile.role`)
- **Purpose**: Authorized evaluators who:
  - Receive assigned restaurants for anonymous quality audits
  - Submit standardized mystery visit reports
  - Upload evidence (photos/receipts)
  - Cannot edit restaurant data or change reports after submission

### Leaderboard Score

**Formula**:

\[
\text{Leaderboard Score} = (\text{User Rating} \times 40\%) + (\text{Mystery Score} \times 60\%)
\]

- **User Rating**:
  - Average review rating (0–5), normalised to 0–100.
- **Mystery Score**:
  - Latest `MysteryVisit.overall_score` (0–100).
  - Freshness decay: older visits contribute less using an exponential decay with ~90‑day time constant.
- **Exposed Field**:
  - `leaderboard_score` (float, 0–100) on restaurant cards.
- **Visible In**:
  - `GET /user/api/restaurants/home/`
  - `GET /user/api/restaurants/restaurants/`

Example restaurant card snippet:

```json
{
  "id": 1,
  "name": "The Golden Fork",
  "slug": "the-golden-fork",
  "city_name": "London",
  "country_name": "United Kingdom",
  "leaderboard_score": 87.5,
  "...": "..."
}
```

### Mystery Guest APIs

All endpoints below require:

- **Auth**: `Authorization: Bearer <access_token>`
- **Role**: `mystery_guest`

#### 1. List Assigned / Historical Visits

- **Method**: `GET`
- **Endpoint**: `/user/api/restaurants/mystery-visits`
- **Query Params (optional)**:
  - `status` – `assigned`, `in_progress`, `submitted`, `cancelled`
  - `restaurant` – restaurant ID

**Response 200 OK** (paginated):

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 10,
      "restaurant": 6,
      "restaurant_name": "My New Restaurant",
      "restaurant_city": "London",
      "mystery_guest": 42,
      "scheduled_for": "2024-04-10T19:00:00Z",
      "started_at": null,
      "submitted_at": null,
      "status": "assigned",
      "overall_score": null,
      "is_risk_flagged": false,
      "comments": "",
      "scores": [],
      "evidence": [],
      "created_at": "2024-04-01T10:00:00Z"
    }
  ]
}
```

#### 2. Get Visit Detail

- **Method**: `GET`
- **Endpoint**: `/user/api/restaurants/mystery-visits/{id}/`

Returns full visit details including section scores and evidence.

#### 3. Start a Visit

- **Method**: `POST`
- **Endpoint**: `/user/api/restaurants/mystery-visits/{id}/start/`
- **Body**: _empty_

**Response 200 OK**:

```json
{
  "id": 10,
  "status": "in_progress",
  "started_at": "2024-04-10T18:55:00Z",
  "...": "..."
}
```

#### 4. Submit Mystery Visit Report

- **Method**: `POST`
- **Endpoint**: `/user/api/restaurants/mystery-visits/{id}/submit/`
- **Headers**: `Content-Type: application/json`

**Request Body**:

```json
{
  "pre_visit_score": 8,
  "pre_visit_comment": "App & deal were clear.",
  "ambience_score": 9,
  "ambience_comment": "Nice decor and lighting.",
  "service_score": 8,
  "service_comment": "Friendly, slightly slow.",
  "food_score": 9,
  "food_comment": "Great taste and presentation.",
  "discount_experience_score": 10,
  "discount_experience_comment": "Staff applied QR smoothly.",
  "hygiene_score": 9,
  "hygiene_comment": "Tables and washrooms very clean.",
  "is_risk_flagged": false,
  "comments": "Strong overall experience."
}
```

All `*_score` fields are required integers (`0–10`); comments and `is_risk_flagged` are optional.

**Response 200 OK**:

```json
{
  "id": 10,
  "restaurant": 6,
  "status": "submitted",
  "overall_score": 88.0,
  "is_risk_flagged": false,
  "comments": "Strong overall experience.",
  "scores": [
    {
      "section": "pre_visit",
      "section_display": "Pre-Visit",
      "score": 8,
      "comment": "App & deal were clear."
    }
    // ... other sections
  ],
  "submitted_at": "2024-04-10T20:30:00Z",
  "created_at": "2024-04-01T10:00:00Z"
}
```

Once submitted, the visit is immutable via the API.

#### 5. Upload Evidence

- **Method**: `POST`
- **Endpoint**: `/user/api/restaurants/mystery-visits/{id}/evidence/`
- **Headers**: `Content-Type: multipart/form-data`

**Form Fields**:

- `file` – required (image/PDF/etc.)
- `description` – optional text

**Response 201 Created**:

```json
{
  "id": 5,
  "file": "mystery_evidence/2024/04/10/receipt.jpg",
  "file_url": "http://127.0.0.1:8000/media/mystery_evidence/2024/04/10/receipt.jpg",
  "description": "Final bill with discount applied",
  "created_at": "2024-04-10T20:20:00Z"
}
```

---

**Documentation Version**: 1.2  
**Last Updated**: 2026-02-25  
**User API Base URL**: `http://127.0.0.1:8000/user/api/`  
**Merchant API Base URL**: `http://127.0.0.1:8000/merchant/api/`  
**Status**: ✅ All APIs Tested and Working
