"""
sell_smart.decision.options
Generate selling options: (mandi, selling_day) combinations.
Only generates options on open trading days within cash deadline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

import pandas as pd

from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SellingOption:
    """A candidate mandi × selling day option."""
    mandi_id: str
    sell_date: date
    days_from_now: int
    modal_price_forecast: float
    forecast_lower: float
    forecast_upper: float
    net_return_per_q: float
    economics_breakdown: dict
    is_open_day: bool = True
    calendar_assumed: bool = False
    dq_score: float = 0.0
    is_placeholder: bool = True
    notes: list[str] = field(default_factory=list)


def generate_options(
    crop: str,
    today: date,
    mandis: list[dict],
    forecasts: pd.DataFrame,
    calendar_df: pd.DataFrame,
    economics_fn,
    max_days: int = 14,
    cash_deadline_days: int | None = None,
) -> list[SellingOption]:
    """
    Generate all (mandi, selling_day) options.

    Args:
        crop: crop name.
        today: decision date.
        mandis: list of mandi dicts from mandis.yaml.
        forecasts: DataFrame with pred_q50_h*d columns per mandi/crop.
        calendar_df: trading calendar per (mandi_id, crop, weekday).
        economics_fn: callable(mandi, days_held) -> net_return dict.
        max_days: maximum days to look ahead.
        cash_deadline_days: if set, filter options beyond this.

    Returns:
        List of SellingOption.
    """
    options = []
    effective_max = min(max_days, cash_deadline_days) if cash_deadline_days is not None else max_days

    for mandi in mandis:
        mandi_id = mandi["mandi_id"]
        mandi_crop = mandi.get("crop", "")
        if mandi_crop != crop:
            continue

        dq_score = mandi.get("data_quality_score", 0.0)

        # Get calendar for this mandi/crop
        cal = calendar_df[
            (calendar_df["mandi_id"] == mandi_id) & (calendar_df["crop"] == crop)
        ].set_index("weekday")

        for days_ahead in range(0, effective_max + 1):
            sell_date = today + timedelta(days=days_ahead)
            weekday = sell_date.weekday()

            is_open = True
            cal_assumed = False
            if weekday in cal.index:
                is_open = bool(cal.loc[weekday, "is_open"])
                cal_assumed = bool(cal.loc[weekday, "calendar_assumed"])
            else:
                is_open = weekday < 6  # Mon-Sat default
                cal_assumed = True

            if not is_open:
                continue

            # Get forecast for this horizon
            h = days_ahead if days_ahead > 0 else 1
            q50_col = f"pred_q50_h{h}d"
            q10_col = f"pred_q10_h{h}d"
            q90_col = f"pred_q90_h{h}d"

            fcast_row = forecasts[
                (forecasts["mandi_id"] == mandi_id) &
                (forecasts["crop"] == crop)
            ]

            if fcast_row.empty or q50_col not in fcast_row.columns:
                continue

            modal_forecast = float(fcast_row[q50_col].iloc[-1]) if q50_col in fcast_row.columns else 0.0
            lower = float(fcast_row[q10_col].iloc[-1]) if q10_col in fcast_row.columns else 0.0
            upper = float(fcast_row[q90_col].iloc[-1]) if q90_col in fcast_row.columns else 0.0

            # Net return via economics function
            econ = economics_fn(mandi, days_held=days_ahead, modal_price=modal_forecast)

            options.append(SellingOption(
                mandi_id=mandi_id,
                sell_date=sell_date,
                days_from_now=days_ahead,
                modal_price_forecast=modal_forecast,
                forecast_lower=lower,
                forecast_upper=upper,
                net_return_per_q=econ.get("net_return_per_q", 0.0),
                economics_breakdown=econ,
                is_open_day=is_open,
                calendar_assumed=cal_assumed,
                dq_score=dq_score,
                is_placeholder=econ.get("is_placeholder", True),
                notes=["calendar_assumed"] if cal_assumed else [],
            ))

    return options
