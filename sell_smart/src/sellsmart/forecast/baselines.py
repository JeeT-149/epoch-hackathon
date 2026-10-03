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

    def __init__(self, window: int = 14):
        self.window = window
        self.name = f"rolling_mean_{window}d"

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.Series:
        col = f"roll_mean_{self.window}d"
        if col in features_df.columns:
            return features_df[col].rename(f"pred_{horizon}d")
        return pd.Series(np.nan, index=features_df.index, name=f"pred_{horizon}d")


class EmpiricalReturnForecaster:
    """
    B3: Empirical return distribution baseline (PRD Section 6.4).
    Trailing-window quantiles of h-day log returns per crop and mandi cluster.
    Forecast: y_{t+h}^{(q)} = P_t * exp(quantile(r_{t, h}, q))
    where r_{t, h} = ln(P_{t+h} / P_t).
    """

    name = "empirical_return_quantiles"

    def __init__(self, quantiles: list[float] | None = None):
        self.quantiles = quantiles or [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]
        self.log_return_quantiles: dict[tuple[str, int], dict[float, float]] = {}

    def fit(self, train_df: pd.DataFrame, horizon: int, crop: str) -> None:
        """Fit empirical return quantiles on training/trailing data."""
        t_col = f"target_{horizon}d"
        if t_col not in train_df.columns or "modal_price" not in train_df.columns:
            return
        valid = train_df[
            (train_df["crop"] == crop)
            & train_df[t_col].notna()
            & train_df["modal_price"].notna()
            & (train_df["modal_price"] > 0)
        ]
        if len(valid) < 10:
            return
        log_rets = np.log(valid[t_col].values / valid["modal_price"].values)
        self.log_return_quantiles[(crop, horizon)] = {
            q: float(np.quantile(log_rets, q)) for q in self.quantiles
        }

    def predict_quantiles(
        self, df: pd.DataFrame, horizon: int, crop: str
    ) -> dict[float, np.ndarray]:
        """Predict price quantiles given reference prices in df['modal_price']."""
        key = (crop, horizon)
        base_p = df["modal_price"].values.copy()
        if key not in self.log_return_quantiles:
            return {q: base_p.copy() for q in self.quantiles}
        q_dict = self.log_return_quantiles[key]
        return {q: base_p * np.exp(q_dict[q]) for q in self.quantiles}

