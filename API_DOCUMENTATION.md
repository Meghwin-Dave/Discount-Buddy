# Discount Buddy API Documentation

## Base URL
```
/api/restaurants/
```

## Authentication
Most endpoints are public (AllowAny). For user-specific actions (saving restaurants/deals, using deals), JWT authentication is required.

Get token:
```
POST /api/users/token/
Body: {"email": "user@example.com", "password": "password"}
Response: {"access": "...", "refresh": "..."}
```

Use token:
```
Header: Authorization: Bearer <access_token>
```

---

## Countries

### List Countries
```
GET /api/restaurants/countries/
```
Returns list of all countries with cities count.

**Response:**
```json
[
  {
    "id": 1,
    "name": "United Kingdom",
    "code": "GB",
    "flag_emoji": "🇬🇧",
    "cities_count": 6,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

---

## Cities

### List Cities
```
GET /api/restaurants/cities/
```

**Query Parameters:**
- `country` - Filter by country ID
- `is_active` - Filter by active status (true/false)
- `search` - Search by city or country name
- `ordering` - Order by: name, created_at

**Response:**
```json
[
  {
    "id": 1,
    "name": "London",
    "slug": "london",
    "country": {
      "id": 1,
      "name": "United Kingdom",
      "code": "GB",
      "flag_emoji": "🇬🇧"
    },
    "latitude": "51.5074",
    "longitude": "-0.1278",
    "is_active": true,
    "restaurants_count": 150,
    "active_deals_count": 45,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

---

## Restaurant Categories

### List Categories
```
GET /api/restaurants/categories/
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "Italian",
    "slug": "italian",
    "icon": "🍝",
    "restaurants_count": 25,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

---

## Restaurants

### List Restaurants
```
GET /api/restaurants/restaurants/
```

**Query Parameters:**
- `city` - Filter by city ID
- `city_slug` - Filter by city slug
- `country_code` - Filter by country code
- `verified` - Filter by verified status (true/false)
- `is_featured` - Filter by featured status (true/false)
- `categories` - Filter by category IDs (multiple)
- `category` - Filter by category slug
- `min_price` - Minimum price range (1-4)
- `max_price` - Maximum price range (1-4)
- `has_deals` - Filter restaurants with active deals (true/false)
- `latitude` - Filter nearby restaurants (requires longitude)
- `longitude` - Filter nearby restaurants (requires latitude)
- `radius` - Radius in km for nearby filter (default: 10)
- `search` - Search by name, description, address, city name
- `ordering` - Order by: name, created_at, is_featured

**Response:**
```json
{
  "count": 100,
  "next": "http://api/restaurants/restaurants/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Pizza Palace",
      "slug": "pizza-palace",
      "city_name": "London",
      "country_name": "United Kingdom",
      "latitude": "51.5074",
      "longitude": "-0.1278",
      "price_range": 2,
      "verified": true,
      "is_featured": true,
      "primary_image": "http://media/restaurants/image.jpg",
      "active_deals_count": 3
    }
  ]
}
```

### Get Restaurant Details
```
GET /api/restaurants/restaurants/{id}/
```

**Response:**
```json
{
  "id": 1,
  "name": "Pizza Palace",
  "slug": "pizza-palace",
  "description": "Authentic Italian pizza",
  "city": {
    "id": 1,
    "name": "London",
    "slug": "london",
    "country": {...}
  },
  "address": "123 Main St",
  "postcode": "SW1A 1AA",
  "latitude": "51.5074",
  "longitude": "-0.1278",
  "phone": "+44 20 1234 5678",
  "email": "info@pizzapalace.com",
  "website": "https://pizzapalace.com",
  "categories": [
    {"id": 1, "name": "Italian", "slug": "italian", "icon": "🍝"}
  ],
  "price_range": 2,
  "verified": true,
  "is_featured": true,
  "opening_hours": {
    "monday": "10:00-22:00",
    "tuesday": "10:00-22:00"
  },
  "images": [
    {
      "id": 1,
      "image_url": "http://media/restaurants/image1.jpg",
      "alt_text": "Restaurant exterior",
      "is_primary": true,
      "order": 0
    }
  ],
  "active_deals_count": 3,
  "is_saved": false,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Save/Unsave Restaurant
```
POST /api/restaurants/restaurants/{id}/save/
DELETE /api/restaurants/restaurants/{id}/save/
```
Requires authentication.

**Response (POST):**
```json
{
  "id": 1,
  "restaurant": {...},
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Get Saved Restaurants
```
GET /api/restaurants/restaurants/saved/
```
Requires authentication. Returns list of user's saved restaurants.

### Get Nearby Restaurants
```
GET /api/restaurants/restaurants/nearby/?latitude=51.5074&longitude=-0.1278&radius=10
```
Returns restaurants within radius (in km) of the given coordinates.

---

## Deals

### List Deals
```
GET /api/restaurants/deals/
```

**Query Parameters:**
- `restaurant` - Filter by restaurant ID
- `restaurant_slug` - Filter by restaurant slug
- `city_slug` - Filter by city slug
- `country_code` - Filter by country code
- `deal_type` - Filter by deal type: two_for_one, percentage, fixed, other
- `is_featured` - Filter by featured status (true/false)
- `min_discount` - Minimum discount percentage
- `max_discount` - Maximum discount percentage
- `city` - Filter by city slug (alternate)
- `country` - Filter by country code (alternate)
- `search` - Search by title, description, restaurant name
- `ordering` - Order by: start_date, end_date, created_at, is_featured

**Response:**
```json
{
  "count": 50,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "2-for-1 Main Course",
      "description": "Buy one get one free on main courses",
      "deal_type": "two_for_one",
      "restaurant_name": "Pizza Palace",
      "restaurant_slug": "pizza-palace",
      "city_name": "London",
      "discount_percentage": null,
      "discount_amount": null,
      "minimum_spend": "20.00",
      "start_date": "2024-01-01T00:00:00Z",
      "end_date": "2024-12-31T23:59:59Z",
      "is_featured": true,
      "primary_image": "http://media/deals/image.jpg",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

### Get Deal Details
```
GET /api/restaurants/deals/{id}/
```

**Response:**
```json
{
  "id": 1,
  "restaurant": {
    "id": 1,
    "name": "Pizza Palace",
    "slug": "pizza-palace",
    "city_name": "London",
    "country_name": "United Kingdom",
    "latitude": "51.5074",
    "longitude": "-0.1278",
    "price_range": 2,
    "verified": true,
    "is_featured": true,
    "primary_image": "http://media/restaurants/image.jpg",
    "active_deals_count": 3
  },
  "title": "2-for-1 Main Course",
  "description": "Buy one get one free on main courses",
  "deal_type": "two_for_one",
  "discount_percentage": null,
  "discount_amount": null,
  "minimum_spend": "20.00",
  "terms_and_conditions": "Valid Monday-Friday, excludes holidays",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-12-31T23:59:59Z",
  "max_uses": 1000,
  "used_count": 45,
  "max_per_user": 1,
  "is_featured": true,
  "images": [
    {
      "id": 1,
      "image_url": "http://media/deals/image1.jpg",
      "alt_text": "Deal image",
      "is_primary": true,
      "order": 0
    }
  ],
  "is_active": true,
  "can_use": true,
  "is_saved": false,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Save/Unsave Deal
```
POST /api/restaurants/deals/{id}/save/
DELETE /api/restaurants/deals/{id}/save/
```
Requires authentication.

### Get Saved Deals
```
GET /api/restaurants/deals/saved/
```
Requires authentication. Returns list of user's saved deals.

### Get Active Deals
```
GET /api/restaurants/deals/active/
```
Returns all currently active deals (cached for 5 minutes).

### Use a Deal
```
POST /api/restaurants/deals/{id}/use/
```
Requires authentication. Marks a deal as used by the current user.

**Body:**
```json
{
  "notes": "Used for dinner on Friday"
}
```

**Response:**
```json
{
  "id": 1,
  "deal": {...},
  "used_at": "2024-01-15T19:30:00Z",
  "restaurant_confirmed": false,
  "notes": "Used for dinner on Friday",
  "created_at": "2024-01-15T19:30:00Z"
}
```

---

## Deal Uses

### List User's Deal Uses
```
GET /api/restaurants/deal-uses/
```
Requires authentication. Returns list of deals used by the current user.

**Query Parameters:**
- `deal` - Filter by deal ID
- `restaurant_confirmed` - Filter by confirmation status (true/false)
- `ordering` - Order by: used_at, created_at

**Response:**
```json
[
  {
    "id": 1,
    "deal": {
      "id": 1,
      "title": "2-for-1 Main Course",
      "restaurant_name": "Pizza Palace",
      ...
    },
    "used_at": "2024-01-15T19:30:00Z",
    "restaurant_confirmed": false,
    "notes": "Used for dinner",
    "created_at": "2024-01-15T19:30:00Z"
  }
]
```

---

## Merchant Endpoints

These endpoints require merchant authentication (IsMerchant permission).

### Merchant Restaurants

#### List Merchant's Restaurants
```
GET /api/restaurants/merchant/restaurants/
```

#### Create Restaurant
```
POST /api/restaurants/merchant/restaurants/
Body: {
  "name": "My Restaurant",
  "slug": "my-restaurant",
  "description": "...",
  "city": 1,
  "address": "123 Main St",
  "postcode": "SW1A 1AA",
  "latitude": "51.5074",
  "longitude": "-0.1278",
  "phone": "+44 20 1234 5678",
  "email": "info@myrestaurant.com",
  "website": "https://myrestaurant.com",
  "categories": [1, 2],
  "price_range": 2,
  "opening_hours": {"monday": "10:00-22:00"}
}
```

#### Update Restaurant
```
PUT/PATCH /api/restaurants/merchant/restaurants/{id}/
```

#### Delete Restaurant
```
DELETE /api/restaurants/merchant/restaurants/{id}/
```

### Merchant Deals

#### List Merchant's Deals
```
GET /api/restaurants/merchant/deals/
```

#### Create Deal
```
POST /api/restaurants/merchant/deals/
Body: {
  "restaurant": 1,
  "title": "2-for-1 Main Course",
  "description": "...",
  "deal_type": "two_for_one",
  "discount_percentage": 50,
  "minimum_spend": "20.00",
  "terms_and_conditions": "...",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-12-31T23:59:59Z",
  "max_uses": 1000,
  "max_per_user": 1,
  "is_featured": false
}
```

#### Update Deal
```
PUT/PATCH /api/restaurants/merchant/deals/{id}/
```

#### Delete Deal
```
DELETE /api/restaurants/merchant/deals/{id}/
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "Error message",
  "field_name": ["Field error message"]
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

---

## Pagination

All list endpoints are paginated with 20 items per page by default.

**Response Format:**
```json
{
  "count": 100,
  "next": "http://api/endpoint/?page=2",
  "previous": null,
  "results": [...]
}
```

---

## Filtering

Most list endpoints support Django Filter Backend with various filters. Use query parameters to filter results.

Example:
```
GET /api/restaurants/restaurants/?city=1&verified=true&is_featured=true&ordering=-created_at
```

---

## Search

Many endpoints support search using the `search` query parameter.

Example:
```
GET /api/restaurants/restaurants/?search=pizza
```

