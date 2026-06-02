from __future__ import annotations

import re
import time
import asyncio
from typing import Any, Dict

from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

_LAST_NOMINATIM_CALL = 0.0
_tf = TimezoneFinder()  # load once, reuse — it's slow to init


def _clean_place(place: str) -> str:
    place = (place or "").strip()
    place = re.sub(r"\s+", " ", place)
    return place


def geocode_place_name(place_name: str) -> Dict[str, Any]:
    """Geocode place using Nominatim + TimezoneFinder.

    Returns dict with lat/lng/timezone/display_name, or {"error": ...}.
    Timezone is derived from actual coordinates — never guessed from
    country code, never falls back to UTC for valid locations.
    """

    place = _clean_place(place_name)
    if not place:
        return {"error": "Place not found"}

    global _LAST_NOMINATIM_CALL
    now = time.monotonic()
    if now - _LAST_NOMINATIM_CALL < 1.0:
        time.sleep(1.0 - (now - _LAST_NOMINATIM_CALL))
    _LAST_NOMINATIM_CALL = time.monotonic()

    geolocator = Nominatim(user_agent="astroagent")
    location = geolocator.geocode(place, addressdetails=True)
    if location is None:
        return {"error": f"Place not found: {place_name}"}

    lat = float(location.latitude)
    lng = float(location.longitude)

    # Get exact IANA timezone from coordinates
    # This is accurate to the city/district level — no country guessing
    timezone = _tf.timezone_at(lat=lat, lng=lng)

    # timezone_at() returns None for locations in the ocean or
    # polar regions — extremely unlikely for birth places but handle it
    if timezone is None:
        timezone = _tf.closest_timezone_at(lat=lat, lng=lng)
    if timezone is None:
        timezone = "UTC"  # genuine last resort only

    display_name = str(
        getattr(location, "address", "")
        or (location.raw or {}).get("display_name")
        or place
    )

    return {
        "lat": lat,
        "lng": lng,
        "timezone": timezone,
        "display_name": display_name,
    }
    
async def geocode_place_name_async(place_name: str) -> Dict[str, Any]:
    """Async wrapper — runs geocode_place_name in a thread executor
    so the 1-second Nominatim rate-limit sleep doesn't block the
    FastAPI event loop.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, geocode_place_name, place_name)