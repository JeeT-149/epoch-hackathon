"""
sell_smart.clean.calendar
Infer trading calendar per mandi from data (not assumed).
Build gold panel: one row per (mandi_id, crop, date) with forward-fill gaps.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)

WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def infer_trading_calendar(
    silver_df: pd.DataFrame,
    open_threshold: float = 0.5,
) -> pd.DataFrame:
    """
    For each (mandi_id, crop, weekday), determine if the mandi is "open"
    by checking whether it reported on >= open_threshold of that weekday's dates.

    Returns DataFrame with columns: [mandi_id, crop, weekday, is_open, calendar_assumed].
    """
    df = silver_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["weekday"] = df["date"].dt.dayofweek  # 0=Mon, 6=Sun

    # Total number of each weekday in the dataset
    date_range = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    weekday_totals = pd.Series(date_range.dayofweek).value_counts().to_dict()

    rows = []
    for (mandi_id, crop), grp in df.groupby(["mandi_id", "crop"]):
        obs_by_weekday = grp["weekday"].value_counts().to_dict()
        for wd in range(7):
            total = weekday_totals.get(wd, 1)
            obs = obs_by_weekday.get(wd, 0)
            frac = obs / total
            is_open = frac >= open_threshold
            assumed = obs < 3  # very few observations — assume default
            rows.append({
                "mandi_id": mandi_id,
                "crop": crop,
                "weekday": wd,
                "weekday_name": WEEKDAY_NAMES[wd],
                "open_fraction": round(frac, 3),
                "is_open": is_open,
                "calendar_assumed": assumed,
            })

    return pd.DataFrame(rows)


def build_gold_panel(
    silver_df: pd.DataFrame,
    selected_mandis: list[str],
    crops: list[str],
    calendar_df: pd.DataFrame,
    max_ffill_days: int = 3,
    crops_config: dict | None = None,
) -> pd.DataFrame:
    """
    Build the gold daily panel: one row per (mandi_id, crop, date).
    - Forward-fill modal_price up to max_ffill_days; add days_since_obs feature.
    - Mark calendar_assumed where applicable.
    - Prefer FAQ grade, then canonical variety from crops_config.

    Returns gold DataFrame.
    """
    df = silver_df.copy()
    df["date"] = pd.to_datetime(df["date"])

    # Filter to selected mandis and crops
    df = df[
        df["mandi_id"].isin(selected_mandis) &
        df["crop"].isin(crops)
    ].copy()

    # Remove rows flagged as suspect_outlier or inconsistent_minmax from features
    def _is_clean(flags):
        if isinstance(flags, list):
            return not any(f in flags for f in ["suspect_outlier", "inconsistent_minmax"])
        return True

    df["is_feature_eligible"] = df["dq_flags"].apply(_is_clean)
    clean = df[df["is_feature_eligible"]].copy()

    # Prefer FAQ grade
    def _preferred_variety(grp):
        if crops_config and grp["crop"].iloc[0] in crops_config:
            priority = crops_config[grp["crop"].iloc[0]].get(
                "variety_priority", []
            ) if crops_config else []
        else:
            priority = []
        # Sort: FAQ first, then by priority list
        grp = grp.copy()
        grp["grade_order"] = grp["grade"].apply(
            lambda g: 0 if str(g).upper().startswith("FAQ") else 1
        )
        return grp.sort_values("grade_order").groupby(
            ["mandi_id", "crop", "date"]
        ).agg(
            modal_price=("modal_price", "median"),
            min_price=("min_price", "median"),
            max_price=("max_price", "median"),
            n_source_rows=("modal_price", "count"),
        ).reset_index()

    # Aggregate to one row per (mandi_id, crop, date)
    gold = (
        clean.groupby(["mandi_id", "crop", "date"])
        .agg(
            modal_price=("modal_price", "median"),
            min_price=("min_price", "median"),
            max_price=("max_price", "median"),
            n_source_rows=("modal_price", "count"),
            state=("state", "first"),
            district=("district", "first"),
        )
        .reset_index()
    )

    # Build full date range per (mandi, crop) and forward-fill
    date_range = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    panels = []
    for (mandi_id, crop), grp in gold.groupby(["mandi_id", "crop"]):
        grp = grp.set_index("date").reindex(date_range)
        grp.index.name = "date"
        grp["mandi_id"] = mandi_id
        grp["crop"] = crop

        # Forward-fill price, track days_since_obs
        grp["days_since_obs"] = grp["modal_price"].isna().cumsum()
        grp["days_since_obs"] -= (
            grp["modal_price"].notna().cumsum().where(grp["modal_price"].notna(), np.nan)
            .ffill()
            .fillna(0)
        )
        grp["modal_price"] = grp["modal_price"].fillna(method="ffill", limit=max_ffill_days)
        grp["min_price"] = grp["min_price"].fillna(method="ffill", limit=max_ffill_days)
        grp["max_price"] = grp["max_price"].fillna(method="ffill", limit=max_ffill_days)

        # Add trading day flag from calendar
        cal_sub = calendar_df[
            (calendar_df["mandi_id"] == mandi_id) & (calendar_df["crop"] == crop)
        ].set_index("weekday")[["is_open", "calendar_assumed"]]
        grp["weekday"] = pd.to_datetime(grp.index).dayofweek
        grp = grp.reset_index()
        grp = grp.merge(cal_sub, on="weekday", how="left")
        grp["is_open"] = grp["is_open"].fillna(False)
        grp["calendar_assumed"] = grp["calendar_assumed"].fillna(True)

        panels.append(grp)

    gold_panel = pd.concat(panels, ignore_index=True)
    gold_panel = gold_panel.sort_values(["mandi_id", "crop", "date"]).reset_index(drop=True)

    logger.info(
        f"Gold panel: {len(gold_panel):,} rows, "
        f"{gold_panel['modal_price'].notna().mean():.1%} non-null modal_price."
    )
    return gold_panel
