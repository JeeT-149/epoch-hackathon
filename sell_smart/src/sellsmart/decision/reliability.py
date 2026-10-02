"""
sell_smart.decision.reliability
Reliability metadata attached to each decision output.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReliabilityMetadata:
    dq_score: float
    n_obs_last_90d: int
    last_obs_days_ago: int
    calendar_assumed: bool
    is_placeholder: bool
    model_coverage: float | None  # empirical conformal coverage
    backtest_mae: float | None    # from last backtest run

    def to_dict(self) -> dict:
        return {
            "dq_score": self.dq_score,
            "n_obs_last_90d": self.n_obs_last_90d,
            "last_obs_days_ago": self.last_obs_days_ago,
            "calendar_assumed": self.calendar_assumed,
            "is_placeholder": self.is_placeholder,
            "model_coverage": self.model_coverage,
            "backtest_mae": self.backtest_mae,
        }
