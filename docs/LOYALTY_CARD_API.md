# Loyalty Card API Documentation

API reference for the **Loyalty Card** feature. Share this document with frontend developers integrating customer and merchant apps.

**Base URLs**

| Audience | Base URL |
|----------|----------|
| Customer (User) | `/user/api/restaurants` |
| Merchant (Restaurant) | `/merchant/api/restaurants` |

**Authentication**

- Customer endpoints marked **Auth: Yes** require `Authorization: Bearer <access_token>`
- Merchant endpoints require a merchant/restaurant-owner JWT
- Public endpoints accept unauthenticated requests; loyalty progress is only included when the user is logged in

**Convention:** No trailing slashes on endpoints.

---

## Overview

Each restaurant can optionally run a loyalty card program:

1. **Merchant** enables loyalty on the restaurant and sets **required redemptions** + **reward description**
2. **Customer** redeems deals/coupons/QR codes at the restaurant
3. Each successful redemption increments the customer's progress for that restaurant
4. When progress reaches the required count, the customer becomes **reward eligible**
5. **Merchant** marks the reward as **claimed**, resetting the cycle (excess redemptions carry over)

---

## Data Models (API shapes)

### Loyalty program object

Returned on restaurant detail, loyalty card endpoints, and after deal redemption.

```json
{
  "loyalty_card_enabled": true,
  "required_redemptions": 10,
  "reward_description": "Free dessert on your next visit",
  "completed_redemptions": 3,
  "remaining_redemptions": 7,
  "progress_text": "3 of 10 redemptions completed",
  "progress_percentage": 30.0,
  "is_reward_eligible": false,
  "reward_eligible_at": null,
  "total_lifetime_redemptions": 23,
  "rewards_earned": 2,
  "last_reward_claimed_at": "2026-05-01T14:30:00+00:00"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `loyalty_card_enabled` | boolean | Whether this restaurant runs a loyalty program |
| `required_redemptions` | integer | Redemptions needed per reward cycle |
| `reward_description` | string | Reward details configured by the merchant |
| `completed_redemptions` | integer | Progress in the **current cycle** |
| `remaining_redemptions` | integer | Redemptions still needed for the next reward |
| `progress_text` | string | Human-readable progress, e.g. `"3 of 10 redemptions completed"` |
| `progress_percentage` | float | 0–100 progress toward next reward |
| `is_reward_eligible` | boolean | `true` when the customer can claim a reward |
| `reward_eligible_at` | ISO datetime \| null | When eligibility was reached |
| `total_lifetime_redemptions` | integer | All-time successful redemptions at this restaurant |
| `rewards_earned` | integer | Number of rewards claimed (completed cycles) |
| `last_reward_claimed_at` | ISO datetime \| null | When the last reward was claimed |

When loyalty is disabled:

```json
{ "loyalty_card_enabled": false }
```

---

## Merchant APIs — Restaurant Configuration

### Create / Update restaurant (enable loyalty)

Configure loyalty when creating or editing a restaurant on the **Add Restaurant** / **Manage Restaurant** screen.

| Method | Endpoint | Auth |
|--------|----------|------|
| `POST` | `/merchant/api/restaurants/restaurant/manage` | Yes |
| `PATCH` | `/merchant/api/restaurants/restaurant/manage/{id}` | Yes |
| `POST` | `/merchant/api/restaurants/restaurants` | Yes |
| `PATCH` | `/merchant/api/restaurants/restaurants/{id}` | Yes |

**New request fields**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `loyalty_card_enabled` | boolean | No | Default `false`. Check **Enable Loyalty Card** |
| `loyalty_required_redemptions` | integer | Yes if enabled | Minimum `1`. Number of redemptions to earn a reward |
| `loyalty_reward_description` | string | Yes if enabled | Reward details shown to customers |

**Example — enable loyalty**

```http
PATCH /merchant/api/restaurants/restaurant/manage/42
Authorization: Bearer <merchant_token>
Content-Type: application/json
```

```json
{
  "loyalty_card_enabled": true,
  "loyalty_required_redemptions": 10,
  "loyalty_reward_description": "Free main course on your next visit"
}
```

**Example — disable loyalty**

```json
{
  "loyalty_card_enabled": false
}
```

When disabled, `loyalty_required_redemptions` and `loyalty_reward_description` are cleared automatically.

**Validation errors (400)**

```json
{
  "loyalty_required_redemptions": ["Required when loyalty card is enabled (minimum 1)."]
}
```

```json
{
  "loyalty_reward_description": ["Required when loyalty card is enabled."]
}
```

**Response:** Standard `RestaurantSerializer` object including:

```json
{
  "id": 42,
  "name": "Pizza Palace",
  "loyalty_card_enabled": true,
  "loyalty_required_redemptions": 10,
  "loyalty_reward_description": "Free main course on your next visit",
  "...": "other restaurant fields"
}
```

---

## Customer APIs — Restaurant List

### List restaurants

| Method | Endpoint | Auth |
|--------|----------|------|
| `GET` | `/user/api/restaurants/restaurants` | No |

Each item in the list includes:

```json
{
  "id": 42,
  "name": "Pizza Palace",
  "loyalty_card_enabled": true,
  "...": "other list fields"
}
```

**UI guidance:** Show a badge/icon (e.g. "Loyalty Card") when `loyalty_card_enabled` is `true`.

Also available on:

- `GET /user/api/restaurants/home` — home screen sections include `loyalty_card_enabled` on each restaurant

---

## Customer APIs — Restaurant Details

### Restaurant detail (with loyalty progress)

| Method | Endpoint | Auth |
|--------|----------|------|
| `GET` | `/user/api/restaurants/restaurants/{slug_or_id}` | Optional |
| `GET` | `/user/api/restaurants/restaurant-detail/{slug_or_id}` | Optional |

**Query params (optional):** `latitude`, `longitude` for distance

**Response — loyalty section**

```json
{
  "id": 42,
  "name": "Pizza Palace",
  "loyalty_program": {
    "loyalty_card_enabled": true,
    "required_redemptions": 10,
    "reward_description": "Free main course on your next visit",
    "completed_redemptions": 3,
    "remaining_redemptions": 7,
    "progress_text": "3 of 10 redemptions completed",
    "progress_percentage": 30.0,
    "is_reward_eligible": false,
    "reward_eligible_at": null,
    "total_lifetime_redemptions": 3,
    "rewards_earned": 0,
    "last_reward_claimed_at": null
  },
  "...": "other detail fields"
}
```

- **Guest (not logged in):** `completed_redemptions` and related progress fields are `0`; program config is still visible
- **Logged-in user:** Shows their actual progress at this restaurant

**UI guidance:** Display `progress_text`, a progress bar using `progress_percentage`, and highlight when `is_reward_eligible` is `true`.

---

## Customer APIs — Loyalty Cards

### List all loyalty cards for the current user

| Method | Endpoint | Auth |
|--------|----------|------|
| `GET` | `/user/api/restaurants/loyalty-cards` | Yes |

Returns loyalty progress at every restaurant where the user has activity and loyalty is enabled.

**Response (200)**

```json
[
  {
    "id": 15,
    "restaurant_id": 42,
    "restaurant_name": "Pizza Palace",
    "restaurant_slug": "pizza-palace",
    "current_cycle_redemptions": 3,
    "total_lifetime_redemptions": 23,
    "rewards_earned": 2,
    "is_reward_eligible": false,
    "reward_eligible_at": null,
    "last_reward_claimed_at": "2026-05-01T14:30:00+00:00",
    "loyalty_program": { "...": "full loyalty program object" },
    "created_at": "2026-01-10T10:00:00+00:00",
    "updated_at": "2026-06-20T18:00:00+00:00"
  }
]
```

### Get loyalty card for one restaurant

| Method | Endpoint | Auth |
|--------|----------|------|
| `GET` | `/user/api/restaurants/loyalty-cards/{restaurant_id}` | Yes |

`{restaurant_id}` is the restaurant's numeric ID.

If the user has no record yet but the restaurant has loyalty enabled, an empty record is created and returned with zero progress.

**Errors**

| Status | Condition |
|--------|-----------|
| `404` | Restaurant not found or loyalty not enabled |

---

## Redemption Tracking (Automatic)

Loyalty progress updates **automatically** when a merchant successfully redeems a customer's deal.

### Merchant redeems deal (existing endpoint — now includes loyalty)

| Method | Endpoint | Auth |
|--------|----------|------|
| `POST` | `/merchant/api/restaurants/deals/redeem` | Yes |

**Request** (unchanged)

```json
{
  "qr_data": "DEALUSE:123:456789",
  "price": 45.00,
  "people_count": 2,
  "restaurant_id": 42
}
```

Or use `redemption_code` instead of `qr_data`.

**Response (200) — new loyalty fields**

```json
{
  "success": true,
  "reason": "Deal redeemed successfully.",
  "id": 123,
  "is_redeemed": true,
  "loyalty": {
    "loyalty_card_enabled": true,
    "required_redemptions": 10,
    "reward_description": "Free main course",
    "completed_redemptions": 10,
    "remaining_redemptions": 0,
    "progress_text": "10 of 10 redemptions completed",
    "progress_percentage": 100.0,
    "is_reward_eligible": true,
    "reward_eligible_at": "2026-06-22T18:00:00+00:00",
    "total_lifetime_redemptions": 30,
    "rewards_earned": 2,
    "last_reward_claimed_at": "2026-05-01T14:30:00+00:00"
  },
  "loyalty_reward_just_earned": true,
  "...": "other deal_use fields"
}
```

| New field | Description |
|-----------|-------------|
| `loyalty` | Customer's updated loyalty progress (only if restaurant has loyalty enabled) |
| `loyalty_reward_just_earned` | `true` when this redemption caused the customer to become reward eligible |

**Notes**

- Only **successful** redemptions count (when `is_redeemed` becomes `true`)
- Each `DealUse` is counted at most once (idempotent)
- If loyalty is disabled for the restaurant, `loyalty` is omitted

---

## Merchant APIs — Loyalty Management

### List customers with loyalty progress

| Method | Endpoint | Auth |
|--------|----------|------|
| `GET` | `/merchant/api/restaurants/loyalty/customers` | Yes |

**Query parameters**

| Param | Required | Description |
|-------|----------|-------------|
| `restaurant_id` | Yes | Restaurant to query |
| `eligible_only` | No | `true` to return only customers with `is_reward_eligible=true` |

**Response (200)**

```json
{
  "restaurant_id": 42,
  "restaurant_name": "Pizza Palace",
  "loyalty_card_enabled": true,
  "required_redemptions": 10,
  "reward_description": "Free main course on your next visit",
  "count": 2,
  "customers": [
    {
      "id": 15,
      "user_id": 7,
      "user_email": "customer@example.com",
      "user_name": "Jane Doe",
      "current_cycle_redemptions": 10,
      "total_lifetime_redemptions": 30,
      "rewards_earned": 2,
      "is_reward_eligible": true,
      "reward_eligible_at": "2026-06-22T18:00:00+00:00",
      "last_reward_claimed_at": "2026-05-01T14:30:00+00:00",
      "loyalty_program": { "...": "full loyalty program object" },
      "updated_at": "2026-06-22T18:00:00+00:00"
    }
  ]
}
```

### Claim / grant loyalty reward

Mark a customer's reward as claimed after they receive it in-store.

| Method | Endpoint | Auth |
|--------|----------|------|
| `POST` | `/merchant/api/restaurants/loyalty/claim-reward` | Yes |

**Request**

```json
{
  "restaurant_id": 42,
  "user_id": 7
}
```

**Response (200)**

```json
{
  "success": true,
  "reason": "Loyalty reward claimed successfully.",
  "loyalty": {
    "id": 15,
    "user_id": 7,
    "user_email": "customer@example.com",
    "user_name": "Jane Doe",
    "current_cycle_redemptions": 0,
    "is_reward_eligible": false,
    "rewards_earned": 3,
    "...": "other fields"
  }
}
```

**Errors (400)**

```json
{ "success": false, "reason": "This customer is not eligible for a loyalty reward." }
```

```json
{ "success": false, "reason": "No loyalty record found for this customer." }
```

**Cycle behavior:** After claim, `current_cycle_redemptions` resets (excess redemptions above the threshold carry into the new cycle). If the carried-over count already meets the threshold, `is_reward_eligible` becomes `true` again immediately.

### Loyalty redemption history (audit log)

| Method | Endpoint | Auth |
|--------|----------|------|
| `GET` | `/merchant/api/restaurants/loyalty/history` | Yes |

**Query parameters**

| Param | Required | Description |
|-------|----------|-------------|
| `restaurant_id` | Yes | Restaurant to query |
| `user_id` | No | Filter by customer |
| `status` | No | `counted`, `reward_earned`, or `reward_claimed` |

**Response (200)**

```json
{
  "restaurant_id": 42,
  "count": 3,
  "records": [
    {
      "id": 101,
      "user_email": "customer@example.com",
      "deal_use_id": 123,
      "deal_title": "20% Off Main Course",
      "status": "reward_earned",
      "cycle_redemption_number": 10,
      "total_lifetime_redemptions": 30,
      "notes": "",
      "created_at": "2026-06-22T18:00:00+00:00"
    },
    {
      "id": 100,
      "user_email": "customer@example.com",
      "deal_use_id": 122,
      "deal_title": "Free Appetizer",
      "status": "counted",
      "cycle_redemption_number": 9,
      "total_lifetime_redemptions": 29,
      "notes": "",
      "created_at": "2026-06-15T12:00:00+00:00"
    }
  ]
}
```

**Status values**

| Status | Meaning |
|--------|---------|
| `counted` | Redemption counted toward loyalty progress |
| `reward_earned` | This redemption reached the required threshold |
| `reward_claimed` | Merchant marked the reward as given to the customer |

---

## Frontend Integration Checklist

### Merchant app — Add Restaurant page

- [ ] Add checkbox: **Enable Loyalty Card** → `loyalty_card_enabled`
- [ ] When checked, show:
  - **Required Redemptions** → `loyalty_required_redemptions` (integer, min 1)
  - **Reward Description** → `loyalty_reward_description` (text)
- [ ] Send fields on `POST` / `PATCH` to `/merchant/api/restaurants/restaurant/manage`

### Customer app — Restaurant list

- [ ] Read `loyalty_card_enabled` from list/home responses
- [ ] Show a loyalty badge on qualifying restaurants

### Customer app — Restaurant detail

- [ ] Read `loyalty_program` from detail response
- [ ] Show required redemptions, reward description, and progress
- [ ] Display `progress_text` and progress bar from `progress_percentage`
- [ ] Highlight when `is_reward_eligible` is `true`

### Merchant app — Redemption flow

- [ ] After successful `POST /deals/redeem`, check `loyalty_reward_just_earned`
- [ ] Show alert when customer becomes eligible for a reward
- [ ] Use **Claim Reward** screen calling `POST /loyalty/claim-reward`

### Customer app — My Loyalty Cards (optional dedicated screen)

- [ ] `GET /loyalty-cards` for a list of all active loyalty cards
- [ ] `GET /loyalty-cards/{restaurant_id}` for a single restaurant

---

## Swagger / Live Docs

Interactive API docs are available at:

- User: `/user/api/docs/swagger/`
- Merchant: `/merchant/api/docs/swagger/`

---

## Database entities (reference)

| Model | Purpose |
|-------|---------|
| `Restaurant` | Stores `loyalty_card_enabled`, `loyalty_required_redemptions`, `loyalty_reward_description` |
| `UserRestaurantLoyalty` | One row per user–restaurant pair; tracks cycle progress and eligibility |
| `LoyaltyRedemptionRecord` | Audit log linking redemptions to loyalty events |

Migration: `restaurants/migrations/0015_loyalty_card.py`
