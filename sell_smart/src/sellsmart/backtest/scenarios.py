"""
sell_smart.backtest.scenarios
Generate backtest scenarios from gold panel + synthetic farmers.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from sellsmart.synth.farmers import generate_farmers
from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


def build_scenarios(
    gold_df: pd.DataFrame,
    mandis: list[dict],
    config: dict,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Build backtest scenarios by joining gold panel dates with synthetic farmer records.
    Excludes outcomes beyond the data window (R rule: no imputation of missing outcomes).

    Returns:
        DataFrame with [date, mandi_id, crop, farmer_id, ...farmer_attrs,
                        modal_price, target_price_*d, is_synthetic].
    """
    n_scenarios = config.get("backtest", {}).get("n_scenarios", 500)
    n_farmers = max(1, n_scenarios // max(len(mandis), 1))

    farmer_df = generate_farmers(
        mandis=mandis,
        n_farmers_per_mandi=n_farmers,
        config=config,
        seed=seed,
        config_hash=config.get("_hash", ""),
    )

    # Filter gold panel to open trading days with non-null price
    avail = gold_df[gold_df["modal_price"].notna() & gold_df["is_open"]].copy()
    avail = avail.sort_values(["mandi_id", "crop", "date"]).reset_index(drop=True)

    # Merge: each scenario picks a (mandi, crop, date) from the gold panel
    rng = np.random.default_rng(seed)
    rows = []
    for _, farmer in farmer_df.iterrows():
        mandi_id = farmer["mandi_id"]
        crop = farmer["crop"]
        panel_sub = avail[(avail["mandi_id"] == mandi_id) & (avail["crop"] == crop)]
        if panel_sub.empty:
            continue
        chosen = panel_sub.sample(1, random_state=int(rng.integers(1e6))).iloc[0]
        row = {**farmer.to_dict(), **chosen.to_dict()}
        rows.append(row)

    scenarios = pd.DataFrame(rows)
    logger.info(f"Built {len(scenarios)} backtest scenarios.")
    return scenarios
