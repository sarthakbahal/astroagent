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
    const.SUN: "Sun",
    const.MOON: "Moon",
    const.MERCURY: "Mercury",
    const.VENUS: "Venus",
    const.MARS: "Mars",
    const.JUPITER: "Jupiter",
    const.SATURN: "Saturn",
    const.URANUS: "Uranus",
    const.NEPTUNE: "Neptune",
    const.PLUTO: "Pluto",
    const.NORTH_NODE: "Rahu",
}


@dataclass(frozen=True)
class PlanetPosition:
    name: str
    sign: str
    degree: float
    house: int
    lon: float


AspectType = Literal["conjunction", "trine", "square"]


def _norm_lon(lon: float) -> float:
    return float(lon) % 360.0


def _house_cusps(chart: Chart) -> List[Tuple[int, float]]:
    cusps: List[Tuple[int, float]] = []
    for i in range(1, 13):
        h = chart.getHouse(f"House{i}")
        cusps.append((i, _norm_lon(float(h.lon))))
    return cusps


def _house_for_lon(lon: float, cusps: List[Tuple[int, float]]) -> int:
    """Return the 1-12 house that contains the given ecliptic longitude.

    flatlib 0.2.3 objects don't expose `.house` consistently, so we derive it
    from house cusp longitudes.
    """

    p = _norm_lon(lon)
    for idx in range(12):
        house_num, start = cusps[idx]
        _, end = cusps[(idx + 1) % 12]

        if end <= start:
            end += 360.0

        p2 = p
        if p2 < start:
            p2 += 360.0

        if start <= p2 < end:
            return int(house_num)

    return 12


def _utc_offset_for_datetime(timezone: str, local_dt: dt.datetime) -> str:
    """Return a flatlib utc offset string like "+05:30".

    Accepts either:
      - IANA timezone name ("Asia/Kolkata")
      - Already-an-offset string ("+05:30", "-04:00")
      - "UTC"

    If timezone cannot be interpreted, falls back to "+00:00".
    """

    tz = (timezone or "").strip()
    if not tz:
        return "+00:00"

    if tz.upper() == "UTC":
        return "+00:00"

    # If already looks like an offset, use it.
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
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{sign}{hours:02d}:{minutes:02d}"
    except Exception:  # noqa: BLE001
        return "+00:00"


def compute_natal_chart(
    *,
    date_str: str,
    time_str: str,
    lat: float,
    lng: float,
    timezone: str,
) -> Dict[str, Any]:
    """Compute natal chart positions using flatlib."""

    # flatlib expects dates in YYYY/MM/DD.
    flat_date_str = date_str.replace("-", "/")

    # Validate date/time formats early
    try:
        local_dt = dt.datetime.fromisoformat(f"{date_str}T{time_str}:00")
    except ValueError as exc:
        raise ValueError("Invalid date/time; expected YYYY-MM-DD and HH:MM") from exc

    if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
        raise ValueError("Invalid coordinates")

    utc_offset = _utc_offset_for_datetime(timezone=timezone, local_dt=local_dt)

    date = Datetime(flat_date_str, time_str, utc_offset)
    pos = GeoPos(lat, lng)

    # Sidereal mode (Lahiri ayanamsa) for Vedic/Jyotish.
    try:
        swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    except Exception:  # noqa: BLE001
        pass

    chart = Chart(date, pos, IDs=PLANETS, hsys=const.HOUSES_PLACIDUS)

    try:
        ay = float(swe.get_ayanamsa_ut(date.jd))
    except Exception:  # noqa: BLE001
        try:
            ay = float(swe.get_ayanamsa(date.jd))
        except Exception:  # noqa: BLE001
            ay = 0.0

    def to_sidereal(tropical_lon: float) -> float:
        return (float(tropical_lon) - ay) % 360.0

    def lon_to_sign(lon: float) -> Tuple[str, float]:
        names = [
            "Aries",
            "Taurus",
            "Gemini",
            "Cancer",
            "Leo",
            "Virgo",
            "Libra",
            "Scorpio",
            "Sagittarius",
            "Capricorn",
            "Aquarius",
            "Pisces",
        ]
        idx = int((lon % 360.0) / 30.0)
        deg = lon % 30.0
        return names[idx], round(deg, 2)

    # Build sidereal house cusps from tropical cusps.
    raw_cusps = _house_cusps(chart)
    cusps = [(i, to_sidereal(lon)) for i, lon in raw_cusps]

    planets: Dict[str, Dict[str, Any]] = {}
    for pid in PLANETS:
        obj = chart.getObject(pid)
        trop_lon = float(obj.lon)
        sid_lon = to_sidereal(trop_lon)
        sign_name, deg_in_sign = lon_to_sign(sid_lon)
        pname = PLANET_NAME_MAP.get(pid, str(pid))
        planets[pname] = {
            "sign": sign_name,
            "degree": deg_in_sign,
            "house": _house_for_lon(sid_lon, cusps),
            "lon": sid_lon,
        }

    # Ketu is always exactly opposite Rahu.
    if "Rahu" in planets:
        rahu_lon = float(planets["Rahu"]["lon"])
        ketu_lon = (rahu_lon + 180.0) % 360.0
        k_sign, k_deg = lon_to_sign(ketu_lon)
        planets["Ketu"] = {
            "sign": k_sign,
            "degree": k_deg,
            "house": _house_for_lon(ketu_lon, cusps),
            "lon": ketu_lon,
        }

    houses: Dict[str, str] = {}
    for i in range(1, 13):
        _, cusp_sid = cusps[i - 1]
        houses[str(i)] = lon_to_sign(cusp_sid)[0]

    asc = chart.getAngle(const.ASC)
    mc = chart.getAngle(const.MC)
    asc_sid = to_sidereal(float(asc.lon))
    mc_sid = to_sidereal(float(mc.lon))
    asc_sign, asc_deg = lon_to_sign(asc_sid)
    mc_sign, mc_deg = lon_to_sign(mc_sid)

    return {
        "planets": {
            k: {"sign": v["sign"], "degree": round(float(v["degree"]), 2), "house": v["house"], "lon": round(float(v["lon"]), 6)}
            for k, v in planets.items()
        },
        "houses": houses,
        "ascendant": {"sign": asc_sign, "degree": round(float(asc_deg), 2)},
        "midheaven": {"sign": mc_sign, "degree": round(float(mc_deg), 2)},
        "system": "sidereal_lahiri",
        "meta": {
            "date": date_str,
            "time": time_str,
            "utc_offset": utc_offset,
            "lat": lat,
            "lng": lng,
            "ayanamsa": round(ay, 6),
        },
    }


def _angular_distance(deg1: float, deg2: float) -> float:
    diff = abs((deg1 - deg2) % 360.0)
    return min(diff, 360.0 - diff)


def _aspect_between(transit_lon: float, natal_lon: float) -> Optional[Tuple[AspectType, float]]:
    """Return (aspect_type, orb) if within orb; else None."""

    delta = _angular_distance(transit_lon, natal_lon)

    # Conjunction: 0° within 8°
    if delta <= 8.0:
        return ("conjunction", delta)

    # Trine: 120° within 6°
    if abs(delta - 120.0) <= 6.0:
        return ("trine", abs(delta - 120.0))

    # Square: 90° within 6°
    if abs(delta - 90.0) <= 6.0:
        return ("square", abs(delta - 90.0))

    return None


def _aspect_phrase(aspect: AspectType) -> str:
    if aspect == "conjunction":
        return "conjunct"
    if aspect == "trine":
        return "trines"
    return "squares"


def compute_transits_summary(*, natal_chart: Dict[str, Any], target_date: str) -> List[str]:
    """Compute daily transits (simple aspect matching) using flatlib."""

    if not natal_chart or "planets" not in natal_chart or "meta" not in natal_chart:
        raise ValueError("natal_chart is missing required fields")

    try:
        _ = dt.date.fromisoformat(target_date)
    except ValueError as exc:
        raise ValueError("target_date must be YYYY-MM-DD") from exc

    meta = natal_chart.get("meta", {})
    lat = float(meta.get("lat"))
    lng = float(meta.get("lng"))
    utc_offset = str(meta.get("utc_offset") or "+00:00")

    # Compute a transit chart at 12:00 local time for stability.
    flat_target = target_date.replace("-", "/")
    date = Datetime(flat_target, "12:00", utc_offset)
    pos = GeoPos(lat, lng)

    try:
        swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    except Exception:  # noqa: BLE001
        pass

    tchart = Chart(date, pos, IDs=PLANETS, hsys=const.HOUSES_PLACIDUS)

    try:
        ay = float(swe.get_ayanamsa_ut(date.jd))
    except Exception:  # noqa: BLE001
        try:
            ay = float(swe.get_ayanamsa(date.jd))
        except Exception:  # noqa: BLE001
            ay = 0.0

    def to_sidereal(tropical_lon: float) -> float:
        return (float(tropical_lon) - ay) % 360.0

    t_cusps = [(i, to_sidereal(lon)) for i, lon in _house_cusps(tchart)]

    natal_planets = natal_chart["planets"]

    # Use only classical + outer planets as transits; include Sun/Moon too.
    transits: List[str] = []

    # Prefer tighter, meaningful matches: outer planets + Mars/Jupiter/Saturn
    transit_order = [
        "Saturn",
        "Jupiter",
        "Mars",
        "Venus",
        "Mercury",
        "Sun",
        "Moon",
        "Uranus",
        "Neptune",
        "Pluto",
    ]

    id_by_name = {v: k for k, v in PLANET_NAME_MAP.items()}

    # Build natal lon lookup
    natal_lon = {
        pname: float(pdata.get("lon") if pdata.get("lon") is not None else pdata.get("degree"))
        for pname, pdata in natal_planets.items()
        if isinstance(pdata, dict)
    }

    for tname in transit_order:
        pid = id_by_name.get(tname)
        if not pid:
            continue
        tobj = tchart.getObject(pid)
        t_lon = to_sidereal(float(tobj.lon))
        t_house = _house_for_lon(t_lon, t_cusps)

        for nname, ndeg in natal_lon.items():
            asp = _aspect_between(t_lon, ndeg)
            if not asp:
                continue
            aspect_type, orb = asp
            phrase = _aspect_phrase(aspect_type)

            # A gentle, interpretive but specific template.
            base = f"{tname} {phrase} your natal {nname} (orb {orb:.1f}°)"
            if t_house:
                base += f" — activating themes of your {t_house}th house"
            transits.append(base)

    # De-duplicate and cap to a practical set
    seen = set()
    unique: List[str] = []
    for t in transits:
        if t in seen:
            continue
        seen.add(t)
        unique.append(t)

    # Keep the top 6 to avoid noise
    return unique[:6]
