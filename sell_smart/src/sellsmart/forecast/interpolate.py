"""
sell_smart.forecast.interpolate
Temporal interpolation for sparse mandis and missing forecast dates.
Used to fill gaps in mandi panels where forward-fill limit exceeded.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def interpolate_sparse_panel(
    df: pd.DataFrame,
    price_col: str = "modal_price",
    max_gap_days: int = 7,
) -> pd.DataFrame:
    """
    Linear interpolation for gaps up to max_gap_days.
    Beyond that, leaves NaN for LightGBM to handle natively.

    Must only be applied to training data — never creates future values in test.
    """
    df = df.copy().sort_values("date")
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    # Identify gaps
    filled = df[price_col].interpolate(method="time", limit=max_gap_days)
    df[price_col] = filled
    return df.reset_index()
