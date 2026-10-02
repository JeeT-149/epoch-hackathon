"""
sell_smart.forecast.baselines
Baseline forecasters: naive (last value), seasonal-naive (same weekday 52w ago).
Used as comparison benchmarks in backtest.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


class NaiveForecaster:
    """Predict last observed price (horizon-agnostic)."""

    name = "naive_last"

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.Series:
        return features_df["lag_1d"].rename(f"pred_{horizon}d")


class SeasonalNaiveForecaster:
    """
    Predict price from same weekday ~52 weeks ago.
    If insufficient history, returns NaN with a 'n/a (insufficient history)' marker.
    PRD 4.2.3: 'Never silently skip.'
    """

    name = "seasonal_naive"
    min_history_days = 364  # ~ 52 weeks

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.Series:
        lag_col = "lag_364d"  # 52 weeks
        if lag_col in features_df.columns:
            result = features_df[lag_col].copy()
        else:
            result = pd.Series(np.nan, index=features_df.index)
            logger.info(
                f"SeasonalNaiveForecaster: lag_364d not in features. "
                f"Returning NaN — 'n/a (insufficient history)' (PRD 4.2.3)."
            )
        result.name = f"pred_{horizon}d"
        result.attrs["evaluable"] = result.notna().any()
        result.attrs["note"] = (
            "n/a (insufficient history)"
            if result.isna().all()
            else "seasonal_naive"
        )
        return result


class RollingMeanForecaster:
    """Predict rolling mean of last N days."""

    name = "rolling_mean_14d"

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.Series:
        col = "roll_mean_14d"
        if col in features_df.columns:
            return features_df[col].rename(f"pred_{horizon}d")
        return pd.Series(np.nan, index=features_df.index, name=f"pred_{horizon}d")
