"""
sell_smart.calibration.passport
Calibration Passport: model coverage and interval calibration metrics.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


def compute_calibration_passport(
    y_true: np.ndarray,
    y_pred_quantiles: dict[float, np.ndarray],
    conformal_lower: np.ndarray | None = None,
    conformal_upper: np.ndarray | None = None,
    crop: str = "",
    horizon: int = 0,
    mandi_id: str = "",
) -> dict:
    """
    Compute Calibration Passport: empirical coverage per quantile.

    For each quantile q, a calibrated model should have ~q of predictions below y_true.
    """
    n = len(y_true)
    calibration = {}

    for q, preds in y_pred_quantiles.items():
        empirical_fraction = float((y_true < preds).mean())
        calibration[f"q{int(q * 100)}"] = {
            "target_coverage": q,
            "empirical_fraction_below": empirical_fraction,
            "calibration_error": abs(empirical_fraction - q),
        }

    # Conformal interval coverage
    if conformal_lower is not None and conformal_upper is not None:
        covered = ((y_true >= conformal_lower) & (y_true <= conformal_upper)).mean()
        width = (conformal_upper - conformal_lower).mean()
        calibration["conformal"] = {
            "empirical_coverage": float(covered),
            "mean_interval_width": float(width),
        }

    passport = {
        "crop": crop,
        "mandi_id": mandi_id,
        "horizon_days": horizon,
        "n_test_samples": n,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "calibration": calibration,
    }
    return passport


def save_passport(passport: dict, output_dir: Path, name: str = "calibration_passport") -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{name}.json"
    with open(path, "w") as f:
        json.dump(passport, f, indent=2)
    logger.info(f"Calibration passport saved to {path}")
    return path
