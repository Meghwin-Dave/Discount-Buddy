"""Optional Gemini helper for drafting admin promo title/body."""
import json
import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-3.6-flash"


class GeminiUnavailable(Exception):
    pass


def generate_promo_copy(prompt: str, restaurant_name: str | None = None) -> dict:
    api_key = getattr(settings, "GEMINI_API_KEY", "") or ""
    if not api_key:
        raise GeminiUnavailable("Gemini is not configured.")

    context = f" Restaurant: {restaurant_name}." if restaurant_name else ""
    instruction = (
        "Write a short promotional push notification for the Discount Buddy app "
        "(UK English). Return JSON only with keys title and body. "
        "title max 50 characters, body max 150 characters. No markdown."
        f"{context}\nAdmin brief: {prompt}"
    )
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={api_key}"
    )
    try:
        response = requests.post(
            url,
            json={"contents": [{"parts": [{"text": instruction}]}]},
            timeout=20,
        )
        if response.status_code >= 400:
            raise GeminiUnavailable(_gemini_error_message(response))
        data = response.json()
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
    except Exception as exc:
        logger.exception("Gemini generate failed")
        raise GeminiUnavailable(str(exc)) from exc

    parsed = _parse_json_object(text)
    title = str(parsed.get("title") or "").strip()[:50]
    body = str(parsed.get("body") or "").strip()[:150]
    if not title or not body:
        raise GeminiUnavailable("Gemini did not return title and body.")
    return {"title": title, "body": body}


def _gemini_error_message(response) -> str:
    try:
        payload = response.json()
        return (
            payload.get("error", {}).get("message")
            or payload.get("error", {}).get("status")
            or response.text[:300]
        )
    except Exception:
        return response.text[:300] or f"HTTP {response.status_code}"


def _parse_json_object(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
    return {}
