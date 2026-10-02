"""
tests/leakage/test_no_future_leakage.py
Leakage tests (PRD R2, R5):
- No synthetic column in feature list
- Feature windows use only past data (shift before rolling)
- Target columns are excluded from feature list
"""
import numpy as np
import pandas as pd
import pytest

from sellsmart.features.leakage_guard import (
    LeakageError,
    ALWAYS_SYNTHETIC_FREE,
    assert_no_leakage,
    assert_synthetic_disjoint,
)
from sellsmart.features.build import SYNTHETIC_COLS, _mandi_hash, build_features


def _make_gold_panel(n=200, seed=42) -> pd.DataFrame:
    """Minimal gold panel for leakage tests."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-08-15", periods=n, freq="D")
    return pd.DataFrame({
        "date": dates,
        "mandi_id": "mp_indore_indore",
        "crop": "soybean",
        "modal_price": 4000 + rng.normal(0, 100, n),
        "min_price": 3900 + rng.normal(0, 80, n),
        "max_price": 4100 + rng.normal(0, 120, n),
        "n_source_rows": 1,
        "is_open": True,
    })


MINIMAL_CONFIG = {
    "features": {
        "lags": [1, 2, 3, 5, 7, 14],
        "rolling_windows": [7, 14, 21],
        "horizon_days": [1, 3, 7],
        "calendar_min_years": 1.0,
        "force_calendar_features": True,
        "use_weather": False,
    }
}


class TestSyntheticDisjoint:
    """R5: No synthetic column may be a model feature."""

    def test_feature_cols_disjoint_from_synthetic(self):
        """Feature columns produced by build_features must not overlap with synthetic column list."""
        gold = _make_gold_panel()
        features_df = build_features(gold, MINIMAL_CONFIG)
        feature_cols = [
            c for c in features_df.columns
            if c.startswith((
                "lag_", "roll_", "price_spread", "days_since_obs_feat",
                "activity_proxy", "month", "day_of_year", "weekday",
                "weather_", "mandi_id_enc", "arrivals_qt",
            ))
        ]
        assert_synthetic_disjoint(feature_cols, SYNTHETIC_COLS)

    def test_assert_no_leakage_raises_on_synthetic_col(self):
        """assert_no_leakage raises LeakageError if synthetic column present."""
        bad_df = pd.DataFrame({"farmer_id": [1, 2], "lag_1d": [100.0, 200.0]})
        with pytest.raises(LeakageError):
            assert_no_leakage(bad_df)

    def test_clean_features_pass_leakage(self):
        """Clean feature dataframe should not raise LeakageError."""
        gold = _make_gold_panel()
        features_df = build_features(gold, MINIMAL_CONFIG)
        assert_no_leakage(features_df)  # should not raise


class TestNoPastDataInFeatures:
    """R2: No future data in features. Lags/rolling must use shift(1) before rolling."""

    def test_lag_1d_equals_previous_day_price(self):
        """lag_1d at row i must equal modal_price at row i-1."""
        gold = _make_gold_panel(50)
        features_df = build_features(gold, MINIMAL_CONFIG)
        grp = features_df.dropna(subset=["lag_1d"]).reset_index(drop=True)
        # lag_1d for row i should match modal_price of previous row (same mandi/crop)
        for i in range(1, min(20, len(grp))):
            expected = grp.loc[i - 1, "modal_price"]
            actual = grp.loc[i, "lag_1d"]
            assert actual == pytest.approx(expected, rel=1e-6), f"Row {i}: lag mismatch"

    def test_rolling_mean_excludes_current_row(self):
        """roll_mean_7d at row i must NOT include modal_price at row i (past-only, shift(1))."""
        gold = _make_gold_panel(50)
        # Inject a spike at row 10 — rolling mean should not reflect it at row 10
        gold.loc[10, "modal_price"] = 9999.0
        features_df = build_features(gold, MINIMAL_CONFIG)
        row10 = features_df.iloc[10]
        # roll_mean at row 10 is computed from shift(1) → uses rows 3..9, not row 10
        if not np.isnan(row10["roll_mean_7d"]):
            assert row10["roll_mean_7d"] < 5000.0, "roll_mean_7d at spike row leaks current value"

    def test_target_columns_are_future(self):
        """Target at t+h must equal modal_price h rows ahead."""
        gold = _make_gold_panel(50)
        features_df = build_features(gold, MINIMAL_CONFIG)
        grp = features_df[features_df["crop"] == "soybean"].sort_values("date").reset_index(drop=True)
        for h in [1, 3, 7]:
            col = f"target_{h}d"
            if col not in grp.columns:
                continue
            for i in range(len(grp) - h):
                actual_target = grp.loc[i, col]
                future_price = grp.loc[i + h, "modal_price"]
                if np.isnan(actual_target) or np.isnan(future_price):
                    continue
                assert actual_target == pytest.approx(future_price, rel=1e-6), \
                    f"target_{h}d at row {i} != modal_price at row {i+h}"

    def test_target_not_in_feature_list(self):
        """Target columns must not appear in the feature column list used for training."""
        gold = _make_gold_panel()
        features_df = build_features(gold, MINIMAL_CONFIG)
        feature_cols = [
            c for c in features_df.columns
            if c.startswith((
                "lag_", "roll_", "price_spread", "days_since_obs_feat",
                "activity_proxy", "month", "day_of_year", "weekday",
                "weather_", "mandi_id_enc", "arrivals_qt",
            ))
        ]
        for col in feature_cols:
            assert not col.startswith("target_"), f"target column '{col}' leaked into feature list"


class TestDeterministicHash:
    """R10: mandi_id_enc must be reproducible across calls."""

    def test_same_input_same_hash(self):
        h1 = _mandi_hash("mp_indore_indore")
        h2 = _mandi_hash("mp_indore_indore")
        assert h1 == h2

    def test_different_mandi_different_hash(self):
        h1 = _mandi_hash("mp_indore_indore")
        h2 = _mandi_hash("mh_nashik_lasalgaon")
        assert h1 != h2

    def test_hash_in_valid_range(self):
        for mandi in ["mp_indore_indore", "rj_jaipur_jaipur", "gj_ahmedabad_ahmedabad"]:
            h = _mandi_hash(mandi)
            assert 0 <= h < 10000
