"""
sell_smart.economics.spoilage
Crop-specific spoilage curves from crops.yaml config.
All rates are PLACEHOLDER until verified from field data (R6).
"""
from __future__ import annotations

import math
from typing import Literal

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)

SpoilageCurve = Literal["exponential", "linear_then_step", "moisture_threshold"]


def compute_spoilage_fraction(
    crop: str,
    days_held: int,
    storage_condition: str = "ambient",
    quality_factor: float = 1.0,
    crops_config: dict | None = None,
) -> float:
    """
    Compute fraction of quantity LOST to spoilage after `days_held` days.
    Returns a value in [0, 1]. 0 = no loss, 1 = all lost.

    Args:
        crop: 'soybean', 'onion', or 'tomato'.
        days_held: number of days in storage.
        storage_condition: 'ambient', 'dry', 'humid', etc.
        quality_factor: 1.0 = good quality; < 1.0 increases spoilage.
        crops_config: loaded crops.yaml crops section.

    Returns:
        Spoilage fraction [0, 1].
    """
    if crops_config is None:
        from sellsmart.common.config import load_crops_config
        crops_config = load_crops_config()

    if crop not in crops_config:
        logger.warning(f"No spoilage config for crop '{crop}'. Returning 0 spoilage.")
        return 0.0

    cfg = crops_config[crop]["spoilage"]
    source = cfg.get("source", "PLACEHOLDER")
    if source == "PLACEHOLDER":
        logger.warning(
            f"Spoilage parameters for {crop} are PLACEHOLDER (unverified). "
            "demo_ready=False enforced per R6."
        )

    curve = cfg.get("curve", "exponential")

    # Get condition-specific rate
    conditions = cfg.get("conditions", {})
    cond_cfg = conditions.get(storage_condition, conditions.get("ambient", {}))
    daily_rate_pct = cond_cfg.get("daily_rate_pct", cfg.get("daily_rate_pct", 0.5))
    daily_rate = daily_rate_pct / 100.0

    # Quality factor adjustment (worse quality = higher spoilage)
    daily_rate = daily_rate * (2.0 - quality_factor)  # quality_factor=1→no change, 0.5→2x

    if curve == "exponential":
        fraction_remaining = math.exp(-daily_rate * days_held)
        return max(0.0, min(1.0, 1.0 - fraction_remaining))

    elif curve == "linear_then_step":
        accel_day = cfg.get("rot_acceleration_day", 45)
        accel_factor = cfg.get("rot_acceleration_factor", 2.5)
        if days_held <= accel_day:
            return min(1.0, daily_rate * days_held)
        else:
            base = daily_rate * accel_day
            extra = daily_rate * accel_factor * (days_held - accel_day)
            return min(1.0, base + extra)

    elif curve == "moisture_threshold":
        # For soybean: minimal loss unless moisture exceeds threshold
        # quality_factor proxies moisture; below 0.8 = moist
        if quality_factor < 0.8:
            mult = cfg.get("above_threshold_rate_multiplier", 5.0)
            return min(1.0, daily_rate * mult * days_held)
        return min(1.0, daily_rate * days_held)

    else:
        logger.warning(f"Unknown spoilage curve '{curve}'. Using linear fallback.")
        return min(1.0, daily_rate * days_held)
