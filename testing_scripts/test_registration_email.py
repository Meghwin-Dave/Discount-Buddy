#!/usr/bin/env python
"""
Test registration OTP email via the live server API.

POST http://16.171.196.144/user/api/users/register/init

Run:
  python testing_scripts/test_registration_email.py
  python testing_scripts/test_registration_email.py other@example.com
"""
import json
import sys

import requests

BASE_URL = "http://16.171.196.144/user/api"
TEST_EMAIL = "priyanshu@16arena.com"


def main() -> int:
    to_email = (sys.argv[1] if len(sys.argv) > 1 else TEST_EMAIL).strip()
    if not to_email or "@" not in to_email:
        print("Usage: python testing_scripts/test_registration_email.py <email>")
        return 1

    url = f"{BASE_URL}/users/register/init"
    payload = {"email": to_email, "role": "customer"}

    print("--- Live server registration email test ---")
    print(f"URL  : {url}")
    print(f"To   : {to_email}")
    print(f"Body : {json.dumps(payload)}")
    print()

    try:
        response = requests.post(url, json=payload, timeout=30)
    except requests.RequestException as exc:
        print(f"FAIL: request error: {exc}")
        return 1

    print(f"Status: {response.status_code}")
    try:
        body = response.json()
        print(f"Body  : {json.dumps(body, indent=2)}")
    except ValueError:
        print(f"Body  : {response.text}")
        body = None

    if response.status_code == 200:
        print()
        print("OK: Server accepted register/init.")
        print(f"Check inbox + spam for: {to_email}")
        print("Subject: Your Discount Buddy verification code")
        print()
        print(
            "Note: API can return 200 even if SMTP fails later "
            "(email is sent in a background thread that swallows errors)."
        )
        return 0

    print()
    print("FAIL: register/init did not succeed.")
    if isinstance(body, dict) and "email" in body:
        print("Hint: that email may already be registered on this server.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
