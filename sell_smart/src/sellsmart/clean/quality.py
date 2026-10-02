"""
sell_smart.clean.quality
Outlier detection and Data Quality Score per (mandi, crop).
Uses robust statistics (rolling MAD) — no hard-coded price ranges (R rule).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


def flag_outliers(
    df: pd.DataFrame,
    k: float = 6.0,
    window: int = 30,
) -> pd.DataFrame:
    """
    Per (mandi_id, crop): rolling median ± k × MAD outlier detection.
    Flags 'suspect_outlier' in dq_flags. Suspect rows are excluded from
    features and NEVER used as 'current price' in a decision.

    Args:
        df: Silver DataFrame with [date, mandi_id, crop, modal_price, dq_flags].
        k: MAD multiplier (default 6, config quality.outlier_k).
        window: rolling window in days for baseline.

    Returns:
        DataFrame with dq_flags updated.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["mandi_id", "crop", "date"])

    def _flag_group(grp: pd.DataFrame) -> pd.DataFrame:
        grp = grp.copy()
        prices = grp["modal_price"]
        roll_med = prices.rolling(window, min_periods=3, center=False).median()
        roll_mad = prices.rolling(window, min_periods=3, center=False).apply(
            lambda x: np.median(np.abs(x - np.median(x))), raw=True
        )
        # Consistent MAD; avoid division by zero
        mad_safe = roll_mad.clip(lower=1.0)
        z_like = (prices - roll_med).abs() / (mad_safe * 1.4826)
        suspect = z_like > k
        for idx in grp.index[suspect]:
            flags = grp.at[idx, "dq_flags"]
            if isinstance(flags, list) and "suspect_outlier" not in flags:
                grp.at[idx, "dq_flags"] = flags + ["suspect_outlier"]
        return grp

    result = df.groupby(["mandi_id", "crop"], group_keys=False).apply(_flag_group)
    n_suspect = result["dq_flags"].apply(
        lambda f: "suspect_outlier" in (f if isinstance(f, list) else [])
    ).sum()
    logger.info(f"Outlier detection: {n_suspect:,} rows flagged as suspect_outlier.")
    return result.reset_index(drop=True)


def compute_dq_scores(
    df: pd.DataFrame,
    lookback_days: int = 90,
    weights: dict | None = None,
) -> pd.DataFrame:
    """
    Compute a Data Quality Score in [0,1] per (mandi_id, crop).

    Metrics:
        - coverage: fraction of trading days with a price in last lookback_days
        - gap_penalty: inverse longest gap (in lookback window)
        - recency: 1 if last observation within 7 days, decays
        - suspect_rate: fraction of rows flagged suspect

    Returns:
        DataFrame with columns [mandi_id, crop, dq_score, coverage, longest_gap_days,
                                 last_obs_days_ago, suspect_rate].
    """
    if weights is None:
        weights = {
            "coverage": 0.40,
            "gap_penalty": 0.25,
            "recency": 0.20,
            "clean_rate": 0.15,
        }

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    ref_date = df["date"].max()
    cutoff = ref_date - pd.Timedelta(days=lookback_days)
    recent = df[df["date"] >= cutoff].copy()

    rows = []
    for (mandi_id, crop), grp in recent.groupby(["mandi_id", "crop"]):
        dates = grp["date"].drop_duplicates().sort_values()
        trading_days = pd.bdate_range(cutoff, ref_date, freq="B")  # business days proxy
        n_trading = max(len(trading_days), 1)

        # Coverage
        coverage = len(dates) / n_trading

        # Longest gap
        if len(dates) > 1:
            gaps = (dates.diff().dt.days).dropna()
            longest_gap = int(gaps.max())
        else:
            longest_gap = lookback_days  # penalise single observation

        # Recency
        last_obs = dates.max() if len(dates) > 0 else cutoff
        days_ago = (ref_date - last_obs).days
        recency_score = max(0.0, 1.0 - days_ago / 14.0)

        # Suspect rate
        has_suspect = grp["dq_flags"].apply(
            lambda f: "suspect_outlier" in (f if isinstance(f, list) else [])
        )
        suspect_rate = has_suspect.mean()
        clean_rate = 1.0 - suspect_rate

        # Gap penalty [0,1]: 0 if gap >= lookback, 1 if gap = 1
        gap_score = max(0.0, 1.0 - (longest_gap - 1) / (lookback_days - 1))

        dq_score = (
            weights["coverage"] * min(coverage, 1.0)
            + weights["gap_penalty"] * gap_score
            + weights["recency"] * recency_score
            + weights["clean_rate"] * clean_rate
        )

        rows.append({
            "mandi_id": mandi_id,
            "crop": crop,
            "dq_score": round(dq_score, 4),
            "coverage": round(min(coverage, 1.0), 4),
            "longest_gap_days": longest_gap,
            "last_obs_days_ago": days_ago,
            "suspect_rate": round(suspect_rate, 4),
        })

    result = pd.DataFrame(rows).sort_values("dq_score", ascending=False)
    logger.info(f"DQ scores computed for {len(result)} (mandi, crop) pairs.")
    return result
