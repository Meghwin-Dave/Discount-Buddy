#!/usr/bin/env python
"""
Book a table at a restaurant for a user.

Run: python testing_scripts/book_restaurant.py
"""
import json
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

BASE_URL = "http://127.0.0.1:8000/user/api"

EMAIL = "user4@test.com"
PASSWORD = "test123"
RESTAURANT_ID = 8


def main():
    print("Logging in...")
    login_response = requests.post(
        f"{BASE_URL}/users/token",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=30,
    )
    if login_response.status_code != 200:
        print(f"Login failed ({login_response.status_code}): {login_response.text}")
        sys.exit(1)

    access_token = login_response.json()["access"]
    headers = {"Authorization": f"Bearer {access_token}"}
    print(f"Logged in as {EMAIL}")

    london = ZoneInfo("Europe/London")
    booking_local = (datetime.now(london) + timedelta(days=7)).replace(
        hour=17, minute=0, second=0, microsecond=0
    )
    booking_date = booking_local.astimezone(ZoneInfo("UTC")).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    print(f"Booking local (London): {booking_local.strftime('%Y-%m-%d %H:%M %Z')}")

    booking_payload = {
        "restaurant": RESTAURANT_ID,
        "booking_date": booking_date,
        "number_of_guests": 2,
        "contact_name": "User Four",
        "contact_phone": "+44 7123456789",
        "special_requests": "Window seat if available",
    }

    print(f"Creating booking at restaurant {RESTAURANT_ID} for {booking_date}...")
    booking_response = requests.post(
        f"{BASE_URL}/restaurants/bookings",
        headers=headers,
        json=booking_payload,
        timeout=30,
    )

    if booking_response.status_code != 201:
        print(f"Booking failed ({booking_response.status_code}): {booking_response.text}")
        sys.exit(1)

    booking = booking_response.json()
    print("Booking created successfully!")
    print(json.dumps(booking, indent=2))


if __name__ == "__main__":
    main()
