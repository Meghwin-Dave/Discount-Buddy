#!/usr/bin/env python
"""
Test script to verify all APIs are working
Run: python test_all_apis.py
"""
import requests
import json
from datetime import datetime, timedelta

USER_BASE_URL = "http://127.0.0.1:8000/user/api"
MERCHANT_BASE_URL = "http://127.0.0.1:8000/merchant/api"
results = []

def test_api(name, method, url, headers=None, data=None, expected_status=200):
    """Test an API endpoint"""
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        
        status = "[OK]" if response.status_code == expected_status else "[FAIL]"
        results.append({
            "name": name,
            "status": status,
            "code": response.status_code,
            "expected": expected_status
        })
        print(f"{status} {name}: {response.status_code} (expected {expected_status})")
        
        if response.status_code != expected_status:
            print(f"   Response: {response.text[:200]}")
        
        return response
    except Exception as e:
        print(f"[ERROR] {name}: ERROR - {str(e)}")
        results.append({
            "name": name,
            "status": "[ERROR]",
            "code": "ERROR",
            "expected": expected_status,
            "error": str(e)
        })
        return None

print("=" * 60)
print("TESTING ALL APIs")
print("=" * 60)

# Test 1: User Registration
print("\n1. USER REGISTRATION")
user_data = {
    "email": f"testuser_{datetime.now().timestamp()}@test.com",
    "username": f"testuser_{int(datetime.now().timestamp())}",
    "password": "test123456",
    "role": "customer"
}
register_response = test_api(
    "Register User",
    "POST",
    f"{USER_BASE_URL}/users/register/",
    data=user_data,
    expected_status=201
)

if register_response and register_response.status_code == 201:
    user_id = register_response.json().get("id")
    user_email = user_data["email"]
    user_password = user_data["password"]
    
    # Test 2: User Login
    print("\n2. USER LOGIN")
    login_response = test_api(
        "Login User",
        "POST",
        f"{USER_BASE_URL}/users/token/",
        data={"email": user_email, "password": user_password},
        expected_status=200
    )
    
    if login_response and login_response.status_code == 200:
        token_data = login_response.json()
        access_token = token_data.get("access")
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Test 3: Get User Profile
        print("\n3. GET USER PROFILE")
        test_api("Get User Profile", "GET", f"{USER_BASE_URL}/users/me/", headers=headers)
        
        # Test 4: Home Screen
        print("\n4. HOME SCREEN API")
        test_api("Home Screen", "GET", f"{USER_BASE_URL}/restaurants/home/", headers=headers)
        
        # Test 5: List Restaurants
        print("\n5. LIST RESTAURANTS")
        restaurants_response = test_api(
            "List Restaurants",
            "GET",
            f"{USER_BASE_URL}/restaurants/restaurants/",
            headers=headers
        )
        
        restaurant_id = None
        restaurant_slug = None
        if restaurants_response and restaurants_response.status_code == 200:
            restaurants = restaurants_response.json().get("results", [])
            if restaurants:
                restaurant_id = restaurants[0].get("id")
                restaurant_slug = restaurants[0].get("slug")
        
        # Test 6: Restaurant Detail
        print("\n6. RESTAURANT DETAIL")
        if restaurant_slug:
            test_api(
                "Restaurant Detail",
                "GET",
                f"{USER_BASE_URL}/restaurants/restaurant-detail/{restaurant_slug}/",
                headers=headers
            )
        
        # Test 7: Add to Favourites
        print("\n7. ADD TO FAVOURITES")
        if restaurant_slug:
            test_api(
                "Add to Favourites",
                "POST",
                f"{USER_BASE_URL}/restaurants/restaurant-detail/{restaurant_slug}/favourite/",
                headers=headers,
                expected_status=201
            )
        
        # Test 8: List Deals
        print("\n8. LIST DEALS")
        deals_response = test_api(
            "List Deals",
            "GET",
            f"{USER_BASE_URL}/restaurants/deals/",
            headers=headers
        )
        
        deal_id = None
        if deals_response and deals_response.status_code == 200:
            deals = deals_response.json().get("results", [])
            if deals:
                deal_id = deals[0].get("id")
        
        # Test 9: Claim Deal
        print("\n9. CLAIM/REDEEM DEAL")
        if deal_id:
            test_api(
                "Claim Deal",
                "POST",
                f"{USER_BASE_URL}/restaurants/deals/{deal_id}/use/",
                headers=headers,
                data={"notes": "Test claim"},
                expected_status=201
            )
        
        # Test 10: View Claimed Deals
        print("\n10. VIEW CLAIMED DEALS")
        test_api(
            "View Claimed Deals",
            "GET",
            f"{USER_BASE_URL}/restaurants/deal-uses/",
            headers=headers
        )
        
        # Test 11: Create Booking
        print("\n11. CREATE BOOKING")
        if restaurant_id:
            booking_date = (datetime.now() + timedelta(days=7)).isoformat()
            booking_response = test_api(
                "Create Booking",
                "POST",
                f"{USER_BASE_URL}/restaurants/bookings/",
                headers=headers,
                data={
                    "restaurant": restaurant_id,
                    "booking_date": booking_date,
                    "number_of_guests": 2,
                    "contact_name": "Test User",
                    "contact_phone": "+44 7123456789"
                },
                expected_status=201
            )
            
            booking_id = None
            if booking_response and booking_response.status_code == 201:
                booking_id = booking_response.json().get("id")
        
        # Test 12: List Bookings
        print("\n12. LIST BOOKINGS")
        test_api(
            "List Bookings",
            "GET",
            f"{USER_BASE_URL}/restaurants/bookings/",
            headers=headers
        )
        
        # Test 13: Add Review
        print("\n13. ADD REVIEW")
        if restaurant_id:
            test_api(
                "Add Review",
                "POST",
                f"{USER_BASE_URL}/restaurants/reviews/",
                headers=headers,
                data={
                    "restaurant": restaurant_id,
                    "rating": 5,
                    "comment": "Great restaurant! Test review."
                },
                expected_status=201
            )
        
        # Test 14: Profile Stats
        print("\n14. PROFILE STATS")
        test_api(
            "Profile Stats",
            "GET",
            f"{USER_BASE_URL}/restaurants/profile/stats/",
            headers=headers
        )
        
        # Test 15: Public Endpoints (No Auth)
        print("\n15. PUBLIC ENDPOINTS (NO AUTH)")
        test_api("List Cities", "GET", f"{USER_BASE_URL}/restaurants/cities/")
        test_api("List Countries", "GET", f"{USER_BASE_URL}/restaurants/countries/")
        test_api("List Cuisines", "GET", f"{USER_BASE_URL}/restaurants/cuisines/")
        test_api("List Categories", "GET", f"{USER_BASE_URL}/restaurants/categories/")
        
        # Test 16: Restaurant Management (if merchant)
        print("\n16. RESTAURANT MANAGEMENT (Merchant)")
        # Register merchant
        merchant_data = {
            "email": f"merchant_{datetime.now().timestamp()}@test.com",
            "username": f"merchant_{int(datetime.now().timestamp())}",
            "password": "test123456",
            "role": "merchant"
        }
        merchant_register = test_api(
            "Register Merchant",
            "POST",
            f"{USER_BASE_URL}/users/register/",
            data=merchant_data,
            expected_status=201
        )
        
        if merchant_register and merchant_register.status_code == 201:
            merchant_login = test_api(
                "Merchant Login",
                "POST",
                f"{USER_BASE_URL}/users/token/",
                data={"email": merchant_data["email"], "password": merchant_data["password"]},
                expected_status=200
            )
            
            if merchant_login and merchant_login.status_code == 200:
                merchant_token = merchant_login.json().get("access")
                merchant_headers = {"Authorization": f"Bearer {merchant_token}"}
                
                test_api(
                    "List Owned Restaurants",
                    "GET",
                    f"{MERCHANT_BASE_URL}/restaurants/restaurant/manage/",
                    headers=merchant_headers
                )
                
                test_api(
                    "View Restaurant Reviews",
                    "GET",
                    f"{MERCHANT_BASE_URL}/restaurants/restaurant/reviews/",
                    headers=merchant_headers
                )
                
                test_api(
                    "View Restaurant Bookings",
                    "GET",
                    f"{MERCHANT_BASE_URL}/restaurants/restaurant/bookings/",
                    headers=merchant_headers
                )

# Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
passed = sum(1 for r in results if r["status"] == "[OK]")
failed = sum(1 for r in results if r["status"] != "[OK]")
total = len(results)

print(f"\nTotal Tests: {total}")
print(f"[OK] Passed: {passed}")
print(f"[FAIL] Failed: {failed}")

if failed > 0:
    print("\nFailed Tests:")
    for r in results:
        if r["status"] != "[OK]":
            print(f"  - {r['name']}: Got {r['code']}, expected {r['expected']}")

print("\n" + "=" * 60)
print("API Testing Complete!")
print("=" * 60)
