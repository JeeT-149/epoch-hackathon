"""
sell_smart.trigger.monitor_plans
Daily monitor command evaluating farmer plans against incoming mandi price series.
Guarantees:
1. Idempotency: Running twice on the same date produces the exact same DB state and zero duplicate outbox events.
2. Next-open-day execution: Fired triggers strictly execute on the NEXT open day's price, preventing same-day lookahead leakage.
3. Full lifecycle: WATCHING → TRIGGERED_SELL → EXECUTED, plus DEADLINE_REACHED and SUSPENDED_SHOCK.
"""
from __future__ import annotations

from datetime import date
from typing import Callable, Dict, List, Optional, Any
import pandas as pd

from sellsmart.trigger.plan_store import PlanStore, SellingPlan
from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


def monitor_daily_plans(
    as_of_date: date,
    plan_store: PlanStore,
    price_panel: pd.DataFrame,
    is_shock_fn: Optional[Callable[[str, str, date], bool]] = None,
    net_return_fn: Optional[Callable[[SellingPlan, float, date], float]] = None,
) -> List[Dict[str, Any]]:
    """
    Evaluate all active plans on as_of_date.

    Args:
        as_of_date: Evaluation date.
        plan_store: SQLite plan store.
        price_panel: Daily gold panel containing columns [date, mandi_id, crop, modal_price, is_open].
        is_shock_fn: Optional callable (mandi_id, crop, as_of_date) -> bool detecting policy/price shock.
        net_return_fn: Optional callable (plan, executed_price, as_of_date) -> float net return.

    Returns:
        List of outbox event dicts newly generated today.
    """
    ts_today = pd.Timestamp(as_of_date)
    # Anti-leakage: slice data up to today only
    today_data = price_panel[price_panel["date"] == ts_today].copy()

    # Build fast lookup map: (mandi_id, crop) -> row
    price_lookup = {}
    if not today_data.empty:
        for _, row in today_data.iterrows():
            m_id = str(row["mandi_id"])
            c_name = str(row["crop"]).lower()
            is_open = bool(row.get("is_open", True))
            price = float(row["modal_price"]) if pd.notna(row.get("modal_price")) else None
            price_lookup[(m_id, c_name)] = {"is_open": is_open, "price": price}

    active_plans = plan_store.get_active_plans()
    newly_emitted_events = []

    for plan in active_plans:
        key = (plan.mandi_id, plan.crop.lower())
        market_info = price_lookup.get(key, {"is_open": False, "price": None})
        current_price = market_info["price"]
        is_open = market_info["is_open"] and (current_price is not None and current_price > 0)

        # ---------------------------------------------------------------------
        # State: WATCHING
        # ---------------------------------------------------------------------
        if plan.status == "WATCHING":
            # 1. Shock Radar check (PRD Section 11)
            if is_shock_fn and is_shock_fn(plan.mandi_id, plan.crop, as_of_date):
                plan.status = "SUSPENDED_SHOCK"
                plan.notes = f"Market shock detected on {as_of_date}. Trigger suspended pending resolution."
                plan_store.save_plan(plan)
                payload = {"reason": "market_shock_detected", "shock_date": str(as_of_date)}
                if plan_store.emit_outbox_event(plan.plan_id, as_of_date, "SUSPENDED_SHOCK", payload):
                    newly_emitted_events.append({"plan_id": plan.plan_id, "event_type": "SUSPENDED_SHOCK", **payload})
                continue

            # 2. Cash Deadline check
            if as_of_date >= plan.cash_deadline_date:
                plan.status = "DEADLINE_REACHED"
                plan.triggered_date = as_of_date
                plan.notes = f"Cash deadline {plan.cash_deadline_date} reached on {as_of_date}. Mandatory liquidation triggered."
                plan_store.save_plan(plan)
                payload = {"reason": "cash_deadline_reached", "deadline_date": str(plan.cash_deadline_date)}
                if plan_store.emit_outbox_event(plan.plan_id, as_of_date, "DEADLINE_REACHED", payload):
                    newly_emitted_events.append({"plan_id": plan.plan_id, "event_type": "DEADLINE_REACHED", **payload})
                continue

            # 3. Market Price Trigger checks (only if open today)
            if is_open and current_price is not None:
                if current_price >= plan.target_price:
                    plan.status = "TRIGGERED_SELL"
                    plan.triggered_date = as_of_date
                    plan.notes = f"Target price ₹{plan.target_price:.0f}/q reached (current: ₹{current_price:.0f}/q). Fired sell trigger for next open day."
                    plan_store.save_plan(plan)
                    payload = {"reason": "target_price_met", "trigger_price": current_price, "target_price": plan.target_price}
                    if plan_store.emit_outbox_event(plan.plan_id, as_of_date, "TRIGGERED_SELL", payload):
                        newly_emitted_events.append({"plan_id": plan.plan_id, "event_type": "TRIGGERED_SELL", **payload})
                elif current_price <= plan.stop_loss_price:
                    plan.status = "TRIGGERED_SELL"
                    plan.triggered_date = as_of_date
                    plan.notes = f"Stop-loss price ₹{plan.stop_loss_price:.0f}/q hit (current: ₹{current_price:.0f}/q). Fired stop-loss trigger for next open day."
                    plan_store.save_plan(plan)
                    payload = {"reason": "stop_loss_hit", "trigger_price": current_price, "stop_loss_price": plan.stop_loss_price}
                    if plan_store.emit_outbox_event(plan.plan_id, as_of_date, "TRIGGERED_SELL", payload):
                        newly_emitted_events.append({"plan_id": plan.plan_id, "event_type": "TRIGGERED_SELL", **payload})

        # ---------------------------------------------------------------------
        # State: TRIGGERED_SELL or DEADLINE_REACHED
        # Next-open-day execution rule: Must execute strictly on a date AFTER triggered_date
        # ---------------------------------------------------------------------
        elif plan.status in ("TRIGGERED_SELL", "DEADLINE_REACHED"):
            # Ensure next open day (as_of_date > triggered_date)
            if plan.triggered_date and as_of_date > plan.triggered_date:
                if is_open and current_price is not None:
                    # Execute trade!
                    plan.status = "EXECUTED"
                    plan.executed_date = as_of_date
                    plan.executed_price = current_price
                    if net_return_fn:
                        plan.net_realized_return_per_q = round(net_return_fn(plan, current_price, as_of_date), 2)
                    else:
                        plan.net_realized_return_per_q = current_price

                    plan.notes = (
                        f"Executed sale on next open market day ({as_of_date}) at ₹{current_price:.0f}/q. "
                        f"Triggered on {plan.triggered_date}."
                    )
                    plan_store.save_plan(plan)
                    payload = {
                        "executed_price": current_price,
                        "net_realized_return_per_q": plan.net_realized_return_per_q,
                        "executed_date": str(as_of_date),
                        "triggered_date": str(plan.triggered_date),
                    }
                    if plan_store.emit_outbox_event(plan.plan_id, as_of_date, "EXECUTED", payload):
                        newly_emitted_events.append({"plan_id": plan.plan_id, "event_type": "EXECUTED", **payload})

    return newly_emitted_events
