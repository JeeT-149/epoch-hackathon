"""
sell_smart.economics.fees
Mandi commission, weighing and other transaction fees from crops.yaml.
All fees are PLACEHOLDER (R6).
Units: ₹ per quintal (R8).
"""
from __future__ import annotations

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


def compute_fees(
    crop: str,
    modal_price: float,
    quantity_q: float,
    crops_config: dict,
) -> dict:
    """
    Compute mandi fees on a sale of `quantity_q` quintals at `modal_price`.

    Returns:
        commission_per_q: ₹/quintal
        weighing_per_q: ₹/quintal
        total_fees_per_q: ₹/quintal
        is_placeholder: True if source is PLACEHOLDER
    """
    cfg = crops_config.get(crop, {}).get("fees", {})
    commission_pct = cfg.get("mandi_commission_pct", 2.0) / 100.0
    weighing = cfg.get("weighing_per_q", 2.0)
    source = cfg.get("source", "PLACEHOLDER")

    if source == "PLACEHOLDER":
        logger.warning(f"Mandi fees for {crop} are PLACEHOLDER. demo_ready=False per R6.")

    commission_per_q = modal_price * commission_pct
    total_fees_per_q = commission_per_q + weighing

    return {
        "commission_per_q": round(commission_per_q, 2),
        "weighing_per_q": round(weighing, 2),
        "total_fees_per_q": round(total_fees_per_q, 2),
        "commission_pct": commission_pct * 100,
        "is_placeholder": source == "PLACEHOLDER",
    }
