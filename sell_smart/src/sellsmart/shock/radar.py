"""
sell_smart.shock.radar
Policy-Shock Radar: detect unusual price movements via z-score.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


def detect_shocks(
    price_series: pd.Series,
    z_threshold: float = 3.0,
    lookback_window: int = 30,
) -> pd.DataFrame:
    """
    Detect price shocks via rolling z-score.

    Returns DataFrame with [date, price, rolling_mean, rolling_std, z_score, is_shock].
    """
    roll_mean = price_series.shift(1).rolling(lookback_window, min_periods=5).mean()
    roll_std = price_series.shift(1).rolling(lookback_window, min_periods=5).std().clip(lower=1.0)
    z_score = (price_series - roll_mean) / roll_std

    df = pd.DataFrame({
        "price": price_series,
        "rolling_mean": roll_mean,
        "rolling_std": roll_std,
        "z_score": z_score,
        "is_shock": z_score.abs() > z_threshold,
    })
    n_shocks = df["is_shock"].sum()
    if n_shocks > 0:
        logger.info(f"Shock radar: {n_shocks} shock events detected (z>{z_threshold}).")
    return df
