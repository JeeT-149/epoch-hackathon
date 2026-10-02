"""
sell_smart.synth.stress
Stress test series: inject labelled shocks into copies of real series.
Used only for unit tests and clearly labelled demo content.
NEVER presented as a real event (R5).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


def generate_stress_series(
    real_series: pd.Series,
    shock_day: int,
    shock_magnitude: float = -0.30,
    seed: int = 42,
) -> pd.Series:
    """
    Inject a labelled price shock into a copy of a real price series.

    Returns a Series with 'is_synthetic=True' metadata.
    Clearly labelled: NEVER used in forecasting or backtest (R5).
    """
    rng = np.random.default_rng(seed)
    series = real_series.copy()
    if shock_day < len(series):
        series.iloc[shock_day:] *= (1 + shock_magnitude)
        # Add small noise
        noise = rng.normal(0, 0.01, size=len(series) - shock_day)
        series.iloc[shock_day:] += series.iloc[shock_day:].mean() * noise

    series.attrs["is_synthetic"] = True
    series.attrs["generator"] = "stress_v1"
    series.attrs["shock_day"] = shock_day
    series.attrs["shock_magnitude"] = shock_magnitude
    series.attrs["note"] = "SYNTHETIC STRESS TEST — clearly labelled, never real data"
    logger.warning(
        "stress_series generated. This is a SYNTHETIC series for testing only. "
        "Never present as real data (R5)."
    )
    return series


def generate_golden_series(seed: int = 42) -> dict[str, pd.Series]:
    """
    Generate golden unit-test fixtures:
    - rising: engine should WAIT
    - falling: engine should SELL NOW
    - flat: engine should ACCEPT
    - shock: hold suspended
    All are synthetic (R5).
    """
    n = 30
    idx = pd.date_range("2025-01-01", periods=n, freq="D")

    rising = pd.Series(1000 + np.linspace(0, 200, n), index=idx, name="rising")
    falling = pd.Series(1000 - np.linspace(0, 200, n), index=idx, name="falling")
    flat = pd.Series(np.full(n, 1000.0), index=idx, name="flat")
    shock = pd.Series(
        [1000.0] * 15 + [600.0] * 15, index=idx, name="shock"
    )

    for s in [rising, falling, flat, shock]:
        s.attrs["is_synthetic"] = True
        s.attrs["generator"] = "golden_fixtures_v1"
        s.attrs["note"] = "SYNTHETIC golden test fixture (R5)"

    return {"rising": rising, "falling": falling, "flat": flat, "shock": shock}
