# Flutter App — Image API Migration Guide

This document describes the backend image changes and what to update in the Flutter (mobile) app.

## Summary

| Area | Action required |
|------|-----------------|
| Upload (POST/PATCH) | **No change** — still send `image` as multipart file |
| HEIC from iPhone | **No change** — server now accepts and converts HEIC |
| Display images | **Update recommended** — new nested `image` response shape |
| `primary_image` on lists | **No change** — still a single URL string |

---

## API endpoints reference

Base URL prefixes used in this project:

| App | Base prefix |
|-----|-------------|
| Customer (Flutter user app) | `{BASE_URL}/user/api/restaurants/` |
| Customer (alternate route) | `{BASE_URL}/api/restaurants/` |
| Merchant app | `{BASE_URL}/merchant/api/restaurants/` |
| Banners | `{BASE_URL}/user/api/core/` |
| User profile | `{BASE_URL}/user/api/users/` |

All paths below omit `{BASE_URL}`. Trailing slashes are **not** used in this API.

---

### Upload endpoints — request unchanged

These accept `multipart/form-data` with an `image` (or `profile_picture`) file. **No request body changes** — still send the same field names.

| Method | Endpoint | Auth | Upload field | Notes |
|--------|----------|------|--------------|-------|
| `POST` | `/merchant/api/restaurants/restaurant-images` | Merchant | `image` | Also send `restaurant`, `image_type`, `is_primary`, `order`, `alt_text` |
| `PATCH` | `/merchant/api/restaurants/restaurant-images/{id}` | Merchant | `image` | Replace photo on existing gallery/menu image |
| `POST` | `/merchant/api/restaurants/restaurant/menu-items` | Merchant | `image` | Optional; uses `MenuItemCreateSerializer` |
| `PATCH` | `/merchant/api/restaurants/restaurant/menu-items/{id}` | Merchant | `image` | Optional image replace |
| `PATCH` | `/user/api/users/me` | User | `profile_picture` | Via `UserUpdateSerializer`; response from `GET /me` uses nested shape |

**Restaurant image upload example (merchant):**

```
POST /merchant/api/restaurants/restaurant-images
Content-Type: multipart/form-data

restaurant: 12
image: <file>          # JPEG, PNG, WebP, or HEIC
image_type: gallery     # or "menu"
is_primary: true
order: 0
alt_text: Front view
```

**Profile picture upload example (user):**

```
PATCH /user/api/users/me
Content-Type: multipart/form-data

profile_picture: <file>
```

> **Deal images:** There is no dedicated merchant API to upload deal photos. Deal `images` appear in **read** responses only (managed via Django admin). No Flutter upload flow for deal images unless you add an endpoint later.

> **Banners:** `POST /user/api/core/banners` exists but is typically admin-managed, not merchant Flutter.

---

### Read endpoints — response changed (update parsing)

These return the new nested `image: { medium, large }` object. **Flutter must update JSON models** for these.

#### Restaurant gallery / menu images (`RestaurantImageSerializer`)

| Method | Endpoint | Auth | Changed field |
|--------|----------|------|---------------|
| `GET` | `/merchant/api/restaurants/restaurant-images` | Merchant | Each item: `image` → `{ medium, large }` |
| `GET` | `/merchant/api/restaurants/restaurant-images/{id}` | Merchant | `image` → `{ medium, large }` |
| `POST` | `/merchant/api/restaurants/restaurant-images` | Merchant | **Response** after upload: `image` → `{ medium, large }` |
| `PATCH` | `/merchant/api/restaurants/restaurant-images/{id}` | Merchant | **Response**: `image` → `{ medium, large }` |

Nested inside restaurant payloads (`images` array):

| Method | Endpoint | Auth | Changed field |
|--------|----------|------|---------------|
| `GET` | `/user/api/restaurants/restaurants/{slug_or_id}` | Public | `images[]` items |
| `GET` | `/api/restaurants/restaurants/{slug_or_id}` | Public | Same as above |
| `GET` | `/user/api/restaurants/restaurant-detail/{id}` | Public | `images[]` items |
| `GET` | `/merchant/api/restaurants/restaurants` | Merchant | `images[]` on each restaurant |
| `GET` | `/merchant/api/restaurants/restaurants/{id}` | Merchant | `images[]` |
| `GET` | `/merchant/api/restaurants/restaurant/manage` | Merchant | `images[]` |

#### Menu items (`MenuItemSerializer`)

| Method | Endpoint | Auth | Changed field |
|--------|----------|------|---------------|
| `GET` | `/merchant/api/restaurants/restaurant/menu-items` | Merchant | `image` → `{ medium, large }` |
| `GET` | `/merchant/api/restaurants/restaurant/menu-items/{id}` | Merchant | `image` → `{ medium, large }` |

Also nested under restaurant detail:

| Method | Endpoint | Auth | Changed field |
|--------|----------|------|---------------|
| `GET` | `/user/api/restaurants/restaurant-detail/{id}` | Public | `menu_categories[].items[].image` |

> **Note:** `POST`/`PATCH` menu-items use `MenuItemCreateSerializer`, which may return `image` differently on create. After save, re-fetch with `GET` or parse nested shape if the create response is updated.

#### Deal images (`DealImageSerializer`) — read only

| Method | Endpoint | Auth | Changed field |
|--------|----------|------|---------------|
| `GET` | `/user/api/restaurants/deals` | Public | `images[]` on each deal |
| `GET` | `/user/api/restaurants/deals/{id}` | Public | `images[]` |
| `GET` | `/merchant/api/restaurants/deals` | Merchant | `images[]` |
| `GET` | `/merchant/api/restaurants/deals/{id}` | Merchant | `images[]` |

Nested in restaurant detail:

| Method | Endpoint | Auth | Changed field |
|--------|----------|------|---------------|
| `GET` | `/user/api/restaurants/restaurant-detail/{id}` | Public | `active_deals[].images[]` |

#### Banners (`BannerSerializer`)

| Method | Endpoint | Auth | Changed field |
|--------|----------|------|---------------|
| `GET` | `/user/api/core/banners` | Public | `image` → `{ medium, large }` |
| `GET` | `/user/api/core/banners/{id}` | Public | `image` → `{ medium, large }` |

#### User profile picture (`UserProfileSerializer`)

| Method | Endpoint | Auth | Changed field |
|--------|----------|------|---------------|
| `GET` | `/user/api/users/me` | User | `profile.profile_picture` → `{ medium, large }` |
| `PATCH` | `/user/api/users/me` | User | **Response** `profile.profile_picture` → `{ medium, large }` |
| `GET` | `/merchant/api/users/me` | Merchant | Same nested `profile.profile_picture` |

---

### Read endpoints — no response change (single URL string)

These still return a **plain URL string**, not `{ medium, large }`. **No Flutter parsing change** for these fields.

| Method | Endpoint | Field | Type |
|--------|----------|-------|------|
| `GET` | `/user/api/restaurants/restaurants` | `primary_image` | `String?` URL (large preferred) |
| `GET` | `/user/api/restaurants/deals` | `primary_image` | `String?` URL |
| `GET` | `/user/api/restaurants/home` | `restaurants[].image` | `String?` URL per restaurant card |
| `GET` | `/user/api/restaurants/home` | (deal sections) | Deals on home do not include image objects in `HomeScreenDealSerializer` |

---

### Quick mapping: which Flutter screen uses which endpoint

| Flutter screen | Endpoint(s) | What to parse |
|----------------|-------------|---------------|
| Merchant — upload restaurant photo | `POST .../restaurant-images` | Response `image.medium` / `image.large` |
| Merchant — gallery list | `GET .../restaurant-images?restaurant={id}` | Each `image` object |
| Customer — restaurant detail gallery | `GET .../restaurant-detail/{id}` → `images` | `ImageVariants` per item |
| Customer — menu list | `GET .../restaurant-detail/{id}` → `menu_categories[].items` | `item.image` object |
| Customer — home restaurant cards | `GET .../home` | `restaurant.image` as **String** (unchanged) |
| Customer — restaurant search/list | `GET .../restaurants` | `primary_image` as **String** (unchanged) |
| Customer — deals list | `GET .../deals` | `primary_image` as **String**; optional `images[]` objects on detail |
| User — profile / avatar | `GET/PATCH .../users/me` | `profile.profile_picture` object |
| Home banners | `GET .../core/banners` | `image` object |

---

## What changed on the backend

### Before (old response)

```json
{
  "id": 1,
  "image": "/media/restaurants/2026/07/02/photo.jpg",
  "image_url": "...",
  "image_thumb_url": "...",
  "image_medium_url": "...",
  "image_large_url": "...",
  "image_processing_status": "completed"
}
```

### After (new response)

```json
{
  "id": 1,
  "image": {
    "medium": "https://api.example.com/media/restaurants/medium/2026/07/02/abc_medium.webp",
    "large": "https://api.example.com/media/restaurants/large/2026/07/02/abc_large.webp"
  },
  "alt_text": "",
  "image_type": "gallery",
  "is_primary": true,
  "order": 0
}
```

Key differences:

1. `image` on **GET** is now an **object**, not a file path string
2. Removed: `image_url`, `image_thumb_url`, `image_medium_url`, `image_large_url`, `image_processing_status`
3. Only **two** sizes: `medium` (800px) and `large` (1920px)
4. Processing is **synchronous** — URLs are ready immediately in the upload response
5. All stored images are **WebP**

---

## Upload — no changes needed

Keep using `multipart/form-data`:

```dart
final formData = FormData.fromMap({
  'restaurant': restaurantId,
  'image': await MultipartFile.fromFile(
    filePath,
    filename: 'photo.jpg', // .heic also works
  ),
  'image_type': 'gallery',
  'is_primary': true,
});
```

Supported upload formats: **JPEG, PNG, WebP, HEIC**.

You do **not** need to convert to WebP on the device.

---

## Required model updates

### Restaurant / deal / menu image model

**Before:**

```dart
class RestaurantImage {
  final int id;
  final String? imageUrl;
  final String? imageThumbUrl;
  final String? imageMediumUrl;
  final String? imageLargeUrl;
  final String? processingStatus;
}
```

**After:**

```dart
class ImageVariants {
  final String? medium;
  final String? large;

  const ImageVariants({this.medium, this.large});

  factory ImageVariants.fromJson(Map<String, dynamic>? json) {
    if (json == null) return const ImageVariants();
    return ImageVariants(
      medium: json['medium'] as String?,
      large: json['large'] as String?,
    );
  }

  /// Best URL for the requested display context.
  String? urlFor({required bool fullScreen}) =>
      fullScreen ? (large ?? medium) : (medium ?? large);
}

class RestaurantImage {
  final int id;
  final ImageVariants image;
  final String? altText;
  final String imageType;
  final bool isPrimary;
  final int order;

  factory RestaurantImage.fromJson(Map<String, dynamic> json) {
    return RestaurantImage(
      id: json['id'] as int,
      image: ImageVariants.fromJson(json['image'] as Map<String, dynamic>?),
      altText: json['alt_text'] as String?,
      imageType: json['image_type'] as String? ?? 'gallery',
      isPrimary: json['is_primary'] as bool? ?? false,
      order: json['order'] as int? ?? 0,
    );
  }
}
```

### User profile picture

Same nested shape on `profile_picture`:

```json
{
  "role": "customer",
  "profile_picture": {
    "medium": "...",
    "large": "..."
  }
}
```

```dart
class UserProfile {
  final ImageVariants profilePicture;
  // ...
  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      profilePicture: ImageVariants.fromJson(
        json['profile_picture'] as Map<String, dynamic>?,
      ),
      // ...
    );
  }
}
```

---

## Display guidelines

| UI context | Use |
|------------|-----|
| Restaurant list cards | `image.medium` |
| Deal list thumbnails | `image.medium` |
| Menu item rows | `image.medium` |
| Image gallery / hero / fullscreen | `image.large` |
| `primary_image` on restaurant/deal lists | Use as-is (single URL string) |

### Example with `CachedNetworkImage`

```dart
CachedNetworkImage(
  imageUrl: restaurantImage.image.urlFor(fullScreen: false) ?? '',
  fit: BoxFit.cover,
)
```

### Fullscreen viewer

```dart
CachedNetworkImage(
  imageUrl: restaurantImage.image.large ?? restaurantImage.image.medium ?? '',
  fit: BoxFit.contain,
)
```

---

## Remove old client logic

You can delete Flutter code that:

- Polled or waited for `image_processing_status`
- Used `image_thumb_url` (thumb variant removed)
- Parsed flat `image_url` / `image_medium_url` / `image_large_url` fields
- Converted images to WebP before upload

---

## Error handling

Handle `400` validation errors on upload:

| Code | User message |
|------|----------------|
| `file_too_large` | Image must be under 10 MB |
| `unsupported_format` | Use a photo (JPEG, PNG, HEIC) — not SVG |
| `animated_not_supported` | Animated images are not supported |
| `resolution_too_high` | Image resolution is too large |

---

## Backward compatibility during rollout

If some records were not reprocessed yet, `medium` or `large` may be `null`. Fallback order in the app:

```dart
String? bestUrl(ImageVariants v, {bool fullScreen = false}) {
  if (fullScreen) return v.large ?? v.medium;
  return v.medium ?? v.large;
}
```

For `primary_image` on list endpoints, the backend still returns a single URL — no change needed.

---

## Migration checklist

- [ ] Review **API endpoints reference** above — map each Flutter screen to its endpoint
- [ ] Update `RestaurantImage`, `DealImage`, `MenuItem` JSON parsing on **read** endpoints listed above
- [ ] Keep `primary_image` and home `image` as `String?` (no change)
- [ ] Update `UserProfile` / `profile_picture` parsing on `GET/PATCH /user/api/users/me`
- [ ] Replace `image_url` / `image_medium_url` usages with `image.medium` / `image.large`
- [ ] Remove `image_processing_status` polling logic
- [ ] Remove thumb URL references
- [ ] Use `medium` in lists, `large` in detail/fullscreen
- [ ] Test HEIC upload via `POST /merchant/api/restaurants/restaurant-images`
- [ ] Verify `CachedNetworkImage` loads `.webp` URLs (supported on modern Flutter)

---

## Optional: no app update scenario

If you ship the backend before updating the app:

- **Uploads** continue to work
- **List views** using `primary_image` continue to work
- **Detail views** parsing `image` as a `String` will **break** — plan a coordinated release or hotfix

Recommend updating the app in the same release as this backend deploy.
