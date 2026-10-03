"""
sell_smart.external.geo
Geocoding and distance utilities.

Strategy (3-layer fallback per PRD 4.5):
1. Offline India Cities LatLng.csv lookup
2. Nominatim API (1 req/sec)
3. NaN with needs_review=True

Road distance: haversine x road_factor (config: geocoding.road_factor, default 1.35).
"""
from __future__ import annotations

import math
import unicodedata
from pathlib import Path
from typing import Optional

import pandas as pd

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)

# Path to offline geocode reference (relative to project root)
_CITIES_CSV = Path("ML/India Cities LatLng.csv")


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", str(s)).encode("ASCII", "ignore").decode("utf-8").lower().strip()


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in km."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def road_km(lat1: float, lon1: float, lat2: float, lon2: float, road_factor: float = 1.35) -> float:
    """Estimated road distance using haversine x road_factor."""
    return haversine_km(lat1, lon1, lat2, lon2) * road_factor


def _load_cities_df() -> Optional[pd.DataFrame]:
    """Load offline city geocode CSV. Returns None if unavailable."""
    csv = _CITIES_CSV
    if not csv.exists():
        # Also try relative to current working directory
        csv = Path.cwd() / _CITIES_CSV
    if not csv.exists():
        return None
    try:
        df = pd.read_csv(csv)
        df["city_norm"] = df["city"].apply(_norm)
        return df
    except Exception as e:
        logger.debug(f"Failed to load cities CSV: {e}")
        return None


_CITIES_DF: Optional[pd.DataFrame] = None


def _get_cities_df() -> Optional[pd.DataFrame]:
    global _CITIES_DF
    if _CITIES_DF is None:
        _CITIES_DF = _load_cities_df()
    return _CITIES_DF


def geocode_mandi(
    market: str,
    district: str,
    state: str = "",
    road_factor: float = 1.35,
) -> dict:
    """
    Geocode a mandi location to (lat, lon).

    Returns dict with:
        lat: float | nan
        lon: float | nan
        geocode_confidence: float [0, 1]
        geocode_source: str
        needs_review: bool
    """
    cities_df = _get_cities_df()

    # 1. Offline lookup
    if cities_df is not None:
        m_norm = _norm(market)
        d_norm = _norm(district)
        match = cities_df[cities_df["city_norm"] == m_norm]
        if len(match) == 0:
            match = cities_df[cities_df["city_norm"] == d_norm]
        if len(match) > 0:
            row = match.iloc[0]
            return {
                "lat": float(row["lat"]),
                "lon": float(row["lng"]),
                "geocode_confidence": 0.95,
                "geocode_source": "india_cities_latlng_csv",
                "needs_review": False,
            }

    # 2. Nominatim API
    try:
        import httpx
        import time

        query = f"{market}, {district}"
        if state:
            query += f", {state}"
        query += ", India"

        resp = httpx.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "SellSmartML/1.0 (hackathon research)"},
            timeout=10.0,
        )
        time.sleep(1.1)  # Nominatim rate limit: 1 req/sec

        results = resp.json()
        if results:
            r = results[0]
            importance = float(r.get("importance", 0.5))
            return {
                "lat": float(r["lat"]),
                "lon": float(r["lon"]),
                "geocode_confidence": importance,
                "geocode_source": "nominatim",
                "needs_review": importance < 0.7,
            }
    except Exception as e:
        logger.warning(f"Nominatim geocoding failed for '{market}/{district}': {e}")

    # 3. Fallback: unknown
    logger.warning(f"Geocoding failed for '{market}', '{district}'. Marking needs_review=True.")
    return {
        "lat": float("nan"),
        "lon": float("nan"),
        "geocode_confidence": 0.0,
        "geocode_source": "failed",
        "needs_review": True,
    }


def nearest_mandi(
    village_lat: float,
    village_lon: float,
    mandis: list[dict],
) -> dict:
    """
    Find the nearest mandi (by haversine distance) from a list of mandi dicts.
    Each mandi dict must have 'lat' and 'lon' keys (non-NaN).

    Returns the nearest mandi dict with an added 'distance_km' key.
    Returns None if no mandi has valid coordinates.
    """
    best = None
    best_dist = float("inf")

    for m in mandis:
        m_lat = m.get("lat")
        m_lon = m.get("lon")
        if m_lat is None or m_lon is None:
            continue
        try:
            m_lat, m_lon = float(m_lat), float(m_lon)
        except (TypeError, ValueError):
            continue
        if math.isnan(m_lat) or math.isnan(m_lon):
            continue

        dist = haversine_km(village_lat, village_lon, m_lat, m_lon)
        if dist < best_dist:
            best_dist = dist
            best = {**m, "distance_km": round(dist, 2)}

    return best
