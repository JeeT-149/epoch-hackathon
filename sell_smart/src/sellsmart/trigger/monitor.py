"""
sell_smart.trigger.monitor
Daily monitoring loop: runs trigger checks, updates state machines, emits events.
"""
from __future__ import annotations

from datetime import date
from typing import Callable

import pandas as pd

from sellsmart.trigger.compute import compute_trigger_signals
from sellsmart.trigger.state import TriggerState, TriggerStateRecord
from sellsmart.trigger.events import TriggerEvent
from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


def run_daily_check(
    price_data: pd.DataFrame,
    state_records: dict[tuple, TriggerStateRecord],
    today: date,
    config: dict,
) -> list[TriggerEvent]:
    """
    Run daily trigger monitoring for all (mandi, crop) pairs.

    Args:
        price_data: Gold panel slice up to `today` (no future data — R2).
        state_records: dict mapping (mandi_id, crop) → TriggerStateRecord.
        today: current date.
        config: full config dict.

    Returns:
        List of TriggerEvent generated today.
    """
    trigger_cfg = config.get("trigger", {})
    drop_threshold = trigger_cfg.get("price_drop_pct", 0.10)
    rise_threshold = trigger_cfg.get("price_rise_pct", 0.10)
    timeout_days = trigger_cfg.get("state_timeout_days", 30)

    # Ensure no future data (R2)
    data = price_data[price_data["date"] <= pd.Timestamp(today)].copy()
    events = []

    for (mandi_id, crop), grp in data.groupby(["mandi_id", "crop"]):
        grp = grp.sort_values("date")
        price_series = grp.set_index("date")["modal_price"]

        signals = compute_trigger_signals(
            price_series,
            drop_threshold=drop_threshold,
            rise_threshold=rise_threshold,
        )

        key = (mandi_id, crop)
        if key not in state_records:
            state_records[key] = TriggerStateRecord(
                mandi_id=mandi_id,
                crop=crop,
                timeout_days=timeout_days,
                entry_date=today,
            )
        record = state_records[key]

        # Check timeout
        record.check_timeout(today)

        today_row = signals[signals.index == str(today)]
        if today_row.empty:
            continue

        row = today_row.iloc[0]
        current_price = float(row["price"]) if pd.notna(row["price"]) else None
        if current_price is None:
            continue

        ref_price = float(row["reference_price"]) if pd.notna(row["reference_price"]) else current_price
        pct = float(row["pct_change"]) if pd.notna(row["pct_change"]) else 0.0

        if row["trigger_drop"] and record.state == TriggerState.WATCHING:
            record.transition(TriggerState.TRIGGERED_SELL, today, f"price_drop_{pct:.1%}")
            events.append(TriggerEvent(
                event_type="price_drop",
                mandi_id=mandi_id,
                crop=crop,
                event_date=today,
                price=current_price,
                reference_price=ref_price,
                pct_change=pct,
                message=f"Price dropped {abs(pct):.1%}. Consider selling.",
            ))

        elif row["trigger_rise"] and record.state in (TriggerState.WATCHING, TriggerState.TRIGGERED_WAIT):
            record.transition(TriggerState.TRIGGERED_SELL, today, f"price_rise_{pct:.1%}")
            events.append(TriggerEvent(
                event_type="price_rise",
                mandi_id=mandi_id,
                crop=crop,
                event_date=today,
                price=current_price,
                reference_price=ref_price,
                pct_change=pct,
                message=f"Price rose {pct:.1%} above reference. Sell signal.",
            ))

    logger.info(f"Daily check for {today}: {len(events)} trigger events generated.")
    return events
