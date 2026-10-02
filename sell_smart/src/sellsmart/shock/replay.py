"""
sell_smart.shock.replay
Crisis Replay: replay historical shock events through the decision engine.
Works from shocks present in data + clearly-labelled synthetic stress tests.

NOTE: The 2023-24 onion export-restriction is outside the dataset window.
Replay uses whatever shocks the data contains plus synthetic stress series
(clearly labelled as synthetic per R5).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from sellsmart.shock.radar import detect_shocks
from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ReplayResult:
    event_id: str
    crop: str
    mandi_id: str
    shock_date: str
    z_score: float
    price_at_shock: float
    is_synthetic: bool
    decision_at_shock: dict
    note: str = ""


def replay_shocks(
    gold_df: pd.DataFrame,
    decision_fn,
    config: dict,
    synthetic_shocks: list[dict] | None = None,
) -> list[ReplayResult]:
    """
    Find shocks in gold panel and replay decision engine on each.

    Args:
        gold_df: Gold panel.
        decision_fn: callable(mandi_id, crop, date) -> DecisionResult.
        config: full config dict.
        synthetic_shocks: list of synthetic shock dicts (clearly labelled).

    Returns:
        List of ReplayResult.
    """
    shock_cfg = config.get("shock", {})
    z_thr = shock_cfg.get("z_threshold", 3.0)
    lookback = shock_cfg.get("lookback_window", 30)

    results = []
    for (mandi_id, crop), grp in gold_df.groupby(["mandi_id", "crop"]):
        price_series = grp.set_index("date")["modal_price"].dropna()
        shocks = detect_shocks(price_series, z_threshold=z_thr, lookback_window=lookback)
        shock_rows = shocks[shocks["is_shock"]]

        for dt, row in shock_rows.iterrows():
            try:
                decision = decision_fn(mandi_id, crop, dt)
            except Exception as e:
                decision = {"error": str(e)}

            results.append(ReplayResult(
                event_id=f"{mandi_id}_{crop}_{dt}",
                crop=crop,
                mandi_id=mandi_id,
                shock_date=str(dt),
                z_score=float(row["z_score"]),
                price_at_shock=float(row["price"]),
                is_synthetic=False,
                decision_at_shock=decision if isinstance(decision, dict) else {},
            ))

    # Synthetic shocks
    if synthetic_shocks:
        logger.info(
            f"⚠ SYNTHETIC: Replaying {len(synthetic_shocks)} synthetic stress shocks "
            "(clearly labelled per R5)."
        )
        for shock in synthetic_shocks:
            results.append(ReplayResult(
                event_id=f"synthetic_{shock.get('id', 'unknown')}",
                crop=shock.get("crop", ""),
                mandi_id=shock.get("mandi_id", ""),
                shock_date=shock.get("date", ""),
                z_score=shock.get("z_score", 0),
                price_at_shock=shock.get("price", 0),
                is_synthetic=True,
                decision_at_shock={},
                note="SYNTHETIC STRESS TEST — not a real event",
            ))

    logger.info(
        f"Crisis Replay: {sum(1 for r in results if not r.is_synthetic)} real shocks, "
        f"{sum(1 for r in results if r.is_synthetic)} synthetic shocks."
    )
    return results
