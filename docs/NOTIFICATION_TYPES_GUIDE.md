# Discount Buddy – Notification Types Guide

> A plain-language guide to every notification the app sends, who receives it, and when.

---

## 📱 Customer Notifications

These notifications are sent to **regular app users** (customers).

---

### 1. Booking Confirmed ✅
| | |
|---|---|
| **When** | A restaurant owner/merchant accepts a customer's booking request and changes the status to **Confirmed** |
| **Title** | `Booking Confirmed 🎉` |
| **Example message** | *"Your table at Pizza Palace has been confirmed for April 1, 2026 at 07:30 PM."* |
| **Deep link** | Opens the booking detail screen |
| **Payload** | `booking_id`, `restaurant_id`, `booking_date` |

---

### 2. New Deal at a Favourite Restaurant 🔥
| | |
|---|---|
| **When** | A restaurant that the customer has **favourited / saved** creates a new active deal |
| **Title** | `New Deal Available 🔥` |
| **Example message** | *"Pizza Palace has launched a new offer: 50% off all pizzas. Check it out!"* |
| **Deep link** | Opens the deal details or restaurant screen |
| **Payload** | `restaurant_id`, `deal_id` |

---

### 3. Deal Redeemed ✅
| | |
|---|---|
| **When** | The customer's QR code or 6-digit code is scanned/entered by the restaurant and the deal is **successfully confirmed** |
| **Title** | `Deal Redeemed Successfully ✅` |
| **Example message** | *"Enjoy your offer at Pizza Palace. Bon appétit!"* |
| **Deep link** | Opens deal history or restaurant screen |
| **Payload** | `deal_id`, `restaurant_id` |

---

### 4. System Announcement 📢
| | |
|---|---|
| **When** | Sent manually by the Discount Buddy admin team for platform announcements, promotions, or important updates |
| **Title** | Custom (set by admin) |
| **Example message** | *"We have exciting new features for you! Update the app to discover them."* |
| **Deep link** | Depends on the payload |
| **Payload** | Custom JSON |

---

## 🏪 Merchant Notifications

These notifications are sent to **restaurant owners and merchants** who manage a restaurant on the platform.

---

### 5. New Table Booking Request 📅
| | |
|---|---|
| **When** | A customer submits a **new booking request** for a table at the merchant's restaurant |
| **Title** | `New Table Booking Request 📅` |
| **Example message** | *"John Doe has requested a table for 2 guests at Pizza Palace on April 1, 2026 at 07:30 PM."* |
| **Action required** | Merchant should confirm or decline the booking from their dashboard |
| **Deep link** | Opens the bookings management screen |
| **Payload** | `booking_id`, `restaurant_id`, `customer_name`, `number_of_guests`, `booking_date` |

---

### 6. Deal Redeemed at Your Restaurant 🎉
| | |
|---|---|
| **When** | A customer successfully redeems a deal code (QR or 6-digit) at the merchant's restaurant |
| **Title** | `Deal Redeemed at Your Restaurant 🎉` |
| **Example message** | *"Jane Smith just redeemed "50% off all pizzas" at Pizza Palace."* |
| **Purpose** | Confirms the redemption and keeps the merchant informed about deal usage in real time |
| **Deep link** | Opens the deal redemptions history screen |
| **Payload** | `deal_use_id`, `deal_id`, `restaurant_id`, `customer_name`, `redemption_code` |

---

### 7. Earnings Milestone Reached 🏆
| | |
|---|---|
| **When** | The restaurant's **cumulative total bill value** (after discounts) through the Discount Buddy app crosses one of these thresholds: **£100, £500, £1,000, £5,000, £10,000, £50,000** |
| **Title** | `Milestone Reached – £100 Earned! 🏆` *(amount varies by milestone)* |
| **Example message** | *"Congratulations! Your restaurant Pizza Palace has crossed £100 in total customer earnings through Discount Buddy. Keep it up!"* |
| **Purpose** | Motivates merchants to keep running deals and rewards growth milestones |
| **Each milestone fires only once** per restaurant — once you've received the £100 notification, you won't get it again, but you will get the £500 one next |
| **Deep link** | Opens the merchant analytics / earnings screen |
| **Payload** | `restaurant_id`, `milestone_amount` |

---

### 8. New Customer Review Posted ✍️
| | |
|---|---|
| **When** | A customer writes a **new review** for the merchant's restaurant |
| **Title** | `New Customer Review Posted ✍️` |
| **Example message** | *"Alex Johnson left a 5-star review for Pizza Palace. ⭐⭐⭐⭐⭐  "Great pizza and excellent service!"* |
| **Purpose** | Keeps merchants informed about customer feedback so they can respond or improve |
| **Deep link** | Opens the reviews management screen for the restaurant |
| **Payload** | `review_id`, `restaurant_id`, `customer_name`, `rating` |

---

## 📊 Summary Table

| # | Notification | Recipient | Trigger |
|---|---|---|---|
| 1 | Booking Confirmed | 👤 Customer | Merchant confirms a booking |
| 2 | New Deal at Favourite | 👤 Customer | Restaurant creates a new deal |
| 3 | Deal Redeemed (customer) | 👤 Customer | Customer's deal code is scanned |
| 4 | System Announcement | 👤 Customer | Admin broadcasts a message |
| 5 | New Booking Request | 🏪 Merchant | Customer submits a booking |
| 6 | Deal Redeemed (merchant) | 🏪 Merchant | A deal is redeemed at their restaurant |
| 7 | Earnings Milestone | 🏪 Merchant | Cumulative earnings cross £100 / £500 / £1K… |
| 8 | New Customer Review | 🏪 Merchant | Customer posts a review |

---

## 🔔 How Are Notifications Delivered?

Discount Buddy delivers notifications through **two channels simultaneously**:

1. **Push Notification (Firebase Cloud Messaging)**  
   Appears on the device lock screen / notification tray even when the app is closed.
   Requires the user to have installed the app and granted notification permission.

2. **In-App Notification**  
   Stored in the database and accessible via the Notifications screen inside the app.  
   Works even without Firebase (useful for testing or web access).

---

## ⚙️ Managing Notifications (Mobile App)

| Action | How |
|---|---|
| View all notifications | Go to the **Notifications** tab |
| Mark one as read | Tap the notification |
| Mark all as read | Tap "Mark all as read" button |
| See unread badge count | Bell icon on Home / tab bar |
| Turn off push (logout) | Device token is deactivated automatically on logout |
