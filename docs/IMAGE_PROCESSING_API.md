# Image Processing API

Streamlined server-side image pipeline for restaurant gallery, deals, menu items, banners, and profile pictures.

## Design principles

- **No original storage** — uploads are converted synchronously; only WebP variants are kept
- **Two variants only** — `medium` (800px) and `large` (1920px)
- **HEIC supported** — iPhone photos are accepted and converted
- **Single service layer** — all logic in `core/services/image_service.py`

## Upload (unchanged for clients)

Send `multipart/form-data` with field name `image` (or `profile_picture` for profiles).

### Accepted formats

| Format | Handling |
|--------|----------|
| JPEG, PNG, WebP | Convert to WebP |
| HEIC / HEIF | Convert to WebP (via `pillow-heif`) |
| Static GIF | Convert to WebP |
| Animated GIF | Rejected |
| SVG | Rejected |

### Limits

- Max file size: **10 MB**
- Max resolution: **40 megapixels**

## Response format

On **read**, `image` is a nested object (not a file path):

```json
{
  "id": 1,
  "image": {
    "medium": "https://api.example.com/media/restaurants/medium/2026/07/02/abc_medium.webp",
    "large": "https://api.example.com/media/restaurants/large/2026/07/02/abc_large.webp"
  },
  "alt_text": "Front view",
  "image_type": "gallery",
  "is_primary": true,
  "order": 0
}
```

On **write** (POST/PATCH), send `image` as a file field. It is write-only and not returned as a path.

Profile pictures use the same shape on the `profile_picture` key in user profile responses.

## Endpoints

| Resource | Upload endpoint |
|----------|-----------------|
| Restaurant images | `POST /merchant/api/restaurants/restaurant-images` |
| Deal images | via merchant deal image endpoints |
| Menu items | via menu item management endpoints |
| Banners | admin / core API |
| Profile picture | user profile update |

## List views (`primary_image`)

Restaurant and deal list serializers still expose `primary_image` as a **single URL string** (the large variant, with fallback to medium or legacy image).

## Legacy images

Records uploaded before this pipeline may still have only the legacy `image` field. URLs fall back automatically:

1. `image_medium` / `image_large` (WebP)
2. Legacy `image` field

Reprocess legacy files:

```bash
python manage.py reprocess_images
python manage.py reprocess_images --model restaurants.restaurantimage --force
```

## Configuration

| Setting | Default |
|---------|---------|
| `IMAGE_MAX_SIZE_MB` | 10 |
| `IMAGE_MAX_PIXELS` | 40,000,000 |
| `IMAGE_SIZES.medium` | 800 |
| `IMAGE_SIZES.large` | 1920 |
| `WEBP_QUALITY.medium` | 82 |
| `WEBP_QUALITY.large` | 85 |

## Architecture

```
Upload (API / Admin)
       ↓
ProcessedImageBehaviorMixin.save()
       ↓
ImageProcessingService.validate_upload()
ImageProcessingService.handle_new_upload()  [sync]
       ↓
medium.webp + large.webp stored
original upload deleted
```

## Dependencies

```bash
pip install pillow-heif
```

Registered automatically in `core/apps.py` on startup.

## Not processed

- `DealUse.qr_code` and other system-generated images

# Production worker (required for async processing)
celery -A discount_buddy worker --loglevel=info

# Reprocess legacy images
python manage.py reprocess_images