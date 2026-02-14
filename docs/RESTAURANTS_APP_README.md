# Restaurants App - NeoTaste Clone Backend

This is a complete backend implementation for a restaurant discount/deal discovery platform similar to NeoTaste.

## Features

### 1. Location Management
- **Countries**: Manage countries with codes and flag emojis
- **Cities**: Manage cities with location coordinates, linked to countries
- Support for multiple countries and cities (like NeoTaste's UK, Germany, Austria, Netherlands)

### 2. Restaurant Management
- **Restaurants**: Full restaurant profiles with:
  - Location (address, coordinates, city)
  - Contact information (phone, email, website)
  - Categories (Italian, Asian, Fast Food, etc.)
  - Price range (1-4 scale)
  - Opening hours (JSON field)
  - Multiple images with primary image support
  - Verification and featured status
  - Active deals count

### 3. Deal Management
- **Deals**: Multiple deal types:
  - 2-for-1 deals
  - Percentage discounts
  - Fixed amount discounts
  - Other custom deals
- Deal features:
  - Validity dates (start/end)
  - Usage limits (total and per-user)
  - Minimum spend requirements
  - Terms and conditions
  - Multiple images
  - Featured status

### 4. User Features
- **Save Restaurants**: Users can save favorite restaurants
- **Save Deals**: Users can save deals for later
- **Use Deals**: Track deal usage by users
- **Deal History**: View all deals used by a user

### 5. Merchant Features
- **Manage Restaurants**: Merchants can create/edit/delete their restaurants
- **Manage Deals**: Merchants can create/edit/delete deals for their restaurants
- Full CRUD operations for merchants

### 6. Search & Discovery
- Search restaurants by name, description, address
- Filter by city, country, category, price range
- Filter restaurants with active deals
- Nearby restaurants based on coordinates and radius
- Search deals by title, description, restaurant name
- Filter deals by type, city, country, discount range

### 7. API Features
- RESTful API design
- JWT authentication for protected endpoints
- Public endpoints for browsing (no auth required)
- Pagination (20 items per page)
- Filtering and search
- Image upload support
- Caching for active deals list

## Models

### Core Models
1. **Country**: Countries where the app operates
2. **City**: Cities within countries
3. **RestaurantCategory**: Categories (Italian, Asian, etc.)
4. **Restaurant**: Restaurant details and location
5. **Deal**: Restaurant deals/discounts
6. **RestaurantImage**: Images for restaurants
7. **DealImage**: Images for deals
8. **SavedRestaurant**: User's saved restaurants
9. **SavedDeal**: User's saved deals
10. **DealUse**: Track when users use deals

## API Endpoints

### Public Endpoints (No Auth Required)
- `GET /api/restaurants/countries/` - List countries
- `GET /api/restaurants/cities/` - List cities
- `GET /api/restaurants/categories/` - List restaurant categories
- `GET /api/restaurants/restaurants/` - List restaurants
- `GET /api/restaurants/restaurants/{id}/` - Restaurant details
- `GET /api/restaurants/restaurants/nearby/` - Nearby restaurants
- `GET /api/restaurants/deals/` - List deals
- `GET /api/restaurants/deals/{id}/` - Deal details
- `GET /api/restaurants/deals/active/` - Active deals (cached)

### Authenticated Endpoints (User)
- `POST/DELETE /api/restaurants/restaurants/{id}/save/` - Save/unsave restaurant
- `GET /api/restaurants/restaurants/saved/` - Get saved restaurants
- `POST/DELETE /api/restaurants/deals/{id}/save/` - Save/unsave deal
- `GET /api/restaurants/deals/saved/` - Get saved deals
- `POST /api/restaurants/deals/{id}/use/` - Use a deal
- `GET /api/restaurants/deal-uses/` - Get deal usage history

### Merchant Endpoints (Merchant Auth Required)
- `GET/POST /api/restaurants/merchant/restaurants/` - List/create restaurants
- `GET/PUT/PATCH/DELETE /api/restaurants/merchant/restaurants/{id}/` - Manage restaurant
- `GET/POST /api/restaurants/merchant/deals/` - List/create deals
- `GET/PUT/PATCH/DELETE /api/restaurants/merchant/deals/{id}/` - Manage deal

## Setup Instructions

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. **Create Superuser** (for admin access)
   ```bash
   python manage.py createsuperuser
   ```

4. **Run Server**
   ```bash
   python manage.py runserver
   ```

## Usage Examples

### 1. Get Restaurants in London
```
GET /api/restaurants/restaurants/?city_slug=london
```

### 2. Get Nearby Restaurants
```
GET /api/restaurants/restaurants/nearby/?latitude=51.5074&longitude=-0.1278&radius=10
```

### 3. Get Active Deals in UK
```
GET /api/restaurants/deals/?country_code=GB
```

### 4. Save a Restaurant (Requires Auth)
```
POST /api/restaurants/restaurants/1/save/
Header: Authorization: Bearer <token>
```

### 5. Use a Deal (Requires Auth)
```
POST /api/restaurants/deals/1/use/
Header: Authorization: Bearer <token>
Body: {"notes": "Used for dinner"}
```

### 6. Create Restaurant as Merchant (Requires Merchant Auth)
```
POST /api/restaurants/merchant/restaurants/
Header: Authorization: Bearer <token>
Body: {
  "name": "My Restaurant",
  "slug": "my-restaurant",
  "city": 1,
  "address": "123 Main St",
  "phone": "+44 20 1234 5678",
  "categories": [1, 2],
  "price_range": 2
}
```

## Admin Interface

All models are registered in Django Admin. Access at `/admin/` with superuser credentials.

## Database Schema

The app uses Django's ORM with:
- SQLite for development (default)
- PostgreSQL for production (configure via environment variables)

See `discount_buddy/settings.py` for database configuration.

## Image Handling

- Restaurant and deal images are stored in `media/restaurants/` and `media/deals/`
- Images are served via `MEDIA_URL` setting
- Primary images are marked with `is_primary=True`
- Images support ordering with `order` field

## Caching

- Active deals list is cached for 5 minutes
- Cache backend: Redis (configured in settings)
- Falls back to database if Redis unavailable

## Filtering & Search

All list endpoints support:
- **Filtering**: Using query parameters (city, verified, is_featured, etc.)
- **Search**: Using `search` parameter
- **Ordering**: Using `ordering` parameter
- **Pagination**: 20 items per page (configurable)

## Security

- JWT authentication for protected endpoints
- Merchant permissions for merchant-only endpoints
- User-specific data filtering (users only see their own saved items)
- Input validation on all endpoints
- CSRF protection enabled

## Testing

Run tests with:
```bash
python manage.py test restaurants
```

## API Documentation

See `API_DOCUMENTATION.md` for complete API reference.

## Next Steps

To use this backend with a mobile app:
1. Set up authentication flow (register/login)
2. Implement restaurant browsing with location services
3. Implement deal discovery and saving
4. Implement deal usage tracking
5. Set up image upload for restaurants/deals (if using merchant app)

## Similar to NeoTaste Features

✅ Multi-city support (UK, Germany, Austria, Netherlands)
✅ Restaurant discovery
✅ Deal types (2-for-1, discounts)
✅ Location-based search
✅ User saved restaurants/deals
✅ Merchant management
✅ Featured restaurants/deals
✅ Active deals filtering
✅ Restaurant categories
✅ Image support

