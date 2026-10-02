"""
sell_smart.trigger.compute
Trigger threshold computation: price drop/rise vs reference.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def compute_price_change(
    current_price: float,
    reference_price: float,
) -> dict:
    """
    Compute price change from reference.
    Returns pct_change, direction, and whether thresholds are crossed.
    """
    if reference_price <= 0:
        return {"pct_change": 0.0, "direction": "flat", "exceeded_drop": False, "exceeded_rise": False}
    pct = (current_price - reference_price) / reference_price
    return {
        "pct_change": round(pct, 4),
        "direction": "up" if pct > 0 else ("down" if pct < 0 else "flat"),
        "exceeded_drop": pct <= 0,  # thresholds applied in monitor.py
        "exceeded_rise": pct >= 0,
    }


def compute_trigger_signals(
    price_series: pd.Series,
    drop_threshold: float = 0.10,
    rise_threshold: float = 0.10,
    lookback: int = 7,
) -> pd.DataFrame:
    """
    For each date in price_series, compute if a trigger fires.
    Reference = rolling mean of last `lookback` days.

    Returns DataFrame with [date, price, reference_price, pct_change,
                             trigger_drop, trigger_rise].
    """
    prices = price_series.copy()
    ref = prices.shift(1).rolling(lookback, min_periods=1).mean()
    pct = (prices - ref) / ref.clip(lower=1.0)

    df = pd.DataFrame({
        "price": prices,
        "reference_price": ref,
        "pct_change": pct,
        "trigger_drop": pct <= -drop_threshold,
        "trigger_rise": pct >= rise_threshold,
    })
    return df
