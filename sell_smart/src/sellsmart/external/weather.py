"""
sell_smart.external.weather
Open-Meteo Historical Weather API Client (PRD Section 4.1 & Section 4.6).

Rules (PRD Section 4.6):
  - Fetches observed historical weather at mandi coordinates up to date t only.
  - Never uses forecasted weather.
  - Placed behind the `features.use_weather` flag; disabled by default.
  - If the API is unreachable or fails, weather features remain disabled (NaN).
  - Rule R3 / Section 4.6: "Do not synthesise weather."
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional
import urllib.request
import json
import pandas as pd
import numpy as np

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_mandi_weather(
    mandi_id: str,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    cache_dir: Optional[Path] = None,
    timeout_sec: int = 10,
) -> pd.DataFrame:
    """
    Fetch observed historical daily weather for a mandi from Open-Meteo Archive.

    Args:
        mandi_id: Unique mandi identifier.
        latitude: Mandi latitude.
        longitude: Mandi longitude.
        start_date: YYYY-MM-DD.
        end_date: YYYY-MM-DD.
        cache_dir: Optional directory to cache downloaded parquet files.
        timeout_sec: Network request timeout.

    Returns:
        DataFrame with [mandi_id, date, weather_temp_mean, weather_rain_7d] or empty on failure.
    """
    if cache_dir:
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cached_file = cache_dir / f"weather_{mandi_id}_{start_date}_{end_date}.parquet"
        if cached_file.exists():
            try:
                df_cached = pd.read_parquet(cached_file)
                logger.info(f"Loaded cached weather for {mandi_id} ({len(df_cached)} days).")
                return df_cached
            except Exception:
                pass

    url = (
        f"{OPEN_METEO_ARCHIVE_URL}?"
        f"latitude={latitude:.4f}&longitude={longitude:.4f}&"
        f"start_date={start_date}&end_date={end_date}&"
        f"daily=temperature_2m_mean,precipitation_sum&"
        f"timezone=Asia/Kolkata"
    )

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SellSmart-AgTech/1.0"})
        with urllib.request.urlopen(req, timeout=timeout_sec) as response:
            data = json.loads(response.read().decode("utf-8"))

        daily = data.get("daily", {})
        dates = daily.get("time", [])
        temps = daily.get("temperature_2m_mean", [])
        rains = daily.get("precipitation_sum", [])

        if not dates:
            logger.warning(f"Open-Meteo returned no daily data for {mandi_id}.")
            return pd.DataFrame()

        df = pd.DataFrame({
            "mandi_id": mandi_id,
            "date": pd.to_datetime(dates),
            "temp_mean": temps,
            "rain_daily": rains,
        })
        df = df.sort_values("date").reset_index(drop=True)

        # Feature engineering: trailing 7-day rolling rainfall sum and mean temp (strictly past-only)
        df["weather_temp_mean"] = df["temp_mean"].rolling(7, min_periods=1).mean()
        df["weather_rain_7d"] = df["rain_daily"].rolling(7, min_periods=1).sum()

        result = df[["mandi_id", "date", "weather_temp_mean", "weather_rain_7d"]].copy()

        if cache_dir and not result.empty:
            result.to_parquet(cached_file, index=False)
            logger.info(f"Cached Open-Meteo weather for {mandi_id} to {cached_file}")

        return result

    except Exception as e:
        logger.warning(
            f"Open-Meteo weather fetch failed for {mandi_id} ({latitude}, {longitude}): {e}. "
            "Disabling weather features per PRD Section 4.6 (Do not synthesise weather)."
        )
        return pd.DataFrame()


def build_weather_panel(
    mandis_list: list[dict],
    start_date: str,
    end_date: str,
    cache_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Fetch observed weather for all selected mandis over the historical period.
    """
    all_dfs = []
    for m in mandis_list:
        m_id = m.get("mandi_id")
        lat = m.get("lat")
        lon = m.get("lon")
        if not m_id or lat is None or lon is None or np.isnan(lat) or np.isnan(lon):
            continue
        df_m = fetch_mandi_weather(m_id, float(lat), float(lon), start_date, end_date, cache_dir=cache_dir)
        if not df_m.empty:
            all_dfs.append(df_m)
        time.sleep(0.1)  # Respect Open-Meteo public API etiquette

    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    return pd.DataFrame(columns=["mandi_id", "date", "weather_temp_mean", "weather_rain_7d"])
