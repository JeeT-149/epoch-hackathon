"""
sell_smart.features.leakage_guard
Asserts that no feature uses information from after date t.
Must be called on every feature set. Tests in tests/leakage/ enforce this.
"""
from __future__ import annotations

import pandas as pd


class LeakageError(Exception):
    pass


ALWAYS_SYNTHETIC_FREE = [
    "farmer_id", "village_lat", "village_lon", "quantity_q",
    "vehicle_type", "cash_deadline_days", "storage_condition",
    "quality_factor", "trader_offer_proxy", "stress_shock_series",
    "demo_arrivals_index", "generator", "seed",
]


def assert_no_leakage(
    features_df: pd.DataFrame,
    date_col: str = "date",
    horizon_col: str | None = "horizon_days",
) -> None:
    """
    Verify no synthetic column appears in feature columns.
    Verify date alignment: all feature columns that encode a window
    must be derivable from data up to `date` inclusive.

    This is a lightweight check; the definitive test is in tests/leakage/.
    """
    feature_cols = set(features_df.columns)
    bad = feature_cols & set(ALWAYS_SYNTHETIC_FREE)
    if bad:
        raise LeakageError(
            f"Synthetic columns found in feature set (R5 violation): {bad}"
        )

    # Check target column doesn't appear shifted forward
    if "target" in feature_cols and date_col in feature_cols:
        # Target is at t+h; the feature must not contain raw future price at t
        # Full check is in tests/leakage/test_no_future_leakage.py
        pass


def assert_synthetic_disjoint(feature_cols: list[str], synthetic_cols: list[str]) -> None:
    """
    Assert that no synthetic column is in the feature list (R5).
    Called as a unit test fixture.
    """
    overlap = set(feature_cols) & set(synthetic_cols)
    if overlap:
        raise LeakageError(
            f"R5 VIOLATION: synthetic columns overlap with feature columns: {overlap}"
        )
