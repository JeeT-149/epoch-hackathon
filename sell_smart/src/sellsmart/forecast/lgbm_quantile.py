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
    "weather_temp_mean", "weather_rain_7d",
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
        return [c for c in FEATURE_COLS_BASE if c in df.columns and not df[c].isna().all()]

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
        
        # Embargo between splits: at least max(H) days (default 21 days) per PRD 6.8
        embargo_days = fc.get("embargo_days", 21)
        train_end_date = train["date"].max()
        val_start_date = train_end_date + pd.Timedelta(days=embargo_days)
        val = df[(df["date"] >= val_start_date) & (df.index < split_val)]
        if len(val) < 20:
            val = df.iloc[split_train:split_val]

        val_end_date = val["date"].max() if len(val) > 0 else train_end_date
        test_start_date = val_end_date + pd.Timedelta(days=embargo_days)
        test = df[df["date"] >= test_start_date]
        if len(test) < 20:
            test = df.iloc[split_val:]

        # R4: Log test access if final
        if final and log_path:
            self._log_test_access(crop, horizon, log_path)

        feature_cols = self._get_feature_cols(df)
        self.feature_cols = feature_cols

        lgb_cfg = fc.get("lgbm", {})
        quantiles = fc.get("quantiles", [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95])

        for q in quantiles:
            X_train = train[feature_cols]
            # PRD 6.2: Target y = log(P[mandi, as_of + h] / P_ref) where P_ref is observed modal price
            p_ref_train = np.maximum(train["modal_price"].values, 1.0)
            y_train = np.log(np.maximum(train[target_col].values, 1.0) / p_ref_train)

            if len(val) > 0:
                X_val = val[feature_cols]
                p_ref_val = np.maximum(val["modal_price"].values, 1.0)
                y_val = np.log(np.maximum(val[target_col].values, 1.0) / p_ref_val)
            else:
                X_val = X_train[:1]
                y_val = y_train[:1]

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
            f"Fitted {len(quantiles)} quantile models for crop={crop}, horizon={horizon}d (log-return target). "
            f"Train: {len(train)}, Val: {len(val)}, Test: {len(test)} rows."
        )

    def predict(
        self,
        features_df: pd.DataFrame,
        horizon: int,
        crop: str,
    ) -> pd.DataFrame:
        """
        Return DataFrame with price predictions per quantile: pred_q{q}_h{h}d.
        Converts log-return predictions back to price via PRD 6.2: P_q = P_ref * exp(y_q).
        Enforces quantile monotonicity (PRD 6.4).
        """
        fc = self.config.get("forecast", {})
        quantiles = sorted(fc.get("quantiles", [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]))
        feature_cols = self.feature_cols if self.feature_cols else self._get_feature_cols(features_df)

        df = features_df[features_df["crop"] == crop].copy()
        result = df[["date", "mandi_id", "crop"]].copy()

        # Ensure all trained feature cols exist in df
        for col in feature_cols:
            if col not in df.columns:
                df[col] = np.nan

        # Reference price for conversion: modal_price (or lag_1d fallback)
        p_ref = df["modal_price"].values if "modal_price" in df.columns else df["lag_1d"].values
        p_ref = np.where(np.isnan(p_ref) | (p_ref <= 0), 1000.0, p_ref)

        q_preds = []
        for q in quantiles:
            key = (crop, horizon, q)
            if key not in self.models:
                price_preds = np.full(len(df), np.nan)
            else:
                model = self.models[key]
                X = df[feature_cols]
                log_ret_preds = model.predict(X)
                # PRD 6.2: Convert log return back to price: P_q = P_ref * exp(y_q)
                price_preds = p_ref * np.exp(log_ret_preds)
            q_preds.append(price_preds)

        # Monotonicity enforcement across quantiles (PRD 6.4)
        if q_preds and not np.isnan(q_preds[0]).all():
            arr = np.array(q_preds)  # shape: (n_quantiles, n_samples)
            arr_sorted = np.sort(arr, axis=0)
            for idx, q in enumerate(quantiles):
                result[f"pred_q{int(q*100):02d}_h{horizon}d"] = arr_sorted[idx]
        else:
            for q in quantiles:
                result[f"pred_q{int(q*100):02d}_h{horizon}d"] = np.nan

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
