"""
sell_smart.economics.storage
Storage cost per quintal per day from crops.yaml.
All costs are PLACEHOLDER (R6).
Units: ₹ per original quintal (R8).
"""
from __future__ import annotations

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


def compute_storage_cost(
    crop: str,
    days_held: int,
    quantity_q: float,
    crops_config: dict,
) -> dict:
    """
    Compute storage cost for holding `quantity_q` quintals for `days_held` days.

    Returns:
        cost_per_q: ₹/quintal (of original quantity)
        total_cost: ₹
        daily_rate: ₹/quintal/day
        is_placeholder: True if source is PLACEHOLDER
    """
    cfg = crops_config.get(crop, {}).get("storage", {})
    daily_rate = cfg.get("cost_per_q_per_day", 1.5)
    source = cfg.get("source", "PLACEHOLDER")

    if source == "PLACEHOLDER":
        logger.warning(
            f"Storage cost for {crop} is PLACEHOLDER. demo_ready=False per R6."
        )

    total_cost = daily_rate * days_held * quantity_q
    cost_per_q = daily_rate * days_held

    return {
        "cost_per_q": round(cost_per_q, 2),
        "total_cost": round(total_cost, 2),
        "daily_rate": daily_rate,
        "days_held": days_held,
        "is_placeholder": source == "PLACEHOLDER",
    }
