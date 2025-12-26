# Quick Start Guide - Discount Buddy Restaurant Backend

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

3. **Create a superuser (optional, for admin access):**
   ```bash
   python manage.py createsuperuser
   ```

4. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

5. **Access the API:**
   - API Base: `http://localhost:8000/api/restaurants/`
   - Admin Panel: `http://localhost:8000/admin/`
   - API Docs (Swagger): `http://localhost:8000/api/docs/swagger/`
   - API Docs (ReDoc): `http://localhost:8000/api/docs/redoc/`

## Quick Test

### 1. Get All Countries
```bash
curl http://localhost:8000/api/restaurants/countries/
```

### 2. Get All Cities
```bash
curl http://localhost:8000/api/restaurants/cities/
```

### 3. Get All Restaurants
```bash
curl http://localhost:8000/api/restaurants/restaurants/
```

### 4. Get All Deals
```bash
curl http://localhost:8000/api/restaurants/deals/
```

## Sample Data Setup (via Django Shell)

```python
python manage.py shell
```

```python
from restaurants.models import Country, City, RestaurantCategory, Restaurant, Deal
from vouchers.models import Merchant
from users.models import User

# Create a country
uk = Country.objects.create(name="United Kingdom", code="GB", flag_emoji="🇬🇧")

# Create a city
london = City.objects.create(name="London", slug="london", country=uk, is_active=True)

# Create a category
italian = RestaurantCategory.objects.create(name="Italian", slug="italian", icon="🍝")

# Create a user and merchant (if needed)
# user = User.objects.create_user(email="merchant@example.com", username="merchant", password="password")
# merchant = Merchant.objects.create(user=user, name="Test Merchant", verified=True)

# Create a restaurant
# restaurant = Restaurant.objects.create(
#     merchant=merchant,
#     name="Pizza Palace",
#     slug="pizza-palace",
#     description="Authentic Italian pizza",
#     city=london,
#     address="123 Main St",
#     postcode="SW1A 1AA",
#     latitude="51.5074",
#     longitude="-0.1278",
#     phone="+44 20 1234 5678",
#     price_range=2,
#     verified=True
# )
# restaurant.categories.add(italian)

# Create a deal
# deal = Deal.objects.create(
#     restaurant=restaurant,
#     title="2-for-1 Main Course",
#     description="Buy one get one free on main courses",
#     deal_type=Deal.DEAL_TYPE_TWO_FOR_ONE,
#     minimum_spend=20.00,
#     start_date="2024-01-01T00:00:00Z",
#     end_date="2024-12-31T23:59:59Z",
#     max_uses=1000,
#     max_per_user=1
# )
```

## Authentication

### Register a User
```bash
curl -X POST http://localhost:8000/api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "user",
    "password": "password123",
    "role": "customer"
  }'
```

### Login (Get Token)
```bash
curl -X POST http://localhost:8000/api/users/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

### Use Token
```bash
curl http://localhost:8000/api/restaurants/restaurants/saved/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## API Endpoints Summary

### Public Endpoints
- `GET /api/restaurants/countries/` - List countries
- `GET /api/restaurants/cities/` - List cities
- `GET /api/restaurants/categories/` - List categories
- `GET /api/restaurants/restaurants/` - List restaurants
- `GET /api/restaurants/restaurants/{id}/` - Restaurant details
- `GET /api/restaurants/restaurants/nearby/` - Nearby restaurants
- `GET /api/restaurants/deals/` - List deals
- `GET /api/restaurants/deals/{id}/` - Deal details
- `GET /api/restaurants/deals/active/` - Active deals

### User Endpoints (Requires Auth)
- `POST /api/restaurants/restaurants/{id}/save/` - Save restaurant
- `DELETE /api/restaurants/restaurants/{id}/save/` - Unsave restaurant
- `GET /api/restaurants/restaurants/saved/` - Get saved restaurants
- `POST /api/restaurants/deals/{id}/save/` - Save deal
- `DELETE /api/restaurants/deals/{id}/save/` - Unsave deal
- `GET /api/restaurants/deals/saved/` - Get saved deals
- `POST /api/restaurants/deals/{id}/use/` - Use a deal
- `GET /api/restaurants/deal-uses/` - Get deal usage history

### Merchant Endpoints (Requires Merchant Auth)
- `GET/POST /api/restaurants/merchant/restaurants/` - Manage restaurants
- `GET/PUT/PATCH/DELETE /api/restaurants/merchant/restaurants/{id}/` - Manage restaurant
- `GET/POST /api/restaurants/merchant/deals/` - Manage deals
- `GET/PUT/PATCH/DELETE /api/restaurants/merchant/deals/{id}/` - Manage deal

## Filtering Examples

### Get restaurants in London
```
GET /api/restaurants/restaurants/?city_slug=london
```

### Get restaurants with active deals
```
GET /api/restaurants/restaurants/?has_deals=true
```

### Get deals in UK
```
GET /api/restaurants/deals/?country_code=GB
```

### Search restaurants
```
GET /api/restaurants/restaurants/?search=pizza
```

### Get nearby restaurants (within 10km)
```
GET /api/restaurants/restaurants/nearby/?latitude=51.5074&longitude=-0.1278&radius=10
```

## Production Deployment

1. Set environment variables:
   - `DJANGO_SECRET_KEY`
   - `DJANGO_DEBUG=False`
   - `DJANGO_ALLOWED_HOSTS=yourdomain.com`
   - `DB_ENGINE=postgres`
   - `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`

2. Run migrations:
   ```bash
   python manage.py migrate
   ```

3. Collect static files:
   ```bash
   python manage.py collectstatic
   ```

4. Use gunicorn:
   ```bash
   gunicorn discount_buddy.wsgi:application
   ```

For detailed API documentation, see `API_DOCUMENTATION.md`.
For app details, see `RESTAURANTS_APP_README.md`.

