# Mobile Implementation Guide: Restaurant Booking Button Enable/Disable

## Quick Reference

### User/Customer Side (Read-Only)
| Action | Endpoint | Method |
|--------|----------|--------|
| List restaurants | `GET /api/restaurant/user/restaurants/` | GET |
| Restaurant detail | `GET /api/restaurant/user/restaurant-detail/{slug}/` | GET |
| Create booking | `POST /api/restaurant/user/bookings/` | POST |
| Home screen | `GET /api/restaurant/user/home` | GET |

### Merchant Side (Read & Write)
| Action | Endpoint | Method |
|--------|----------|--------|
| List my restaurants | `GET /api/restaurant/merchant/restaurants/` | GET |
| Get restaurant details | `GET /api/restaurant/merchant/restaurant/manage/{id}/` | GET |
| **Toggle bookings** | `PATCH /api/restaurant/merchant/restaurant/manage/{id}/` | PATCH |
| View all bookings | `GET /api/restaurant/merchant/restaurant/bookings/` | GET |
| Confirm booking | `POST /api/restaurant/merchant/restaurant/bookings/{id}/confirm/` | POST |
| Mark arrived | `POST /api/restaurant/merchant/restaurant/bookings/{id}/arrive/` | POST |
| Mark no-show | `POST /api/restaurant/merchant/restaurant/bookings/{id}/no_show/` | POST |

### Key Response Field
All restaurant endpoints return:
```json
{
  "bookings_enabled": true  // or false
}
```

---

## Overview
The backend now supports enabling/disabling booking functionality per restaurant using the `bookings_enabled` boolean field. This guide covers how to implement this feature on the mobile side.

---

## 1. API Response Models/DTOs

### Flutter/Dart Example

```dart
class Restaurant {
  final int id;
  final String name;
  final String slug;
  final String description;
  final String location;
  final String priceRange;
  final int occupancy;
  final bool verified;
  final bool isFeatured;
  final double averageRating;
  final int reviewCount;
  final List<String> cuisines;
  final List<Deal> deals;
  final bool isFavourite;
  final bool loyaltyCardEnabled;
  final bool bookingsEnabled;  // NEW FIELD
  // ... other fields

  Restaurant({
    required this.id,
    required this.name,
    required this.slug,
    required this.description,
    required this.location,
    required this.priceRange,
    required this.occupancy,
    required this.verified,
    required this.isFeatured,
    required this.averageRating,
    required this.reviewCount,
    required this.cuisines,
    required this.deals,
    required this.isFavourite,
    required this.loyaltyCardEnabled,
    required this.bookingsEnabled,  // NEW FIELD
    // ... other fields
  });

  factory Restaurant.fromJson(Map<String, dynamic> json) {
    return Restaurant(
      id: json['id'],
      name: json['name'],
      slug: json['slug'],
      description: json['description'],
      location: json['location'],
      priceRange: json['price_range'],
      occupancy: json['occupancy'],
      verified: json['verified'],
      isFeatured: json['is_featured'],
      averageRating: (json['average_rating'] ?? 0).toDouble(),
      reviewCount: json['review_count'] ?? 0,
      cuisines: List<String>.from(json['cuisines'] ?? []),
      deals: (json['active_deals'] as List?)
          ?.map((d) => Deal.fromJson(d))
          .toList() ?? [],
      isFavourite: json['is_favourite'] ?? false,
      loyaltyCardEnabled: json['loyalty_card_enabled'] ?? false,
      bookingsEnabled: json['bookings_enabled'] ?? true,  // NEW FIELD - default to true
      // ... other fields
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'slug': slug,
      'description': description,
      'location': location,
      'price_range': priceRange,
      'occupancy': occupancy,
      'verified': verified,
      'is_featured': isFeatured,
      'average_rating': averageRating,
      'review_count': reviewCount,
      'cuisines': cuisines,
      'active_deals': deals,
      'is_favourite': isFavourite,
      'loyalty_card_enabled': loyaltyCardEnabled,
      'bookings_enabled': bookingsEnabled,  // NEW FIELD
      // ... other fields
    };
  }
}
```

### React Native/TypeScript Example

```typescript
interface Restaurant {
  id: number;
  name: string;
  slug: string;
  description: string;
  location: string;
  priceRange: string;
  occupancy: number;
  verified: boolean;
  isFeatured: boolean;
  averageRating: number;
  reviewCount: number;
  cuisines: string[];
  deals: Deal[];
  isFavourite: boolean;
  loyaltyCardEnabled: boolean;
  bookingsEnabled: boolean;  // NEW FIELD
  // ... other fields
}

export const restaurantFromJson = (json: any): Restaurant => {
  return {
    id: json.id,
    name: json.name,
    slug: json.slug,
    description: json.description,
    location: json.location,
    priceRange: json.price_range,
    occupancy: json.occupancy,
    verified: json.verified,
    isFeatured: json.is_featured,
    averageRating: json.average_rating || 0,
    reviewCount: json.review_count || 0,
    cuisines: json.cuisines || [],
    deals: json.active_deals?.map(dealFromJson) || [],
    isFavourite: json.is_favourite || false,
    loyaltyCardEnabled: json.loyalty_card_enabled || false,
    bookingsEnabled: json.bookings_enabled ?? true,  // NEW FIELD - default to true
    // ... other fields
  };
};
```

### Native iOS (Swift) Example

```swift
struct Restaurant: Codable {
    let id: Int
    let name: String
    let slug: String
    let description: String
    let location: String
    let priceRange: String
    let occupancy: Int
    let verified: Bool
    let isFeatured: Bool
    let averageRating: Double
    let reviewCount: Int
    let cuisines: [String]
    let deals: [Deal]
    let isFavourite: Bool
    let loyaltyCardEnabled: Bool
    let bookingsEnabled: Bool  // NEW FIELD

    enum CodingKeys: String, CodingKey {
        case id, name, slug, description, location
        case priceRange = "price_range"
        case occupancy, verified
        case isFeatured = "is_featured"
        case averageRating = "average_rating"
        case reviewCount = "review_count"
        case cuisines
        case deals = "active_deals"
        case isFavourite = "is_favourite"
        case loyaltyCardEnabled = "loyalty_card_enabled"
        case bookingsEnabled = "bookings_enabled"  // NEW FIELD
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(Int.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        slug = try container.decode(String.self, forKey: .slug)
        description = try container.decode(String.self, forKey: .description)
        location = try container.decode(String.self, forKey: .location)
        priceRange = try container.decode(String.self, forKey: .priceRange)
        occupancy = try container.decode(Int.self, forKey: .occupancy)
        verified = try container.decode(Bool.self, forKey: .verified)
        isFeatured = try container.decode(Bool.self, forKey: .isFeatured)
        averageRating = try container.decodeIfPresent(Double.self, forKey: .averageRating) ?? 0
        reviewCount = try container.decodeIfPresent(Int.self, forKey: .reviewCount) ?? 0
        cuisines = try container.decodeIfPresent([String].self, forKey: .cuisines) ?? []
        deals = try container.decodeIfPresent([Deal].self, forKey: .deals) ?? []
        isFavourite = try container.decodeIfPresent(Bool.self, forKey: .isFavourite) ?? false
        loyaltyCardEnabled = try container.decodeIfPresent(Bool.self, forKey: .loyaltyCardEnabled) ?? false
        bookingsEnabled = try container.decodeIfPresent(Bool.self, forKey: .bookingsEnabled) ?? true  // NEW FIELD
    }
}
```

### Native Android (Kotlin) Example

```kotlin
data class Restaurant(
    val id: Int,
    val name: String,
    val slug: String,
    val description: String,
    val location: String,
    @SerializedName("price_range")
    val priceRange: String,
    val occupancy: Int,
    val verified: Boolean,
    @SerializedName("is_featured")
    val isFeatured: Boolean,
    @SerializedName("average_rating")
    val averageRating: Double = 0.0,
    @SerializedName("review_count")
    val reviewCount: Int = 0,
    val cuisines: List<String> = emptyList(),
    @SerializedName("active_deals")
    val deals: List<Deal> = emptyList(),
    @SerializedName("is_favourite")
    val isFavourite: Boolean = false,
    @SerializedName("loyalty_card_enabled")
    val loyaltyCardEnabled: Boolean = false,
    @SerializedName("bookings_enabled")
    val bookingsEnabled: Boolean = true  // NEW FIELD - default to true
    // ... other fields
)
```

---

## 2. UI Components - Show/Hide Booking Button

### Flutter Widget Example

```dart
class RestaurantDetailScreen extends StatelessWidget {
  final Restaurant restaurant;

  const RestaurantDetailScreen({
    Key? key,
    required this.restaurant,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(restaurant.name),
      ),
      body: SingleChildScrollView(
        child: Column(
          children: [
            // Restaurant info
            RestaurantInfoWidget(restaurant: restaurant),
            
            // Booking button - CONDITIONAL RENDERING
            if (restaurant.bookingsEnabled)
              BookingButton(
                onPressed: () => _navigateToBooking(context),
                restaurant: restaurant,
              )
            else
              DisabledBookingNotice(),
            
            // Other content
            MenuSection(restaurant: restaurant),
            DealsSection(deals: restaurant.deals),
          ],
        ),
      ),
    );
  }

  void _navigateToBooking(BuildContext context) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => BookingScreen(restaurant: restaurant),
      ),
    );
  }
}

class BookingButton extends StatelessWidget {
  final VoidCallback onPressed;
  final Restaurant restaurant;

  const BookingButton({
    Key? key,
    required this.onPressed,
    required this.restaurant,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: SizedBox(
        width: double.infinity,
        child: ElevatedButton(
          onPressed: onPressed,
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.blue,
            padding: const EdgeInsets.symmetric(vertical: 16),
          ),
          child: const Text(
            'Book a Table',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
          ),
        ),
      ),
    );
  }
}

class DisabledBookingNotice extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.grey[200],
          borderRadius: BorderRadius.circular(8),
        ),
        child: const Row(
          children: [
            Icon(Icons.info_outline, color: Colors.grey),
            SizedBox(width: 12),
            Expanded(
              child: Text(
                'Bookings are currently unavailable for this restaurant',
                style: TextStyle(color: Colors.grey, fontSize: 14),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

### React Native Example

```tsx
import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';

interface RestaurantDetailScreenProps {
  restaurant: Restaurant;
  navigation: any;
}

export const RestaurantDetailScreen: React.FC<RestaurantDetailScreenProps> = ({
  restaurant,
  navigation,
}) => {
  const handleBooking = () => {
    navigation.navigate('Booking', { restaurantId: restaurant.id });
  };

  return (
    <View style={styles.container}>
      {/* Restaurant info */}
      <RestaurantInfo restaurant={restaurant} />

      {/* Booking button - CONDITIONAL RENDERING */}
      {restaurant.bookingsEnabled ? (
        <BookingButton onPress={handleBooking} />
      ) : (
        <DisabledBookingNotice />
      )}

      {/* Other content */}
      <MenuSection restaurant={restaurant} />
      <DealsSection deals={restaurant.deals} />
    </View>
  );
};

interface BookingButtonProps {
  onPress: () => void;
}

const BookingButton: React.FC<BookingButtonProps> = ({ onPress }) => {
  return (
    <TouchableOpacity 
      style={styles.bookingButton} 
      onPress={onPress}
      activeOpacity={0.7}
    >
      <Text style={styles.bookingButtonText}>Book a Table</Text>
    </TouchableOpacity>
  );
};

const DisabledBookingNotice: React.FC = () => {
  return (
    <View style={styles.disabledNotice}>
      <Text style={styles.disabledText}>
        ℹ️ Bookings are currently unavailable for this restaurant
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  bookingButton: {
    margin: 16,
    padding: 16,
    backgroundColor: '#007AFF',
    borderRadius: 8,
    alignItems: 'center',
  },
  bookingButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  disabledNotice: {
    margin: 16,
    padding: 12,
    backgroundColor: '#E8E8E8',
    borderRadius: 8,
  },
  disabledText: {
    color: '#666',
    fontSize: 14,
  },
});
```

### Swift/iOS Example

```swift
import UIKit

class RestaurantDetailViewController: UIViewController {
    let restaurant: Restaurant
    
    private let bookingButton = UIButton()
    private let disabledNoticeView = UIView()
    
    init(restaurant: Restaurant) {
        self.restaurant = restaurant
        super.init(nibName: nil, bundle: nil)
    }
    
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
    
    override func viewDidLoad() {
        super.viewDidLoad()
        
        title = restaurant.name
        view.backgroundColor = .systemBackground
        
        setupUI()
    }
    
    private func setupUI() {
        // Booking button section - CONDITIONAL RENDERING
        if restaurant.bookingsEnabled {
            setupBookingButton()
        } else {
            setupDisabledNotice()
        }
    }
    
    private func setupBookingButton() {
        bookingButton.setTitle("Book a Table", for: .normal)
        bookingButton.backgroundColor = .systemBlue
        bookingButton.setTitleColor(.white, for: .normal)
        bookingButton.layer.cornerRadius = 8
        bookingButton.addTarget(self, action: #selector(handleBooking), for: .touchUpInside)
        
        view.addSubview(bookingButton)
        bookingButton.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            bookingButton.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 16),
            bookingButton.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -16),
            bookingButton.heightAnchor.constraint(equalToConstant: 50),
        ])
    }
    
    private func setupDisabledNotice() {
        disabledNoticeView.backgroundColor = .systemGray6
        disabledNoticeView.layer.cornerRadius = 8
        
        let label = UILabel()
        label.text = "ℹ️ Bookings are currently unavailable for this restaurant"
        label.textColor = .systemGray
        label.font = .systemFont(ofSize: 14)
        label.numberOfLines = 0
        
        disabledNoticeView.addSubview(label)
        view.addSubview(disabledNoticeView)
        
        disabledNoticeView.translatesAutoresizingMaskIntoConstraints = false
        label.translatesAutoresizingMaskIntoConstraints = false
        
        NSLayoutConstraint.activate([
            disabledNoticeView.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 16),
            disabledNoticeView.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -16),
            disabledNoticeView.heightAnchor.constraint(greaterThanOrEqualToConstant: 50),
            
            label.leadingAnchor.constraint(equalTo: disabledNoticeView.leadingAnchor, constant: 12),
            label.trailingAnchor.constraint(equalTo: disabledNoticeView.trailingAnchor, constant: -12),
            label.topAnchor.constraint(equalTo: disabledNoticeView.topAnchor, constant: 12),
            label.bottomAnchor.constraint(equalTo: disabledNoticeView.bottomAnchor, constant: -12),
        ])
    }
    
    @objc private func handleBooking() {
        let bookingVC = BookingViewController(restaurant: restaurant)
        navigationController?.pushViewController(bookingVC, animated: true)
    }
}
```

---

## 3. List Views - Disable Booking in List Items

### Flutter - Restaurant List Example

```dart
class RestaurantListItem extends StatelessWidget {
  final Restaurant restaurant;
  final VoidCallback onTap;
  final VoidCallback? onQuickBook;

  const RestaurantListItem({
    Key? key,
    required this.restaurant,
    required this.onTap,
    this.onQuickBook,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Card(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Restaurant image with badge
            Stack(
              children: [
                RestaurantImage(imageUrl: restaurant.imageUrl),
                if (!restaurant.bookingsEnabled)
                  Positioned(
                    top: 8,
                    right: 8,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.red.withOpacity(0.8),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Text(
                        'Bookings Disabled',
                        style: TextStyle(color: Colors.white, fontSize: 12),
                      ),
                    ),
                  ),
              ],
            ),
            // Restaurant details
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    restaurant.name,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    restaurant.cuisines.join(', '),
                    style: const TextStyle(fontSize: 12, color: Colors.grey),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.star, size: 16, color: Colors.amber),
                          const SizedBox(width: 4),
                          Text(restaurant.averageRating.toString()),
                        ],
                      ),
                      // Quick book button - only show if bookings enabled
                      if (restaurant.bookingsEnabled)
                        SizedBox(
                          height: 32,
                          child: ElevatedButton.icon(
                            onPressed: onQuickBook,
                            icon: const Icon(Icons.calendar_today, size: 14),
                            label: const Text('Book'),
                            style: ElevatedButton.styleFrom(
                              padding: const EdgeInsets.symmetric(horizontal: 12),
                            ),
                          ),
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

---

## 4. API Service/Networking Layer Updates

### Flutter - API Service Example

```dart
class RestaurantService {
  final http.Client client;
  final String baseUrl;

  RestaurantService({
    required this.client,
    required this.baseUrl,
  });

  Future<Restaurant> getRestaurant(String slug) async {
    final response = await client.get(
      Uri.parse('$baseUrl/restaurants/$slug'),
    );

    if (response.statusCode == 200) {
      // Now includes bookings_enabled from API
      return Restaurant.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to load restaurant');
    }
  }

  Future<List<Restaurant>> getRestaurantList({
    int page = 1,
    int pageSize = 20,
  }) async {
    final response = await client.get(
      Uri.parse('$baseUrl/restaurants/?page=$page&page_size=$pageSize'),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      final restaurants = (data['results'] as List)
          .map((r) => Restaurant.fromJson(r))
          .toList();
      // Now includes bookings_enabled for each restaurant
      return restaurants;
    } else {
      throw Exception('Failed to load restaurants');
    }
  }
}
```

### React Native - API Service Example

```typescript
import axios, { AxiosInstance } from 'axios';

class RestaurantService {
  private client: AxiosInstance;

  constructor(baseURL: string) {
    this.client = axios.create({ baseURL });
  }

  async getRestaurant(slug: string): Promise<Restaurant> {
    const response = await this.client.get(`/restaurants/${slug}`);
    // Now includes bookings_enabled from API
    return restaurantFromJson(response.data);
  }

  async getRestaurantList(page: number = 1, pageSize: number = 20): Promise<Restaurant[]> {
    const response = await this.client.get('/restaurants/', {
      params: { page, page_size: pageSize },
    });
    // Now includes bookings_enabled for each restaurant
    return response.data.results.map(restaurantFromJson);
  }
}

export const restaurantService = new RestaurantService(
  process.env.REACT_APP_API_URL || 'http://localhost:8000/api'
);
```

---

## 5. Booking Flow - Check Before Allowing Booking

### Flutter - Booking Validation Example

```dart
class BookingService {
  Future<void> initiateBooking(Restaurant restaurant) async {
    // Check if bookings are enabled before allowing
    if (!restaurant.bookingsEnabled) {
      throw BookingDisabledException(
        'Bookings are not available for this restaurant'
      );
    }

    // Proceed with booking flow
    // ... rest of booking logic
  }
}

class BookingDisabledException implements Exception {
  final String message;
  
  BookingDisabledException(this.message);
  
  @override
  String toString() => 'BookingDisabledException: $message';
}

// Usage in UI:
void handleBooking() {
  bookingService.initiateBooking(restaurant).then((_) {
    // Show booking form
    showBookingForm();
  }).catchError((error) {
    if (error is BookingDisabledException) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.message)),
      );
    }
  });
}
```

---

## 6. Testing Checklist

- [ ] Verify `bookings_enabled` field is received in API responses
- [ ] Test restaurant detail screen with `bookings_enabled = true` (button visible)
- [ ] Test restaurant detail screen with `bookings_enabled = false` (notice visible)
- [ ] Test restaurant list with mixed `bookings_enabled` states
- [ ] Verify booking button is disabled in list when `bookings_enabled = false`
- [ ] Test quick-book functionality respects `bookings_enabled` flag
- [ ] Test that disabled restaurants still show all other information correctly
- [ ] Test error handling when trying to book disabled restaurant
- [ ] Verify UI is responsive and accessible

---

## 7. Backend API Endpoints

### USER SIDE (Customer) - Read-Only Endpoints

#### List Restaurants
```
GET /api/restaurant/user/restaurants/
```
**Response includes:**
- `bookings_enabled`: boolean
- All other restaurant fields

**Example Response:**
```json
{
  "count": 150,
  "results": [
    {
      "id": 1,
      "name": "The Italian Kitchen",
      "slug": "the-italian-kitchen",
      "bookings_enabled": true,
      "price_range": "$$",
      "average_rating": 4.5,
      "cuisines": ["Italian", "Mediterranean"],
      "is_favourite": false
    }
  ]
}
```

#### Get Restaurant Detail
```
GET /api/restaurant/user/restaurant-detail/{slug}/
```
**Response includes:**
- `bookings_enabled`: boolean
- Complete restaurant information including menu, reviews, opening slots

**Example Response:**
```json
{
  "id": 1,
  "name": "The Italian Kitchen",
  "slug": "the-italian-kitchen",
  "bookings_enabled": true,
  "description": "...",
  "opening_hours": [...],
  "menu_categories": [...],
  "reviews": [...],
  "average_rating": 4.5
}
```

#### Create Booking (User-side)
```
POST /api/restaurant/user/bookings/
```
**Request body:**
```json
{
  "restaurant": 1,
  "booking_date": "2026-08-15",
  "time_slot": "18:00",
  "party_size": 4,
  "special_requests": "Window seat preferred"
}
```
**Response:**
- Returns 201 Created if `bookings_enabled = true`
- Returns 400 Bad Request if `bookings_enabled = false` with message:
```json
{
  "detail": "Bookings are not available for this restaurant"
}
```

#### Home Screen (Featured Restaurants)
```
GET /api/restaurant/user/home
```
**Response includes:**
- Featured restaurants with `bookings_enabled` flag
- Active deals and cuisines

---

### MERCHANT SIDE - Read & Write Endpoints

#### Get Merchant's Restaurants
```
GET /api/restaurant/merchant/restaurants/
```
**Response includes:**
- All merchant's restaurants
- `bookings_enabled` status for each

**Example Response:**
```json
{
  "count": 5,
  "results": [
    {
      "id": 1,
      "name": "The Italian Kitchen",
      "slug": "the-italian-kitchen",
      "bookings_enabled": true
    }
  ]
}
```

#### Get Restaurant Details (Merchant View)
```
GET /api/restaurant/merchant/restaurant/manage/{id}/
```
**Response includes:**
- Full restaurant details
- `bookings_enabled` status
- All configuration options

**Example Response:**
```json
{
  "id": 1,
  "name": "The Italian Kitchen",
  "slug": "the-italian-kitchen",
  "bookings_enabled": true,
  "loyalty_card_enabled": true,
  "occupancy": "available",
  "verified": true,
  "is_featured": false
}
```

#### Update Restaurant Settings (Merchant) - TOGGLE BOOKINGS
```
PATCH /api/restaurant/merchant/restaurant/manage/{id}/
```
**Request body to disable bookings:**
```json
{
  "bookings_enabled": false
}
```

**Request body to enable bookings:**
```json
{
  "bookings_enabled": true
}
```

**Response:**
```json
{
  "id": 1,
  "name": "The Italian Kitchen",
  "bookings_enabled": false,
  "message": "Booking status updated successfully"
}
```

#### Manage Restaurant Bookings (Merchant View)
```
GET /api/restaurant/merchant/restaurant/bookings/
```
**Query parameters:**
- `status`: pending, confirmed, arrived, no_show
- `date`: YYYY-MM-DD filter

**Response includes:**
- List of bookings
- Only available if `bookings_enabled = true`

**Example Response:**
```json
{
  "count": 25,
  "results": [
    {
      "id": 1,
      "customer_name": "John Doe",
      "party_size": 4,
      "booking_date": "2026-08-15",
      "time_slot": "18:00",
      "status": "confirmed"
    }
  ]
}
```

#### View Booking Details
```
GET /api/restaurant/merchant/restaurant/bookings/{id}/
```
**Response:**
```json
{
  "id": 1,
  "customer": {
    "id": 5,
    "name": "John Doe",
    "email": "john@example.com"
  },
  "party_size": 4,
  "booking_date": "2026-08-15",
  "time_slot": "18:00",
  "special_requests": "Window seat preferred",
  "status": "confirmed"
}
```

#### Confirm/Accept Booking
```
POST /api/restaurant/merchant/restaurant/bookings/{id}/confirm/
```
**Response:** 200 OK with updated booking

#### Mark Booking as No-Show
```
POST /api/restaurant/merchant/restaurant/bookings/{id}/no_show/
```
**Request body:**
```json
{
  "reason": "Customer did not arrive"
}
```
**Response:** 200 OK with updated booking

#### Mark Booking as Arrived
```
POST /api/restaurant/merchant/restaurant/bookings/{id}/arrive/
```
**Response:** 200 OK with updated booking

---

### ADMIN SIDE - Django Admin Panel

The `bookings_enabled` field is available in Django Admin:

```
Navigate to: /admin/restaurants/restaurant/
```

**Where to find it:**
- In list view: Shows `bookings_enabled` status for each restaurant
- In detail view: Under "Status" section alongside `verified`, `is_featured`, `is_active`

**To toggle:**
1. Click on restaurant
2. Scroll to "Status" section
3. Check/uncheck "Bookings Enabled"
4. Click Save

---

## 8. Error Handling & Edge Cases

### User-Side Error Handling

**When attempting to book a disabled restaurant:**

```python
# Flutter/Dart Example
try {
  final booking = await bookingService.createBooking(
    restaurantId: restaurant.id,
    date: selectedDate,
    timeSlot: selectedTime,
    partySize: guestCount,
  );
  // Success
  showSuccessDialog(context, 'Booking confirmed!');
} on BookingDisabledException catch (e) {
  showErrorDialog(context, 
    'Bookings Unavailable',
    'This restaurant is not accepting bookings at the moment. Please try again later.'
  );
} catch (e) {
  showErrorDialog(context, 'Error', 'Failed to create booking');
}
```

**Common Error Responses:**

| Status | Error | Cause |
|--------|-------|-------|
| 400 | "Bookings are not available for this restaurant" | `bookings_enabled = false` |
| 401 | "Authentication required" | User not logged in |
| 404 | "Restaurant not found" | Invalid restaurant ID |
| 422 | "Invalid booking date/time" | Slot not available |

### Merchant-Side Error Handling

**When updating booking status:**

```python
# Example error response
{
  "detail": "Cannot confirm booking - restaurant bookings are disabled",
  "code": "BOOKINGS_DISABLED"
}
```

**When disabling bookings with pending bookings:**

```python
# Before disabling, check pending bookings
GET /api/restaurant/merchant/restaurant/bookings/?status=confirmed&status=pending
```

Response shows how many bookings would be affected:
```json
{
  "message": "Warning: You have 3 pending bookings. Disabling bookings will not cancel existing bookings.",
  "pending_bookings_count": 3
}
```

---

## 9. Merchant Dashboard Implementation

### Dashboard UI Elements

**Swift/iOS Example - Settings Toggle:**

```swift
struct RestaurantSettingsView: View {
    @State var restaurant: Restaurant
    @State var isBookingsEnabled: Bool
    @State var isLoading = false
    @State var showAlert = false
    @State var alertMessage = ""
    
    var body: some View {
        VStack(spacing: 20) {
            Form {
                Section(header: Text("Booking Settings")) {
                    Toggle(isOn: $isBookingsEnabled) {
                        VStack(alignment: .leading) {
                            Text("Accept Bookings")
                                .font(.headline)
                            Text("Allow customers to book tables at your restaurant")
                                .font(.caption)
                                .foregroundColor(.gray)
                        }
                    }
                    .onChange(of: isBookingsEnabled) { newValue in
                        updateBookingStatus(newValue)
                    }
                }
                
                Section(header: Text("Impact")) {
                    HStack {
                        Image(systemName: "info.circle")
                            .foregroundColor(.blue)
                        VStack(alignment: .leading) {
                            Text(isBookingsEnabled ? "Booking button visible" : "Booking button hidden")
                                .font(.subheadline)
                            Text(isBookingsEnabled ? 
                                "Customers can book tables" : 
                                "New bookings cannot be made"
                            )
                            .font(.caption)
                            .foregroundColor(.gray)
                        }
                    }
                }
            }
        }
        .alert("Alert", isPresented: $showAlert) {
            Button("OK") { }
        } message: {
            Text(alertMessage)
        }
    }
    
    private func updateBookingStatus(_ enabled: Bool) {
        isLoading = true
        restaurantService.updateRestaurant(
            restaurantId: restaurant.id,
            bookingsEnabled: enabled
        ) { result in
            isLoading = false
            switch result {
            case .success:
                alertMessage = "Booking status updated successfully"
                showAlert = true
            case .failure(let error):
                alertMessage = "Failed to update: \(error.localizedDescription)"
                showAlert = true
                isBookingsEnabled = !enabled // Revert
            }
        }
    }
}
```

**React Native Example - Settings Screen:**

```tsx
export const RestaurantSettingsScreen = ({ restaurant }) => {
  const [isBookingsEnabled, setIsBookingsEnabled] = useState(
    restaurant.bookings_enabled
  );
  const [isLoading, setIsLoading] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');

  const handleToggle = async (value) => {
    setIsLoading(true);
    try {
      await restaurantService.updateRestaurant(restaurant.id, {
        bookings_enabled: value,
      });
      setIsBookingsEnabled(value);
      setAlertMessage('Booking status updated successfully');
      Alert.alert('Success', alertMessage);
    } catch (error) {
      setAlertMessage('Failed to update: ' + error.message);
      Alert.alert('Error', alertMessage);
      // Revert the toggle
      setIsBookingsEnabled(!value);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.section}>
        <Text style={styles.title}>Booking Settings</Text>
        
        <View style={styles.toggleContainer}>
          <View style={styles.toggleLabel}>
            <Text style={styles.toggleTitle}>Accept Bookings</Text>
            <Text style={styles.toggleSubtitle}>
              Allow customers to book tables at your restaurant
            </Text>
          </View>
          <Switch
            value={isBookingsEnabled}
            onValueChange={handleToggle}
            disabled={isLoading}
          />
        </View>

        <View style={styles.infoBox}>
          <Icon name="info-circle" size={20} color="#007AFF" />
          <View style={styles.infoText}>
            <Text style={styles.infoTitle}>
              {isBookingsEnabled ? 'Booking button visible' : 'Booking button hidden'}
            </Text>
            <Text style={styles.infoSubtitle}>
              {isBookingsEnabled
                ? 'Customers can book tables'
                : 'New bookings cannot be made'}
            </Text>
          </View>
        </View>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  section: { padding: 16 },
  title: { fontSize: 18, fontWeight: '600', marginBottom: 16 },
  toggleContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: 'white',
    padding: 16,
    borderRadius: 8,
    marginBottom: 16,
  },
  toggleLabel: { flex: 1 },
  toggleTitle: { fontSize: 16, fontWeight: '500', marginBottom: 4 },
  toggleSubtitle: { fontSize: 13, color: '#666' },
  infoBox: {
    flexDirection: 'row',
    backgroundColor: '#E3F2FD',
    padding: 12,
    borderRadius: 8,
  },
  infoText: { marginLeft: 12, flex: 1 },
  infoTitle: { fontSize: 14, fontWeight: '500', color: '#007AFF' },
  infoSubtitle: { fontSize: 13, color: '#666', marginTop: 4 },
});
```

---

## 10. Implementation Workflow

### For User/Customer Mobile App:

1. ✅ Update Restaurant DTO/Model to include `bookingsEnabled`
2. ✅ Parse `bookings_enabled` from API responses
3. ✅ Conditionally show/hide booking button in detail screen
4. ✅ Show disabled notice when bookings unavailable
5. ✅ Handle 400 error when attempting disabled booking
6. ✅ Update list view to show badges for disabled restaurants
7. ✅ Test with both enabled and disabled restaurants

### For Merchant Mobile App:

1. ✅ Add settings/configuration screen for restaurants
2. ✅ Show toggle for `bookings_enabled`
3. ✅ Implement PATCH endpoint to update setting
4. ✅ Show confirmation dialog before disabling
5. ✅ Display warning about pending bookings
6. ✅ Show success/error feedback
7. ✅ Refresh restaurant data after toggle

### Backend Checklist:

- ✅ Database migration applied
- ✅ Model field added with default=True
- ✅ Serializers updated for all endpoints
- ✅ Admin interface updated
- ✅ Bookings validation logic in place
- ✅ API responses include the field

