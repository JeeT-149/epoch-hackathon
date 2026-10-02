"""
sell_smart.clean.canonicalize
Converts raw bronze DataFrame into the canonical silver `prices_daily` table.

Silver schema:
    date, state, district, mandi_id, market_raw, crop, commodity_raw,
    variety_raw, grade, min_price, max_price, modal_price, dq_flags,
    source, ingested_at, n_source_rows
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from sellsmart.common.config import load_commodity_map
from sellsmart.common.logging import get_logger

logger = get_logger(__name__)

# Maharashtra district aliases (PRD 4.2(1)) — used only if State column is absent
MH_DISTRICT_ALIASES: dict[str, str] = {
    "ahmednagar": "ahilyanagar",
    "ahilyanagar": "ahilyanagar",
    "aurangabad": "chhatrapati sambhajinagar",  # AMBIGUOUS: also Bihar
    "chhatrapati sambhajinagar": "chhatrapati sambhajinagar",
    "osmanabad": "dharashiv",
    "dharashiv": "dharashiv",
}

# 36 Maharashtra district names (canonical)
MH_DISTRICTS = {
    "ahilyanagar", "akola", "amravati", "aurangabad", "beed", "bhandara",
    "buldhana", "chandrapur", "chhatrapati sambhajinagar", "dharashiv",
    "dhule", "gadchiroli", "gondia", "hingoli", "jalgaon", "jalna",
    "kolhapur", "latur", "mumbai city", "mumbai suburban", "nagpur",
    "nanded", "nandurbar", "nashik", "osmanabad", "palghar", "parbhani",
    "pune", "raigad", "ratnagiri", "sangli", "satara", "sindhudurg",
    "solapur", "thane", "wardha", "washim", "yavatmal",
}


def _make_mandi_id(state: Optional[str], district: str, market: str) -> str:
    def slug(s: str) -> str:
        s = str(s).lower().strip()
        s = re.sub(r"[^a-z0-9]+", "_", s)
        return s.strip("_")[:30]

    state_prefix = slug(state or "xx")[:5]
    return f"{state_prefix}_{slug(district)[:15]}_{slug(market)[:15]}"


def _parse_dates(series: pd.Series, max_fail_rate: float = 0.001) -> pd.Series:
    """Parse dates with explicit format; fail loudly if error rate > threshold."""
    parsed = pd.to_datetime(series, format="%d %b %Y", errors="coerce")
    fail_rate = parsed.isna().mean()
    if fail_rate > max_fail_rate:
        raise ValueError(
            f"Date parsing: {fail_rate:.2%} rows unparseable (threshold {max_fail_rate:.2%}). "
            "Check format of 'price_date' column."
        )
    if fail_rate > 0:
        logger.warning(f"Date parse: {parsed.isna().sum()} rows could not be parsed (will be dropped).")
    return parsed


def _match_crop(commodity: str, commodity_map: dict) -> Optional[str]:
    """Return canonical crop name or None if no match."""
    c = str(commodity).strip()
    for crop_key, cfg in commodity_map.items():
        for pattern in cfg.get("commodity_patterns", []):
            if re.search(pattern, c, re.IGNORECASE):
                return crop_key
    return None


def canonicalize(
    raw_df: pd.DataFrame,
    config: dict,
    commodity_map: Optional[dict] = None,
) -> pd.DataFrame:
    """
    Transform raw bronze DataFrame into canonical silver prices_daily.

    Args:
        raw_df: Bronze DataFrame from any Ingestor.
        config: full config dict (from Config.as_dict()).
        commodity_map: loaded commodity_map.yaml; if None, loaded from disk.

    Returns:
        Silver DataFrame.
    """
    if commodity_map is None:
        commodity_map = load_commodity_map()

    df = raw_df.copy()

    # ── 1. Strip whitespace, normalise strings ────────────────────────────────
    str_cols = ["district_name", "market_name", "commodity", "variety", "grade"]
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()

    # ── 2. Parse dates ────────────────────────────────────────────────────────
    max_fail = config.get("quality", {}).get("max_unparseable_date_rate", 0.001)
    df["date"] = _parse_dates(df["price_date"], max_fail_rate=max_fail)
    df = df.dropna(subset=["date"])
    df["date"] = df["date"].dt.date

    # ── 3. State derivation (column already exists in this dataset) ───────────
    if "state" not in df.columns:
        # Fall back: attempt Maharashtra ID from district name
        logger.warning("No 'state' column found. Attempting Maharashtra detection from districts.")
        df["state"] = None
        dist_lower = df["district_name"].str.lower().str.strip()
        df.loc[dist_lower.isin(MH_DISTRICTS), "state"] = "Maharashtra"
        # Alias mapping
        df["district_name"] = (
            dist_lower.map(MH_DISTRICT_ALIASES).fillna(dist_lower)
            .str.title()
        )
    else:
        df["state"] = df["state"].astype(str).str.strip().str.title()

    # ── 4. District normalisation ─────────────────────────────────────────────
    df["district"] = df["district_name"].str.strip().str.title()

    # ── 5. Mandi ID ───────────────────────────────────────────────────────────
    df["mandi_id"] = df.apply(
        lambda r: _make_mandi_id(r.get("state"), r["district"], r["market_name"]),
        axis=1,
    )
    df["market_raw"] = df["market_name"]

    # ── 6. Crop matching ──────────────────────────────────────────────────────
    df["crop"] = df["commodity"].apply(lambda c: _match_crop(c, commodity_map))
    df["commodity_raw"] = df["commodity"]
    df["variety_raw"] = df["variety"]

    # ── 7. Price columns ──────────────────────────────────────────────────────
    for col, new_col in [
        ("min_price", "min_price"),
        ("max_price", "max_price"),
        ("modal_price", "modal_price"),
    ]:
        df[new_col] = pd.to_numeric(df[col], errors="coerce")

    # ── 8. DQ flags: initialise ───────────────────────────────────────────────
    df["dq_flags"] = [[] for _ in range(len(df))]

    # ── 9. Drop rows with modal_price <= 0 or null ────────────────────────────
    bad_price = df["modal_price"].isna() | (df["modal_price"] <= 0)
    logger.info(f"Dropping {bad_price.sum()} rows with modal_price <= 0 or null.")
    df = df[~bad_price].copy()

    # ── 10. Flag inconsistent min/max/modal ───────────────────────────────────
    incons = ~(
        (df["min_price"] <= df["modal_price"]) &
        (df["modal_price"] <= df["max_price"])
    )
    for idx in df.index[incons]:
        df.at[idx, "dq_flags"] = df.at[idx, "dq_flags"] + ["inconsistent_minmax"]
    logger.info(f"Flagged {incons.sum()} rows with inconsistent min/max/modal.")

    # ── 11. Drop exact duplicates ─────────────────────────────────────────────
    key_cols = ["date", "mandi_id", "crop", "variety_raw", "grade"]
    n_before = len(df)
    df = df.drop_duplicates(subset=key_cols + ["min_price", "max_price", "modal_price"])
    logger.info(f"Dropped {n_before - len(df)} exact duplicate rows.")

    # ── 12. Conflicting duplicates → median ───────────────────────────────────
    dupes_mask = df.duplicated(subset=key_cols, keep=False)
    if dupes_mask.any():
        logger.info(f"Resolving {dupes_mask.sum()} conflicting duplicates via median.")
        agg = (
            df[dupes_mask]
            .groupby(key_cols, as_index=False)
            .agg(
                min_price=("min_price", "median"),
                max_price=("max_price", "median"),
                modal_price=("modal_price", "median"),
            )
        )
        agg["dq_flags"] = [["duplicate_conflict"] for _ in range(len(agg))]
        df = df[~dupes_mask].copy()
        df = pd.concat([df, agg], ignore_index=True)

    # ── 13. Add provenance ────────────────────────────────────────────────────
    if "source" not in df.columns:
        df["source"] = "unknown"
    if "ingested_at" not in df.columns:
        df["ingested_at"] = None

    # ── 14. Select and order final columns ───────────────────────────────────
    silver_cols = [
        "date", "state", "district", "mandi_id", "market_raw",
        "crop", "commodity_raw", "variety_raw", "grade",
        "min_price", "max_price", "modal_price",
        "dq_flags", "source", "ingested_at",
    ]
    df = df[[c for c in silver_cols if c in df.columns]].copy()
    df = df.sort_values(["date", "mandi_id", "crop"]).reset_index(drop=True)

    logger.info(
        f"Canonicalization complete. {len(df):,} rows. "
        f"Crops: {df['crop'].value_counts().to_dict()}"
    )
    return df
