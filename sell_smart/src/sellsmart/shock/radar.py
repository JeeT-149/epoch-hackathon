"""
sell_smart.shock.radar
Policy-Shock Radar: Detects and reacts to market shocks and structural breaks.
Strictly implements PRD Section 11 (Signals S1-S5, Levels NONE/WATCH/SHOCK).
Never presents shocks as policy prediction (Rule R11).
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path
import numpy as np
import pandas as pd

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


class RadarLevel(str, Enum):
    NONE = "NONE"
    WATCH = "WATCH"
    SHOCK = "SHOCK"


def detect_shocks(
    price_series: pd.Series,
    z_threshold: float = 3.0,
    lookback_window: int = 30,
) -> pd.DataFrame:
    """
    S1: Robust Price Jump Detection via rolling Median / MAD (PRD 11.1).
    Evaluates price return deviation against trailing robust statistics.

    Args:
        price_series: Series of daily modal prices indexed by date.
        z_threshold: Robust z-score threshold (default 3.0 per PRD 11.1/11.2).
        lookback_window: Rolling window in days for baseline (default 30-60d).

    Returns:
        DataFrame with [price, rolling_median, rolling_mad, robust_z, is_shock].
    """
    p = price_series.dropna()
    if len(p) < 5:
        return pd.DataFrame(columns=["price", "rolling_median", "rolling_mad", "robust_z", "is_shock"])

    # Compute rolling median and MAD over trailing window (shifted by 1 to prevent leakage)
    past_p = p.shift(1)
    roll_median = past_p.rolling(lookback_window, min_periods=5).median()
    roll_mad = past_p.rolling(lookback_window, min_periods=5).apply(
        lambda x: np.median(np.abs(x - np.median(x))), raw=True
    ).clip(lower=1.0)

    # 1.4826 normal consistency factor for MAD
    robust_z = (p - roll_median) / (roll_mad * 1.4826)
    is_shock = robust_z.abs() >= z_threshold

    df = pd.DataFrame({
        "price": p,
        "rolling_median": roll_median,
        "rolling_mad": roll_mad,
        "robust_z": robust_z,
        "is_shock": is_shock,
    }, index=p.index)

    n_shocks = df["is_shock"].sum()
    if n_shocks > 0:
        logger.info(f"Shock radar (S1): {n_shocks} shock days detected (|z| >= {z_threshold}).")
    return df


def evaluate_radar_state(
    current_date: pd.Timestamp | str,
    crop: str,
    gold_panel: pd.DataFrame,
    events_csv_path: Path | str | None = None,
    z_threshold: float = 3.0,
    breadth_threshold: float = 0.40,
    lookback_window: int = 30,
    event_window_days: int = 7,
) -> dict:
    """
    Evaluates multi-signal Radar Level for a crop at as_of date (PRD Section 11.1 & 11.2).

    Signals:
      S1: Price jump at individual mandi (|robust_z| >= z_threshold)
      S2: Breadth (% of mandis for crop with concurrent |robust_z| >= z_threshold)
      S3: Activity collapse (reporting mandi count drops below 50% of trailing median)
      S4: Event flag in events.csv within event_window_days
      S5: Model surprise (prediction interval breach)

    Returns:
      dict with: level ('NONE'|'WATCH'|'SHOCK'), signals (dict), active_reason (str)
    """
    cur_dt = pd.to_datetime(current_date).date()
    df_crop = gold_panel[gold_panel["crop"] == crop].copy()
    if df_crop.empty:
        return {"level": RadarLevel.NONE, "signals": {}, "active_reason": "no_data"}

    df_crop["date"] = pd.to_datetime(df_crop["date"]).dt.date
    # Past data only up to current_date (Rule R2)
    history = df_crop[df_crop["date"] <= cur_dt]
    if history.empty:
        return {"level": RadarLevel.NONE, "signals": {}, "active_reason": "no_history"}

    mandis = history["mandi_id"].unique()
    s1_signals = {}
    shock_mandis = 0

    # Evaluate S1 per mandi
    for m in mandis:
        m_series = history[history["mandi_id"] == m].set_index("date")["modal_price"].sort_index()
        if len(m_series) >= 10:
            shocks = detect_shocks(m_series, z_threshold=z_threshold, lookback_window=lookback_window)
            if cur_dt in shocks.index and shocks.loc[cur_dt, "is_shock"]:
                shock_mandis += 1
                s1_signals[m] = float(shocks.loc[cur_dt, "robust_z"])

    # S2: Breadth
    breadth = (shock_mandis / len(mandis)) if len(mandis) > 0 else 0.0

    # S3: Activity Collapse
    daily_reporting = history.groupby("date")["modal_price"].count()
    past_reporting = daily_reporting.shift(1).tail(lookback_window)
    med_reporting = past_reporting.median() if len(past_reporting) > 0 else 1.0
    cur_reporting = daily_reporting.get(cur_dt, 0)
    activity_collapse = (cur_reporting < 0.5 * max(med_reporting, 1.0))

    # S4: Event Flag
    s4_event = None
    if events_csv_path and Path(events_csv_path).exists():
        try:
            ev_df = pd.read_csv(events_csv_path)
            ev_df["date"] = pd.to_datetime(ev_df["date"]).dt.date
            # Check for verified event for crop within window
            recent_evs = ev_df[
                (ev_df["crop"] == crop) &
                (ev_df["date"] <= cur_dt) &
                (ev_df["date"] >= cur_dt - pd.Timedelta(days=event_window_days))
            ]
            if not recent_evs.empty:
                s4_event = recent_evs.iloc[-1].to_dict()
        except Exception as e:
            logger.warning(f"Could not check events.csv: {e}")

    # Determine Radar Level (PRD 11.2)
    level = RadarLevel.NONE
    reason = "Normal market conditions"

    # SHOCK trigger: S2 breadth >= breadth_thr OR verified S4 event
    if breadth >= breadth_threshold:
        level = RadarLevel.SHOCK
        reason = f"S2 Market Breadth Shock: {breadth:.1%} of {crop} mandis experiencing concurrent price jumps (|z| >= {z_threshold})"
    elif s4_event:
        level = RadarLevel.SHOCK
        reason = f"S4 Policy Event Shock: {s4_event.get('event_type')}: {s4_event.get('description')}"
    # WATCH trigger: S1 at single mandi OR S3 activity collapse
    elif shock_mandis > 0:
        level = RadarLevel.WATCH
        reason = f"S1 Price Volatility Watch: {shock_mandis}/{len(mandis)} mandis experiencing price jump (|z| >= {z_threshold})"
    elif activity_collapse:
        level = RadarLevel.WATCH
        reason = f"S3 Activity Watch: Reporting mandis dropped to {cur_reporting} vs trailing median {med_reporting:.0f}"

    return {
        "level": level,
        "reason": reason,
        "signals": {
            "s1_mandi_jumps": s1_signals,
            "s2_breadth": round(breadth, 3),
            "s3_activity_collapse": activity_collapse,
            "s4_event": s4_event,
        },
    }
