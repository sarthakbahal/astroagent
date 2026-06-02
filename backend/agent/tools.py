from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from backend.services.ephemeris import (
    compute_natal_chart,
    compute_transits_summary,
)
from backend.services.geocoding import geocode_place_name_async
from backend.services.knowledge import keyword_rag_lookup


@tool
async def geocode_place(place_name: str) -> Dict[str, Any]:
    """Resolve a human place name into latitude/longitude and timezone.

    Use this tool whenever the user gives a place of birth that is not yet
    normalized into coordinates.

    Args:
        place_name: A city/state/country string such as "Mumbai, India".

    Returns:
        A dict with keys: lat, lng, timezone, display_name.
        On failure returns: {"error": "Place not found"}.
    """

    place_name = (place_name or "").strip()
    if not place_name:
        return {"error": "Place not found"}

    result = await geocode_place_name_async(place_name)
    if "error" in result:
        return {"error": "Place not found"}
    return result


@tool
def compute_birth_chart(
    date_str: str,
    time_str: str,
    lat: float,
    lng: float,
    timezone: str,
) -> Dict[str, Any]:
    """Compute a real natal chart using flatlib.

    Always call `geocode_place` first to obtain coordinates.

    Args:
        date_str: Date in YYYY-MM-DD.
        time_str: Time in HH:MM (24h).
        lat: Latitude.
        lng: Longitude.
        timezone: IANA timezone name (e.g. "Asia/Kolkata") or an offset
            string like "+05:30".

    Returns:
        Dict with planets, houses, ascendant, midheaven.
        On bad input returns: {"error": "..."}.
    """

    try:
        chart = compute_natal_chart(
            date_str=date_str,
            time_str=time_str,
            lat=float(lat),
            lng=float(lng),
            timezone=timezone,
        )
        return chart
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Failed to compute chart: {exc}"}


@tool
def get_daily_transits(natal_chart: Dict[str, Any], target_date: Optional[str] = None) -> List[str] | Dict[str, str]:
    """Summarize today's transits against the natal chart.

    Use this tool when the user asks about "today", "this week", or current
    energies. It compares transit planets against natal planets using major
    aspects.

    Args:
        natal_chart: Output from `compute_birth_chart`.
        target_date: Date in YYYY-MM-DD. Defaults to today.

    Returns:
        A list of transit strings, or {"error": "..."} on failure.
    """

    try:
        if not target_date:
            target_date = dt.date.today().isoformat()
        return compute_transits_summary(natal_chart=natal_chart, target_date=target_date)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Failed to compute transits: {exc}"}


@tool
def knowledge_lookup(query: str) -> Dict[str, Any]:
    """Look up relevant astrology reference notes.

    Use this tool for general educational questions (e.g., "Moon in Pisces",
    "What does Saturn in the 10th mean?") when no chart computation is
    required.

    Args:
        query: User's question.

    Returns:
        {"matches": ["paragraph1", "paragraph2"], "query": "..."}
        or {"error": "..."}.
    """

    query = (query or "").strip()
    if not query:
        return {"error": "Empty query"}

    try:
        matches = keyword_rag_lookup(query=query, top_k=2)
        return {"query": query, "matches": matches}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Knowledge lookup failed: {exc}"}
