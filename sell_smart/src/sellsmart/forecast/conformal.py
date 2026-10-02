"""
sell_smart.forecast.conformal
Conformal prediction intervals on top of point / quantile forecasts.
Uses split conformal (exchangeability assumed on val set).
Target coverage: 1 - alpha (default 90%).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


class ConformalPredictor:
    """
    Split conformal prediction wrapper.
    Calibrates on a held-out calibration set; applies to new data.

    PRD requirement: calibrated uncertainty. This gives coverage guarantees
    under exchangeability (satisfied by time-ordered splits with similar
    distribution).
    """

    def __init__(self, alpha: float = 0.1, min_calibration_size: int = 50):
        self.alpha = alpha
        self.min_calibration_size = min_calibration_size
        self.q_hat: float | None = None
        self.calibrated: bool = False

    def calibrate(self, y_true: np.ndarray, y_pred: np.ndarray) -> None:
        """
        Compute nonconformity scores on calibration set.
        Nonconformity score = |y_true - y_pred| (symmetric).
        """
        n = len(y_true)
        if n < self.min_calibration_size:
            logger.warning(
                f"Conformal calibration: only {n} samples (need {self.min_calibration_size}). "
                "Interval may be unreliable."
            )
        scores = np.abs(y_true - y_pred)
        level = np.ceil((1 - self.alpha) * (n + 1)) / n
        level = min(level, 1.0)
        self.q_hat = float(np.quantile(scores, level))
        self.calibrated = True
        logger.info(
            f"Conformal calibrated: alpha={self.alpha}, "
            f"q_hat={self.q_hat:.2f}, n_cal={n}"
        )

    def predict_interval(self, y_pred: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return (lower, upper) prediction interval."""
        if not self.calibrated or self.q_hat is None:
            raise RuntimeError("Call calibrate() before predict_interval().")
        lower = y_pred - self.q_hat
        upper = y_pred + self.q_hat
        return lower, upper

    def coverage_report(self, y_true: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> dict:
        """Compute empirical coverage on a test set."""
        covered = ((y_true >= lower) & (y_true <= upper)).mean()
        width = (upper - lower).mean()
        return {
            "empirical_coverage": float(covered),
            "target_coverage": 1 - self.alpha,
            "mean_interval_width": float(width),
            "q_hat": self.q_hat,
        }
