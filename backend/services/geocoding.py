from __future__ import annotations

import re
import time
from typing import Any, Dict

from geopy.geocoders import Nominatim


_LAST_NOMINATIM_CALL = 0.0


def _clean_place(place: str) -> str:
    place = (place or "").strip()
    place = re.sub(r"\s+", " ", place)
    return place


def _guess_timezone_from_country(address: Dict[str, Any]) -> str:
    """Best-effort timezone inference.

    Nominatim does not reliably return timezone. For production accuracy,
    you'd typically use a dedicated timezone-by-coordinates dataset.

    Here we implement a conservative mapping for common cases and
    otherwise return "UTC".
    """

    country_code = (address.get("country_code") or "").lower()

    # Common, high-impact mappings
    if country_code == "in":
        return "Asia/Kolkata"
    if country_code == "us":
        # Without state-specific mapping, default to UTC.
        return "UTC"
    if country_code == "gb":
        return "Europe/London"
    if country_code == "au":
        return "Australia/Sydney"
    if country_code == "ca":
        return "UTC"

    return "UTC"


def geocode_place_name(place_name: str) -> Dict[str, Any]:
    """Geocode place using Nominatim.

    Returns dict with lat/lng/timezone/display_name, or {"error": ...}.
    """

    place = _clean_place(place_name)
    if not place:
        return {"error": "Place not found"}

    global _LAST_NOMINATIM_CALL
    now = time.monotonic()
    # Be polite to the free Nominatim service.
    if now - _LAST_NOMINATIM_CALL < 1.0:
        time.sleep(1.0 - (now - _LAST_NOMINATIM_CALL))
    _LAST_NOMINATIM_CALL = time.monotonic()

    geolocator = Nominatim(user_agent="astroagent")
    location = geolocator.geocode(place, addressdetails=True)
    if location is None:
        return {"error": "Place not found"}

    address = (location.raw or {}).get("address") or {}
    timezone = _guess_timezone_from_country(address)

    return {
        "lat": float(location.latitude),
        "lng": float(location.longitude),
        "timezone": timezone,
        "display_name": str(getattr(location, "address", "") or (location.raw or {}).get("display_name") or place),
    }
