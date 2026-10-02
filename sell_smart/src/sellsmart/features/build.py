"""
sell_smart.features.build
Build model feature panel from gold daily data.

Feature groups:
- Lag features: modal_price at t-1, t-2, t-3, t-5, t-7, t-14
- Rolling statistics: 7d, 14d, 21d mean, std, min, max
- Spread features: (max - min) / modal
- Days since last observation
- Weekday / month (enabled if history >= calendar_min_years OR force_calendar_features=true)
- Activity proxies (no arrivals in dataset)
- Arrivals dormant path: column exists, is NaN unless data provided

All features are computed with strict past-only logic (R2).
Target: modal_price at t+h for each horizon in config.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from sellsmart.features.leakage_guard import assert_no_leakage
from sellsmart.common.logging import get_logger

logger = get_logger(__name__)

SYNTHETIC_COLS = [
    "farmer_id", "village_lat", "village_lon", "quantity_q",
    "vehicle_type", "cash_deadline_days", "storage_condition",
    "quality_factor", "trader_offer_proxy", "stress_shock_series",
    "demo_arrivals_index", "is_synthetic",
]


def _mandi_hash(mandi_id: str) -> int:
    """Deterministic integer encoding of mandi_id using MD5 (reproducible across processes).
    Replaces non-deterministic Python hash() -- fixes Issue 6 / R10 reproducibility.
    """
    return int(hashlib.md5(mandi_id.encode("utf-8")).hexdigest()[:8], 16) % 10000


def build_features(
    gold_df: pd.DataFrame,
    config: dict,
    use_calendar: bool | None = None,
    climate_summary: dict | None = None,
) -> pd.DataFrame:
    """
    Build model feature panel from gold daily panel.

    Args:
        gold_df: Gold panel with (mandi_id, crop, date, modal_price, ...).
        config: Full config dict.
        use_calendar: Override calendar feature flag; None = auto from config.
        climate_summary: Optional dict from compute_climate_summary().
                         When provided, activates weather and climate risk features.
                         Broadcast uniformly since climate dataset has no date/mandi key.

    Returns:
        DataFrame with features and targets.
    """
    feat_cfg = config.get("features", {})
    lags = feat_cfg.get("lags", [1, 2, 3, 5, 7, 14])
    windows = feat_cfg.get("rolling_windows", [7, 14, 21])
    horizons = feat_cfg.get("horizon_days", [1, 3, 5, 7, 14])
    cal_min_years = feat_cfg.get("calendar_min_years", 1.0)
    force_calendar = feat_cfg.get("force_calendar_features", False)
    use_weather = feat_cfg.get("use_weather", False)

    df = gold_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["mandi_id", "crop", "date"])

    # Determine history span
    date_span_days = (df["date"].max() - df["date"].min()).days
    history_years = date_span_days / 365.25

    if use_calendar is not None:
        enable_calendar = use_calendar
    elif force_calendar:
        enable_calendar = True
    else:
        enable_calendar = history_years >= cal_min_years

    if enable_calendar and history_years < 2.0:
        logger.warning(
            f"Calendar features ENABLED with only {history_years:.1f}y of history. "
            "Seasonal patterns are anecdotal (single observations per season). "
            "Report results accordingly per PRD Section 4.2.3."
        )
    elif not enable_calendar:
        logger.info(
            f"Calendar features DISABLED: history={history_years:.1f}y < {cal_min_years}y required. "
            f"(PRD Section 4.2.3)"
        )

    all_groups = []
    for (mandi_id, crop), grp in df.groupby(["mandi_id", "crop"]):
        grp = grp.copy().sort_values("date").reset_index(drop=True)
        price = grp["modal_price"]

        # -- Lag features -----------------------------------------------------
        for lag in lags:
            grp[f"lag_{lag}d"] = price.shift(lag)

        # -- Rolling features --------------------------------------------------
        for w in windows:
            grp[f"roll_mean_{w}d"] = price.shift(1).rolling(w, min_periods=max(2, w // 3)).mean()
            grp[f"roll_std_{w}d"]  = price.shift(1).rolling(w, min_periods=max(2, w // 3)).std()
            grp[f"roll_min_{w}d"]  = price.shift(1).rolling(w, min_periods=max(2, w // 3)).min()
            grp[f"roll_max_{w}d"]  = price.shift(1).rolling(w, min_periods=max(2, w // 3)).max()

        # -- Spread feature ----------------------------------------------------
        if "min_price" in grp.columns and "max_price" in grp.columns:
            grp["price_spread"] = (grp["max_price"] - grp["min_price"]) / grp["modal_price"].clip(1)

        # -- Days since observation --------------------------------------------
        if "days_since_obs" in grp.columns:
            grp["days_since_obs_feat"] = grp["days_since_obs"].shift(1)

        # -- Activity proxy (no arrivals; flagged as proxy) --------------------
        # Proxy: number of price reports in rolling 7d window (activity level)
        if "n_source_rows" in grp.columns:
            grp["activity_proxy_7d"] = grp["n_source_rows"].shift(1).rolling(7, min_periods=1).sum()
        else:
            grp["activity_proxy_7d"] = np.nan
        grp["arrivals_qt"] = np.nan  # dormant arrivals column (auto-activate if data provided)

        # -- Calendar features -------------------------------------------------
        if enable_calendar:
            grp["month"]      = grp["date"].dt.month
            grp["day_of_year"] = grp["date"].dt.dayofyear
            grp["weekday"]    = grp["date"].dt.dayofweek
        else:
            grp["month"]      = np.nan
            grp["day_of_year"] = np.nan
            grp["weekday"]    = np.nan

        # -- Weather features (from climate_summary if provided, else NaN) ------
        if climate_summary:
            # Activate dormant slots using dataset-derived regional averages.
            # Note: These are dataset-level aggregates, NOT observation-specific.
            # They add signal about the general climate risk environment.
            grp["weather_temp_mean"] = float(climate_summary.get("mean_temperature_c", np.nan))
            grp["weather_rain_7d"] = float(climate_summary.get("mean_precipitation_mm", np.nan))
            # New climate risk features (broadcast from climate scenario dataset)
            grp["climate_stress_index"] = float(climate_summary.get("mean_climate_stress_index", np.nan))
            grp["climate_stress_p95"] = float(climate_summary.get("p95_climate_stress_index", np.nan))
            grp["disease_incidence_enc"] = float(climate_summary.get("high_disease_rate", np.nan))
            grp["water_stress_enc"] = float(climate_summary.get("low_water_rate", np.nan))
            grp["shock_prior_prob"] = float(climate_summary.get("shock_prior_probability", np.nan))
        else:
            grp["weather_temp_mean"] = np.nan   # disabled
            grp["weather_rain_7d"] = np.nan     # disabled
            grp["climate_stress_index"] = np.nan
            grp["climate_stress_p95"] = np.nan
            grp["disease_incidence_enc"] = np.nan
            grp["water_stress_enc"] = np.nan
            grp["shock_prior_prob"] = np.nan

        # -- Mandi identity (deterministic MD5 hash -- R10) --------------------
        grp["mandi_id_enc"] = _mandi_hash(mandi_id)

        # -- Target columns: modal_price at t+h (R2: future, not feature) ------
        for h in horizons:
            grp[f"target_{h}d"] = price.shift(-h)

        all_groups.append(grp)

    features_df = pd.concat(all_groups, ignore_index=True)

    # Validate no synthetic leakage
    assert_no_leakage(features_df)

    feature_cols = [
        c for c in features_df.columns
        if c.startswith((
            "lag_", "roll_", "price_spread", "days_since_obs_feat",
            "activity_proxy", "month", "day_of_year", "weekday",
            "weather_", "mandi_id_enc", "arrivals_qt",
            "climate_", "disease_incidence_enc", "water_stress_enc", "shock_prior_prob",
        ))
    ]

    # Count non-NaN climate features to report activation status
    climate_cols = [c for c in feature_cols if c.startswith(("climate_", "weather_", "disease_", "water_", "shock_"))]
    climate_active = sum(1 for c in climate_cols if features_df[c].notna().any())

    logger.info(
        f"Features built: {len(features_df):,} rows, {len(feature_cols)} feature columns. "
        f"Calendar: {'ON' if enable_calendar else 'OFF'} "
        f"({'anecdotal - <2yr' if enable_calendar and history_years < 2.0 else 'ok'}). "
        f"Climate features: {climate_active}/{len(climate_cols)} active."
    )
    return features_df
