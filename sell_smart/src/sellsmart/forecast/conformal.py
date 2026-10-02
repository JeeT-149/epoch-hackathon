"""
sell_smart.forecast.conformal
Conformalized Quantile Regression (CQR) on nested intervals (PRD Section 6.6).

For each crop and horizon, calibrates nested quantile pairs on the calibration set:
  - (0.25, 0.75) -> Nominal 50% interval (alpha = 0.50)
  - (0.10, 0.90) -> Nominal 80% interval (alpha = 0.20)
  - (0.05, 0.95) -> Nominal 90% interval (alpha = 0.10)

For each pair (lo, hi):
  Nonconformity score: E_i = max(q_lo_i - y_i, y_i - q_hi_i)
  Conformal margin:    m = quantile(E, ceil((n + 1) * (1 - alpha)) / n)
  Calibrated bounds:   [q_lo - m, q_hi + m]
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


class CQRCalibrator:
    """
    Conformalized Quantile Regression (CQR) calibrator on nested quantile pairs (PRD Section 6.6).
    """

    def __init__(self, min_calibration_size: int = 30):
        self.min_calibration_size = min_calibration_size
        self.margins: dict[tuple[float, float], float] = {}
        self.calibrated = False

    def calibrate(
        self,
        y_true: np.ndarray,
        q_preds: dict[float, np.ndarray],
        pairs: list[tuple[float, float]] = [(0.25, 0.75), (0.10, 0.90), (0.05, 0.95)],
    ) -> dict[tuple[float, float], float]:
        """
        Calibrate margins m for each (lo, hi) quantile pair on calibration set.
        """
        n = len(y_true)
        if n < self.min_calibration_size:
            logger.warning(
                f"CQR calibration: only {n} samples (min {self.min_calibration_size}). Margins may be wide."
            )

        self.margins = {}
        for lo, hi in pairs:
            if lo not in q_preds or hi not in q_preds:
                continue
            q_lo = q_preds[lo]
            q_hi = q_preds[hi]
            alpha = round(lo + (1.0 - hi), 4)

            # Nonconformity score: E_i = max(q_lo_i - y_i, y_i - q_hi_i)
            e_scores = np.maximum(q_lo - y_true, y_true - q_hi)
            
            # Finite-sample conformal quantile: ceil((n + 1) * (1 - alpha)) / n
            k = int(np.ceil((n + 1) * (1.0 - alpha)))
            k = max(1, min(k, n))
            # Sort scores and pick k-th smallest
            sorted_e = np.sort(e_scores)
            m = float(sorted_e[k - 1])
            self.margins[(lo, hi)] = m

        self.calibrated = True
        return self.margins

    def predict_intervals(
        self,
        q_preds: dict[float, np.ndarray],
    ) -> dict[tuple[float, float], tuple[np.ndarray, np.ndarray]]:
        """
        Apply calibrated margins to predict calibrated bounds [q_lo - m, q_hi + m].
        """
        if not self.calibrated:
            raise RuntimeError("Call calibrate() before predict_intervals().")

        intervals = {}
        for (lo, hi), m in self.margins.items():
            if lo in q_preds and hi in q_preds:
                lower = q_preds[lo] - m
                upper = q_preds[hi] + m
                intervals[(lo, hi)] = (lower, upper)
        return intervals


class ConformalPredictor:
    """
    Backwards-compatible wrapper implementing split conformal prediction around median or CQR.
    """

    def __init__(self, alpha: float = 0.1, min_calibration_size: int = 30):
        self.alpha = alpha
        self.min_calibration_size = min_calibration_size
        self.q_hat: float | None = None
        self.cqr = CQRCalibrator(min_calibration_size=min_calibration_size)
        self.calibrated: bool = False

    def calibrate(self, y_true: np.ndarray, y_pred: np.ndarray) -> None:
        """Point/median residual calibration."""
        n = len(y_true)
        scores = np.abs(y_true - y_pred)
        level = min(np.ceil((1.0 - self.alpha) * (n + 1)) / n, 1.0)
        self.q_hat = float(np.quantile(scores, level))
        self.calibrated = True

    def predict_interval(self, y_pred: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        if not self.calibrated or self.q_hat is None:
            raise RuntimeError("Call calibrate() before predict_interval().")
        return y_pred - self.q_hat, y_pred + self.q_hat

    def coverage_report(self, y_true: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> dict:
        covered = float(((y_true >= lower) & (y_true <= upper)).mean())
        width = float((upper - lower).mean())
        return {
            "empirical_coverage": covered,
            "target_coverage": 1.0 - self.alpha,
            "mean_interval_width": width,
            "q_hat": self.q_hat,
        }
