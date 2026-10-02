"""
sell_smart.synth.offers
Generate synthetic trader offer proxies.
Headline backtest results use NO-OFFER baseline (sell at nearest mandi today).
Offer-based results are reported per delta regime.
NOT real offers (R5, R6).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


def generate_trader_offers(
    gold_df: pd.DataFrame,
    config: dict,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate synthetic trader offers as nearest_mandi_modal(t0) × (1 - delta).
    delta sampled from mixture distribution in synth.offer_discount.

    NOTE: Headline backtest uses no-offer baseline. These are labelled synthetic.
    Returns DataFrame with [date, mandi_id, crop, modal_price, trader_offer_proxy,
                            delta, is_synthetic, ...].
    """
    rng = np.random.default_rng(seed)
    cfg = config.get("synth", {}).get("offer_discount", {})
    components = cfg.get("components", [
        {"delta": 0.00, "weight": 0.20},
        {"mean": 0.05, "std": 0.02, "weight": 0.50},
        {"mean": 0.12, "std": 0.04, "weight": 0.30},
    ])

    weights = np.array([c["weight"] for c in components], dtype=float)
    weights /= weights.sum()

    df = gold_df[["date", "mandi_id", "crop", "modal_price"]].dropna().copy()

    deltas = []
    for _ in range(len(df)):
        comp_idx = rng.choice(len(components), p=weights)
        comp = components[comp_idx]
        if "delta" in comp:
            delta = comp["delta"]
        else:
            delta = float(rng.normal(comp.get("mean", 0.05), comp.get("std", 0.02)))
        deltas.append(max(0, min(0.5, delta)))  # clip to [0, 0.5]

    df["delta"] = deltas
    df["trader_offer_proxy"] = df["modal_price"] * (1 - df["delta"])
    df["is_synthetic"] = True
    df["generator"] = "offers_v1"
    df["seed"] = seed
    logger.info(
        f"Generated {len(df)} synthetic trader offers. "
        "NOTE: Not real offers. Headline results use no-offer baseline."
    )
    return df
