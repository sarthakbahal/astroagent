from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Tuple

from flatlib import const
from flatlib.chart import Chart
from flatlib.datetime import Datetime
from flatlib.geopos import GeoPos
import swisseph as swe


PLANETS: List[str] = [
    const.SUN,
    const.MOON,
    const.MERCURY,
    const.VENUS,
    const.MARS,
    const.JUPITER,
    const.SATURN,
    const.URANUS,
    const.NEPTUNE,
    const.PLUTO,
    const.NORTH_NODE,
]

PLANET_NAME_MAP: Dict[str, str] = {
    const.SUN:        "Sun",
    const.MOON:       "Moon",
    const.MERCURY:    "Mercury",
    const.VENUS:      "Venus",
    const.MARS:       "Mars",
    const.JUPITER:    "Jupiter",
    const.SATURN:     "Saturn",
    const.URANUS:     "Uranus",
    const.NEPTUNE:    "Neptune",
    const.PLUTO:      "Pluto",
    const.NORTH_NODE: "Rahu",
}

SIGN_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]


AspectType = Literal["conjunction", "trine", "square"]


def _norm_lon(lon: float) -> float:
    return float(lon) % 360.0


def _lon_to_sign(lon: float) -> Tuple[str, float]:
    """Convert 0-360 ecliptic longitude to (sign_name, degree_in_sign)."""
    idx = int((_norm_lon(lon)) / 30.0)
    deg = _norm_lon(lon) % 30.0
    return SIGN_NAMES[idx], round(deg, 2)


def _house_cusps(chart: Chart) -> List[Tuple[int, float]]:
    cusps: List[Tuple[int, float]] = []
    for i in range(1, 13):
        h = chart.getHouse(f"House{i}")
        cusps.append((i, _norm_lon(float(h.lon))))
    return cusps


def _house_for_lon(
    lon: float, cusps: List[Tuple[int, float]]
) -> int:
    """Return 1-12 house for a given ecliptic longitude."""
    p = _norm_lon(lon)
    for idx in range(12):
        house_num, start = cusps[idx]
        _, end = cusps[(idx + 1) % 12]
        if end <= start:
            end += 360.0
        p2 = p if p >= start else p + 360.0
        if start <= p2 < end:
            return int(house_num)
    return 12


def _utc_offset_for_datetime(timezone: str, local_dt: dt.datetime) -> str:
    """Return flatlib utc offset string like '+05:30'."""
    tz = (timezone or "").strip()
    if not tz or tz.upper() == "UTC":
        return "+00:00"

    # Already an offset string
    if (len(tz) in (6, 7)) and (tz[0] in ("+", "-")) and (":" in tz):
        return tz

    try:
        from zoneinfo import ZoneInfo
        zi = ZoneInfo(tz)
        aware = local_dt.replace(tzinfo=zi)
        offset = aware.utcoffset()
        if offset is None:
            return "+00:00"
        total_minutes = int(offset.total_seconds() // 60)
        sign = "+" if total_minutes >= 0 else "-"
        total_minutes = abs(total_minutes)
        return f"{sign}{total_minutes // 60:02d}:{total_minutes % 60:02d}"
    except Exception:
        return "+00:00"


def _get_ayanamsa(jd: float) -> float:
    """Get Lahiri ayanamsa for a Julian Day. Always returns a float."""
    # Set sidereal mode explicitly every time — defensive against
    # state leaking between calls in long-running processes.
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    try:
        return float(swe.get_ayanamsa_ut(jd))
    except Exception:
        try:
            return float(swe.get_ayanamsa(jd))
        except Exception:
            return 23.166  # hardcoded fallback: ~2025 Lahiri value


def compute_natal_chart(
    *,
    date_str: str,
    time_str: str,
    lat: float,
    lng: float,
    timezone: str,
) -> Dict[str, Any]:
    """
    Compute a Vedic sidereal natal chart using Lahiri ayanamsa.

    Strategy:
      1. Build a TROPICAL flatlib chart (do NOT set sidereal mode on
         flatlib — we handle the conversion manually so it happens
         exactly once and is auditable).
      2. Get the Lahiri ayanamsa from pyswisseph for the chart's JD.
      3. Subtract ayanamsa from every tropical longitude once.
      4. Derive signs, houses, Rahu/Ketu from the sidereal longitudes.
    """

    flat_date_str = date_str.replace("-", "/")

    try:
        local_dt = dt.datetime.fromisoformat(f"{date_str}T{time_str}:00")
    except ValueError as exc:
        raise ValueError(
            "Invalid date/time — expected YYYY-MM-DD and HH:MM"
        ) from exc

    if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
        raise ValueError("Invalid coordinates")

    utc_offset = _utc_offset_for_datetime(
        timezone=timezone, local_dt=local_dt
    )

    # ── Build TROPICAL chart (flatlib default) ──────────────────────
    # Do NOT call swe.set_sid_mode here — keep flatlib in tropical mode
    # so longitudes come out tropical. We convert manually below.
    date = Datetime(flat_date_str, time_str, utc_offset)
    pos  = GeoPos(lat, lng)
    chart = Chart(date, pos, IDs=PLANETS, hsys=const.HOUSES_PLACIDUS)

    # ── Get ayanamsa for this Julian Day ────────────────────────────
    ay = _get_ayanamsa(date.jd)

    def to_sidereal(tropical_lon: float) -> float:
        """Subtract ayanamsa once. Result is always 0-360."""
        return (float(tropical_lon) - ay) % 360.0

    # ── Sidereal house cusps ────────────────────────────────────────
    raw_cusps = _house_cusps(chart)                          # tropical
    sid_cusps = [(i, to_sidereal(lon)) for i, lon in raw_cusps]

    # ── Planets ─────────────────────────────────────────────────────
    planets: Dict[str, Dict[str, Any]] = {}

    for pid in PLANETS:
        obj = chart.getObject(pid)
        trop_lon = float(obj.lon)
        sid_lon  = to_sidereal(trop_lon)
        sign_name, deg_in_sign = _lon_to_sign(sid_lon)
        pname = PLANET_NAME_MAP.get(pid, str(pid))

        planets[pname] = {
            "sign":   sign_name,
            "degree": deg_in_sign,
            "house":  _house_for_lon(sid_lon, sid_cusps),
            "lon":    round(sid_lon, 6),
        }

    # ── Ketu = Rahu + 180° ──────────────────────────────────────────
    if "Rahu" in planets:
        rahu_lon = float(planets["Rahu"]["lon"])
        ketu_lon = (rahu_lon + 180.0) % 360.0
        k_sign, k_deg = _lon_to_sign(ketu_lon)
        planets["Ketu"] = {
            "sign":   k_sign,
            "degree": k_deg,
            "house":  _house_for_lon(ketu_lon, sid_cusps),
            "lon":    round(ketu_lon, 6),
        }

    # ── Houses ──────────────────────────────────────────────────────
    houses: Dict[str, str] = {}
    for i in range(1, 13):
        _, cusp_sid = sid_cusps[i - 1]
        houses[str(i)] = _lon_to_sign(cusp_sid)[0]

    # ── Angles ──────────────────────────────────────────────────────
    asc    = chart.getAngle(const.ASC)
    mc     = chart.getAngle(const.MC)
    asc_sid = to_sidereal(float(asc.lon))
    mc_sid  = to_sidereal(float(mc.lon))
    asc_sign, asc_deg = _lon_to_sign(asc_sid)
    mc_sign,  mc_deg  = _lon_to_sign(mc_sid)

    return {
        "planets": {
            k: {
                "sign":   v["sign"],
                "degree": round(float(v["degree"]), 2),
                "house":  v["house"],
                "lon":    round(float(v["lon"]), 6),
            }
            for k, v in planets.items()
        },
        "houses":    houses,
        "ascendant": {"sign": asc_sign, "degree": round(float(asc_deg), 2)},
        "midheaven": {"sign": mc_sign,  "degree": round(float(mc_deg), 2)},
        "system":    "sidereal_lahiri",
        "meta": {
            "date":       date_str,
            "time":       time_str,
            "utc_offset": utc_offset,
            "lat":        lat,
            "lng":        lng,
            "ayanamsa":   round(ay, 6),
        },
    }


# ── Transits ─────────────────────────────────────────────────────────────────

def _angular_distance(deg1: float, deg2: float) -> float:
    diff = abs((_norm_lon(deg1) - _norm_lon(deg2)) % 360.0)
    return min(diff, 360.0 - diff)


def _aspect_between(
    transit_lon: float, natal_lon: float
) -> Optional[Tuple[AspectType, float]]:
    delta = _angular_distance(transit_lon, natal_lon)
    if delta <= 8.0:
        return ("conjunction", delta)
    if abs(delta - 120.0) <= 6.0:
        return ("trine", abs(delta - 120.0))
    if abs(delta - 90.0) <= 6.0:
        return ("square", abs(delta - 90.0))
    return None


def _aspect_phrase(aspect: AspectType) -> str:
    return {"conjunction": "conjunct", "trine": "trines", "square": "squares"}[aspect]


def compute_transits_summary(
    *, natal_chart: Dict[str, Any], target_date: str
) -> List[str]:
    """Compute daily transit aspects against the natal chart."""

    if not natal_chart or "planets" not in natal_chart or "meta" not in natal_chart:
        raise ValueError("natal_chart is missing required fields")

    try:
        dt.date.fromisoformat(target_date)
    except ValueError as exc:
        raise ValueError("target_date must be YYYY-MM-DD") from exc

    meta       = natal_chart["meta"]
    lat        = float(meta["lat"])
    lng        = float(meta["lng"])
    utc_offset = str(meta.get("utc_offset") or "+00:00")

    flat_target = target_date.replace("-", "/")
    date  = Datetime(flat_target, "12:00", utc_offset)
    pos   = GeoPos(lat, lng)

    # Tropical chart for transits — same strategy as natal
    tchart = Chart(date, pos, IDs=PLANETS, hsys=const.HOUSES_PLACIDUS)
    ay     = _get_ayanamsa(date.jd)

    def to_sid(lon: float) -> float:
        return (float(lon) - ay) % 360.0

    t_cusps = [(i, to_sid(lon)) for i, lon in _house_cusps(tchart)]

    # ── FIX: always use 'lon' key (0-360), never fall back to 'degree' ──
    # 'degree' is degrees-within-sign (0-30) which is useless for aspects.
    natal_lons: Dict[str, float] = {}
    for pname, pdata in natal_chart["planets"].items():
        if not isinstance(pdata, dict):
            continue
        lon_val = pdata.get("lon")
        if lon_val is None:
            # lon missing — reconstruct from sign + degree
            sign    = pdata.get("sign", "Aries")
            deg     = float(pdata.get("degree", 0))
            sign_idx = SIGN_NAMES.index(sign) if sign in SIGN_NAMES else 0
            lon_val  = sign_idx * 30.0 + deg
        natal_lons[pname] = float(lon_val)

    id_by_name = {v: k for k, v in PLANET_NAME_MAP.items()}

    transit_order = [
        "Saturn", "Jupiter", "Mars", "Venus",
        "Mercury", "Sun", "Moon",
        "Uranus", "Neptune", "Pluto",
    ]

    transits: List[str] = []
    seen: set = set()

    for tname in transit_order:
        pid = id_by_name.get(tname)
        if not pid:
            continue
        tobj  = tchart.getObject(pid)
        t_lon = to_sid(float(tobj.lon))
        t_house = _house_for_lon(t_lon, t_cusps)

        for nname, n_lon in natal_lons.items():
            asp = _aspect_between(t_lon, n_lon)
            if not asp:
                continue
            aspect_type, orb = asp
            phrase = _aspect_phrase(aspect_type)
            line = (
                f"{tname} {phrase} your natal {nname} "
                f"(orb {orb:.1f}°)"
                + (f" — activating your {t_house}th house" if t_house else "")
            )
            if line not in seen:
                seen.add(line)
                transits.append(line)

    return transits[:6]