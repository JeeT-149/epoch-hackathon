"""
sell_smart.scripts.replay_farmer_plan
Replays one farmer's selling plan end to end against daily market panel prices (Step 5).
Demonstrates:
- Initial plan creation in WATCHING state
- Daily idempotent monitor passes
- State transition to TRIGGERED_SELL when target threshold is hit
- Next-open-day sale execution (anti-leakage rule)
- Transactional outbox event generation
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from sellsmart.trigger.plan_store import PlanStore, SellingPlan
from sellsmart.trigger.monitor_plans import monitor_daily_plans
from sellsmart.common.logging import get_logger

logger = get_logger("replay_farmer_plan")


def run_farmer_plan_replay(gold_panel_path: Path | str, db_path: Path | str) -> dict:
    gold_path = Path(gold_panel_path)
    if not gold_path.exists():
        raise FileNotFoundError(f"Gold panel not found at {gold_path}")

    # Load panel
    df_gold = pd.read_parquet(gold_path).sort_values("date").reset_index(drop=True)
    dewas_soybean = df_gold[
        (df_gold["crop"] == "soybean") & (df_gold["mandi_id"] == "madhy_dewas_dewas")
    ].copy()

    if len(dewas_soybean) < 14:
        raise ValueError("Insufficient history for dewas soybean in gold panel.")

    # Select a 14-day evaluation slice where price experiences natural movement
    sim_slice = dewas_soybean.iloc[50:65].copy()
    start_date = pd.to_datetime(sim_slice["date"].iloc[0]).date()
    initial_price = float(sim_slice["modal_price"].iloc[0])

    # Set plan thresholds relative to initial price
    target_price = round(initial_price * 1.025, 0)      # +2.5% target
    stop_loss_price = round(initial_price * 0.95, 0)    # -5% stop loss
    cash_deadline = start_date + timedelta(days=12)

    plan_store = PlanStore(db_path)

    plan_id = "plan_farmer_ramesh_001"
    initial_plan = SellingPlan(
        plan_id=plan_id,
        farmer_id="farmer_ramesh_dewas",
        crop="soybean",
        mandi_id="madhy_dewas_dewas",
        quantity_q=25.0,
        creation_date=start_date,
        target_price=target_price,
        stop_loss_price=stop_loss_price,
        cash_deadline_date=cash_deadline,
        status="WATCHING",
        notes="Farmer Ramesh looking to sell 25q soybean. Target: +2.5% gain or 12-day deadline.",
    )
    plan_store.save_plan(initial_plan)

    print("=" * 80)
    print(f"  FARMER SELLING PLAN REPLAY: {plan_id}")
    print("=" * 80)
    print(f"Farmer: {initial_plan.farmer_id} | Crop: {initial_plan.crop} | Mandi: {initial_plan.mandi_id}")
    print(f"Quantity: {initial_plan.quantity_q} quintals | Start Date: {start_date}")
    print(f"Baseline Price: ₹{initial_price:.0f}/q | Target: ₹{target_price:.0f}/q | Stop-loss: ₹{stop_loss_price:.0f}/q")
    print(f"Cash Deadline: {cash_deadline}\n")

    history_log = []

    unique_dates = sorted(sim_slice["date"].unique())
    for dt_ts in unique_dates:
        curr_date = pd.to_datetime(dt_ts).date()
        daily_slice = sim_slice[sim_slice["date"] == dt_ts]
        mandi_row = daily_slice.iloc[0]
        curr_price = float(mandi_row["modal_price"])
        is_open = bool(mandi_row.get("is_open", True))

        # Test idempotency on each day by running monitor twice
        events_1 = monitor_daily_plans(curr_date, plan_store, sim_slice)
        events_2 = monitor_daily_plans(curr_date, plan_store, sim_slice)
        assert len(events_2) == 0, f"Idempotency violation on {curr_date}!"

        plan_state = plan_store.get_plan(plan_id)
        open_str = "OPEN" if is_open else "CLOSED"
        day_note = f"Day {curr_date} [{open_str}]: Modal Price = ₹{curr_price:.0f}/q | State = {plan_state.status}"
        print(f" -> {day_note}")

        if events_1:
            for ev in events_1:
                print(f"    📢 OUTBOX EVENT: {ev['event_type']} | Details: {ev}")

        history_log.append({
            "date": str(curr_date),
            "price": curr_price,
            "status": plan_state.status,
            "triggered_date": str(plan_state.triggered_date) if plan_state.triggered_date else None,
            "executed_date": str(plan_state.executed_date) if plan_state.executed_date else None,
        })

        if plan_state.status == "EXECUTED":
            print(f"\n[OK] Plan successfully executed on {plan_state.executed_date} at ₹{plan_state.executed_price:.0f}/q!")
            break

    final_plan = plan_store.get_plan(plan_id)
    all_events = plan_store.get_outbox_events(plan_id)

    print("\n" + "=" * 80)
    print("  REPLAY RECEIPT & FINAL PLAN STATE")
    print("=" * 80)
    print(f"Final Status: {final_plan.status}")
    print(f"Triggered Date: {final_plan.triggered_date}")
    print(f"Executed Date:  {final_plan.executed_date} (Next Open Day Price: ₹{final_plan.executed_price:.0f}/q)")
    print(f"Gross Revenue:  ₹{(final_plan.executed_price or 0.0) * final_plan.quantity_q:,.2f}")
    print(f"Outbox Events Emitted: {len(all_events)}")
    print(f"Plan Notes: {final_plan.notes}\n")

    return {
        "plan_id": plan_id,
        "final_status": final_plan.status,
        "triggered_date": str(final_plan.triggered_date) if final_plan.triggered_date else None,
        "executed_date": str(final_plan.executed_date) if final_plan.executed_date else None,
        "executed_price": final_plan.executed_price,
        "events_count": len(all_events),
        "history": history_log,
    }


if __name__ == "__main__":
    db = Path("sell_smart/artifacts/trigger_plans.db")
    gold = Path("sell_smart/data/gold/gold_panel.parquet")
    run_farmer_plan_replay(gold, db)
