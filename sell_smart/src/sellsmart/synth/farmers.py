"""
sell_smart.synth.farmers
Generate synthetic farmer scenarios around mandi clusters.
All output goes to data/synthetic/ with is_synthetic=True (R5).
Synthetic columns are NEVER model features (enforced by leakage_guard).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)

SYNTHETIC_COLS = [
    "farmer_id", "village_lat", "village_lon", "quantity_q",
    "vehicle_type", "cash_deadline_days", "storage_condition", "quality_factor",
    "is_synthetic", "generator", "seed", "config_hash",
]


def generate_farmers(
    mandis: list[dict],
    n_farmers_per_mandi: int = 20,
    config: dict | None = None,
    seed: int = 42,
    config_hash: str = "",
) -> pd.DataFrame:
    """
    Generate synthetic farmer records around each mandi.

    Location: distance U(village_km_min, village_km_max) from mandi, random bearing.
    Quantity: sampled from synth.quantity_choices.
    Cash deadline: sampled from synth.cash_deadline_days_choices with weights.

    Returns:
        DataFrame with synthetic farmer records (is_synthetic=True always).
    """
    rng = np.random.default_rng(seed)
    synth_cfg = (config or {}).get("synth", {})

    km_min = synth_cfg.get("village_km_min", 5)
    km_max = synth_cfg.get("village_km_max", 60)
    qty_choices = synth_cfg.get("quantity_choices", [10, 20, 50, 100])
    deadline_choices = synth_cfg.get("cash_deadline_days_choices", [0, 3, 7, 14, 21])
    deadline_weights = synth_cfg.get("cash_deadline_days_weights", [0.1, 0.2, 0.3, 0.25, 0.15])
    deadline_weights = np.array(deadline_weights, dtype=float)
    deadline_weights /= deadline_weights.sum()

    rows = []
    for i, mandi in enumerate(mandis):
        mandi_lat = mandi.get("lat") or 22.0
        mandi_lon = mandi.get("lon") or 77.0
        crop = mandi.get("crop", "unknown")
        mandi_id = mandi.get("mandi_id", "")

        for j in range(n_farmers_per_mandi):
            farmer_id = f"F{i:03d}_{j:04d}"
            distance = rng.uniform(km_min, km_max)
            bearing = rng.uniform(0, 360)
            bearing_rad = np.radians(bearing)

            # Approximate lat/lon offset
            dlat = (distance * np.cos(bearing_rad)) / 111.0
            dlon = (distance * np.sin(bearing_rad)) / (111.0 * np.cos(np.radians(mandi_lat)))

            quantity = float(rng.choice(qty_choices))
            deadline = int(rng.choice(deadline_choices, p=deadline_weights))

            # Storage condition per crop
            if crop == "soybean":
                condition = rng.choice(["dry", "moist"], p=[0.7, 0.3])
                quality = float(rng.choice([0.95, 0.90, 0.80], p=[0.5, 0.35, 0.15]))
            elif crop == "onion":
                condition = rng.choice(["ambient_dry", "humid"], p=[0.6, 0.4])
                quality = float(rng.choice([1.0, 0.9, 0.75], p=[0.5, 0.3, 0.2]))
            else:
                condition = "ambient"
                quality = float(rng.choice([1.0, 0.9, 0.8], p=[0.5, 0.3, 0.2]))

            rows.append({
                "farmer_id": farmer_id,
                "mandi_id": mandi_id,
                "crop": crop,
                "village_lat": round(mandi_lat + dlat, 5),
                "village_lon": round(mandi_lon + dlon, 5),
                "distance_to_mandi_km": round(distance, 2),
                "quantity_q": quantity,
                "cash_deadline_days": deadline,
                "storage_condition": condition,
                "quality_factor": quality,
                "is_synthetic": True,
                "generator": "farmers_v1",
                "seed": seed,
                "config_hash": config_hash,
            })

    df = pd.DataFrame(rows)
    logger.info(f"Generated {len(df)} synthetic farmer records.")
    return df
