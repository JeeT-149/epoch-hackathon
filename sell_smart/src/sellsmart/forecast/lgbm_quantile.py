"""
sell_smart.forecast.lgbm_quantile
LightGBM quantile regression for price forecasting.
Strict time-ordered splits (R3). No random train/test splits.
Test period access logged to reports/test_access_log.json (R4).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)

try:
    import lightgbm as lgb

    HAS_LGB = True
except ImportError:
    HAS_LGB = False
    logger.warning("LightGBM not installed. LGBMQuantileForecaster will raise on fit().")


FEATURE_COLS_BASE = [
    "lag_1d", "lag_2d", "lag_3d", "lag_5d", "lag_7d", "lag_14d",
    "roll_mean_7d", "roll_mean_14d", "roll_mean_21d",
    "roll_std_7d", "roll_std_14d",
    "roll_min_7d", "roll_max_7d",
    "price_spread",
    "days_since_obs_feat",
    "activity_proxy_7d",
    "month", "day_of_year",
    "mandi_id_enc",
]


class LGBMQuantileForecaster:
    """
    One model per (crop, horizon, quantile).
    Time-ordered splits: train [0, split_train), val [split_train, split_val), test [split_val, end).
    """

    def __init__(self, config: dict, seed: int = 42):
        self.config = config
        self.seed = seed
        self.models: dict = {}  # key: (crop, horizon, quantile) -> lgb.Booster
        self.feature_cols: list[str] = []

    def _get_feature_cols(self, df: pd.DataFrame) -> list[str]:
        return [c for c in FEATURE_COLS_BASE if c in df.columns]

    def fit(
        self,
        features_df: pd.DataFrame,
        horizon: int,
        crop: str,
        final: bool = False,
        log_path: Optional[Path] = None,
    ) -> None:
        if not HAS_LGB:
            raise ImportError("LightGBM is required. Install with: pip install lightgbm")

        target_col = f"target_{horizon}d"
        if target_col not in features_df.columns:
            raise ValueError(f"Target column '{target_col}' not in features.")

        df = features_df[features_df["crop"] == crop].dropna(subset=[target_col]).copy()
        df = df.sort_values("date").reset_index(drop=True)

        n = len(df)
        fc = self.config.get("forecast", {})
        train_frac = fc.get("train_fraction", 0.70)
        val_frac = fc.get("val_fraction", 0.15)

        split_train = int(n * train_frac)
        split_val = int(n * (train_frac + val_frac))

        train = df.iloc[:split_train]
        val = df.iloc[split_train:split_val]
        test = df.iloc[split_val:]

        # R4: Log test access if final
        if final and log_path:
            self._log_test_access(crop, horizon, log_path)

        feature_cols = self._get_feature_cols(df)
        self.feature_cols = feature_cols

        lgb_cfg = fc.get("lgbm", {})
        quantiles = fc.get("quantiles", [0.1, 0.25, 0.5, 0.75, 0.9])

        for q in quantiles:
            X_train = train[feature_cols]
            y_train = train[target_col]
            X_val = val[feature_cols] if len(val) > 0 else X_train[:1]
            y_val = val[target_col] if len(val) > 0 else y_train[:1]

            train_data = lgb.Dataset(X_train, label=y_train)
            val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

            params = {
                "objective": "quantile",
                "alpha": q,
                "num_leaves": lgb_cfg.get("num_leaves", 63),
                "learning_rate": lgb_cfg.get("learning_rate", 0.05),
                "min_child_samples": lgb_cfg.get("min_child_samples", 20),
                "subsample": lgb_cfg.get("subsample", 0.8),
                "colsample_bytree": lgb_cfg.get("colsample_bytree", 0.8),
                "seed": self.seed,
                "verbosity": -1,
            }

            model = lgb.train(
                params,
                train_data,
                num_boost_round=lgb_cfg.get("n_estimators", 500),
                valid_sets=[val_data],
                callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(-1)],
            )
            self.models[(crop, horizon, q)] = model

        logger.info(
            f"Fitted {len(quantiles)} quantile models for crop={crop}, horizon={horizon}d. "
            f"Train: {len(train)}, Val: {len(val)}, Test: {len(test)} rows."
        )

    def predict(
        self,
        features_df: pd.DataFrame,
        horizon: int,
        crop: str,
    ) -> pd.DataFrame:
        """Return DataFrame with one column per quantile: pred_q{q}_h{h}d."""
        fc = self.config.get("forecast", {})
        quantiles = fc.get("quantiles", [0.1, 0.25, 0.5, 0.75, 0.9])
        feature_cols = self._get_feature_cols(features_df)

        df = features_df[features_df["crop"] == crop].copy()
        result = df[["date", "mandi_id", "crop"]].copy()

        for q in quantiles:
            key = (crop, horizon, q)
            if key not in self.models:
                result[f"pred_q{int(q*100)}_h{horizon}d"] = np.nan
                continue
            model = self.models[key]
            X = df[feature_cols]
            result[f"pred_q{int(q*100)}_h{horizon}d"] = model.predict(X)

        return result

    def _log_test_access(self, crop: str, horizon: int, log_path: Path) -> None:
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        entries = []
        if log_path.exists():
            with open(log_path) as f:
                entries = json.load(f)
        entries.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "crop": crop,
            "horizon": horizon,
            "note": "Final test run with --final flag",
        })
        with open(log_path, "w") as f:
            json.dump(entries, f, indent=2)
