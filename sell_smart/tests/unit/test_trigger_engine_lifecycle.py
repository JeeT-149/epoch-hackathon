"""
tests/unit/test_trigger_engine_lifecycle.py
Verifies Step 5 Trigger Engine requirements:
1. SQLite plan store persistence.
2. Idempotent monitor command (running twice on the same date gives the same result).
3. Transactional events outbox with deduplication.
4. Full lifecycle: WATCHING → TRIGGERED_SELL → EXECUTED.
5. Fired trigger sells on the NEXT open day's price, not the same day's (anti-leakage rule).
6. Cash deadline reached handling (DEADLINE_REACHED → EXECUTED).
7. Market shock handling (SUSPENDED_SHOCK).
8. End-to-end replay of a farmer's plan over a multi-day timeline.
"""
from datetime import date, timedelta
import pandas as pd
import pytest

from sellsmart.trigger.plan_store import PlanStore, SellingPlan
from sellsmart.trigger.monitor_plans import monitor_daily_plans


@pytest.fixture
def plan_store(tmp_path):
    db_file = tmp_path / "test_plans.db"
    store = PlanStore(db_file)
    yield store
    store.close()


def _make_panel(dates, mandi_id="mp_dewas_dewas", crop="soybean", prices=None, is_open=None):
    if prices is None:
        prices = [4500.0] * len(dates)
    if is_open is None:
        is_open = [True] * len(dates)
    return pd.DataFrame({
        "date": [pd.Timestamp(d) for d in dates],
        "mandi_id": mandi_id,
        "crop": crop,
        "modal_price": prices,
        "is_open": is_open,
    })


class TestTriggerEngineLifecycle:

    def test_full_lifecycle_watching_to_triggered_to_executed_next_day(self, plan_store):
        """
        Timeline:
        Day 0 (2025-04-01): Plan created in WATCHING. Market price = 4500. Target = 4800.
        Day 1 (2025-04-02): Price = 4600. Still WATCHING.
        Day 2 (2025-04-03): Price = 4850. Target reached! Fired trigger -> TRIGGERED_SELL. NOT executed today.
        Day 3 (2025-04-04): Market is open, price = 4820. Executes at next open day price 4820 -> EXECUTED!
        """
        d0 = date(2025, 4, 1)
        d1 = date(2025, 4, 2)
        d2 = date(2025, 4, 3)
        d3 = date(2025, 4, 4)

        plan = SellingPlan(
            plan_id="plan_001",
            farmer_id="farmer_ramesh",
            crop="soybean",
            mandi_id="mp_dewas_dewas",
            quantity_q=20.0,
            creation_date=d0,
            target_price=4800.0,
            stop_loss_price=4200.0,
            cash_deadline_date=date(2025, 4, 15),
            status="WATCHING",
        )
        plan_store.save_plan(plan)

        # Day 1: Price 4600
        panel_d1 = _make_panel([d1], prices=[4600.0])
        ev1 = monitor_daily_plans(d1, plan_store, panel_d1)
        assert len(ev1) == 0
        p = plan_store.get_plan("plan_001")
        assert p.status == "WATCHING"
        assert p.triggered_date is None
        assert p.executed_date is None

        # Day 2: Price 4850 (target hit!)
        panel_d2 = _make_panel([d2], prices=[4850.0])
        ev2 = monitor_daily_plans(d2, plan_store, panel_d2)
        assert len(ev2) == 1
        assert ev2[0]["event_type"] == "TRIGGERED_SELL"

        p = plan_store.get_plan("plan_001")
        assert p.status == "TRIGGERED_SELL"
        assert p.triggered_date == d2
        # Crucial: Must NOT be executed on Day 2!
        assert p.executed_date is None
        assert p.executed_price is None

        # Day 3: Next open day price 4820
        panel_d3 = _make_panel([d3], prices=[4820.0])
        ev3 = monitor_daily_plans(d3, plan_store, panel_d3)
        assert len(ev3) == 1
        assert ev3[0]["event_type"] == "EXECUTED"

        p = plan_store.get_plan("plan_001")
        assert p.status == "EXECUTED"
        assert p.triggered_date == d2
        # Verified: Executed on NEXT day with NEXT day's price!
        assert p.executed_date == d3
        assert p.executed_price == 4820.0
        assert p.net_realized_return_per_q == 4820.0

    def test_idempotent_monitor_command(self, plan_store):
        """Running monitor twice on the exact same date produces identical state and zero duplicate events."""
        d = date(2025, 4, 3)
        plan = SellingPlan(
            plan_id="plan_idempotent",
            farmer_id="farmer_suresh",
            crop="soybean",
            mandi_id="mp_dewas_dewas",
            quantity_q=15.0,
            creation_date=date(2025, 4, 1),
            target_price=4800.0,
            stop_loss_price=4200.0,
            cash_deadline_date=date(2025, 4, 15),
            status="WATCHING",
        )
        plan_store.save_plan(plan)
        panel = _make_panel([d], prices=[4900.0])

        # Run 1
        ev_first = monitor_daily_plans(d, plan_store, panel)
        assert len(ev_first) == 1
        p_first = plan_store.get_plan("plan_idempotent")
        events_first = plan_store.get_outbox_events("plan_idempotent")

        # Run 2 (exact same date)
        ev_second = monitor_daily_plans(d, plan_store, panel)
        assert len(ev_second) == 0  # no new events!
        p_second = plan_store.get_plan("plan_idempotent")
        events_second = plan_store.get_outbox_events("plan_idempotent")

        # Database state is strictly identical
        assert p_first.status == p_second.status == "TRIGGERED_SELL"
        assert p_first.triggered_date == p_second.triggered_date == d
        assert len(events_first) == len(events_second) == 1

    def test_cash_deadline_reached_lifecycle(self, plan_store):
        """When cash deadline arrives without price target, mandatory liquidation triggers and executes next day."""
        d_create = date(2025, 4, 1)
        d_deadline = date(2025, 4, 5)
        d_next = date(2025, 4, 6)

        plan = SellingPlan(
            plan_id="plan_deadline",
            farmer_id="farmer_anita",
            crop="soybean",
            mandi_id="mp_dewas_dewas",
            quantity_q=10.0,
            creation_date=d_create,
            target_price=5000.0,
            stop_loss_price=4000.0,
            cash_deadline_date=d_deadline,
            status="WATCHING",
        )
        plan_store.save_plan(plan)

        # On deadline date, price is flat 4500 (target not met)
        panel_dead = _make_panel([d_deadline], prices=[4500.0])
        ev_dead = monitor_daily_plans(d_deadline, plan_store, panel_dead)
        assert len(ev_dead) == 1
        assert ev_dead[0]["event_type"] == "DEADLINE_REACHED"

        p = plan_store.get_plan("plan_deadline")
        assert p.status == "DEADLINE_REACHED"
        assert p.triggered_date == d_deadline
        assert p.executed_date is None

        # Next day execution
        panel_next = _make_panel([d_next], prices=[4480.0])
        ev_next = monitor_daily_plans(d_next, plan_store, panel_next)
        assert len(ev_next) == 1
        assert ev_next[0]["event_type"] == "EXECUTED"

        p = plan_store.get_plan("plan_deadline")
        assert p.status == "EXECUTED"
        assert p.executed_date == d_next
        assert p.executed_price == 4480.0

    def test_suspended_shock_lifecycle(self, plan_store):
        """When market shock radar detects shock, plan suspends into SUSPENDED_SHOCK."""
        d = date(2025, 4, 3)
        plan = SellingPlan(
            plan_id="plan_shock",
            farmer_id="farmer_vikram",
            crop="onion",
            mandi_id="mahar_nashik_lasalgaon",
            quantity_q=25.0,
            creation_date=date(2025, 4, 1),
            target_price=2800.0,
            stop_loss_price=1800.0,
            cash_deadline_date=date(2025, 4, 20),
            status="WATCHING",
        )
        plan_store.save_plan(plan)

        def mock_shock_radar(mandi, crop, dt):
            return mandi == "mahar_nashik_lasalgaon" and dt == d

        panel = _make_panel([d], mandi_id="mahar_nashik_lasalgaon", crop="onion", prices=[3200.0])
        ev = monitor_daily_plans(d, plan_store, panel, is_shock_fn=mock_shock_radar)
        assert len(ev) == 1
        assert ev[0]["event_type"] == "SUSPENDED_SHOCK"

        p = plan_store.get_plan("plan_shock")
        assert p.status == "SUSPENDED_SHOCK"
        assert "shock" in p.notes.lower()

    def test_next_day_closed_market_waits_for_next_open_day(self, plan_store):
        """If day t+1 is closed (Sunday/holiday), execution waits for first open day."""
        d_trig = date(2025, 4, 4)
        d_closed = date(2025, 4, 5)
        d_open = date(2025, 4, 6)

        plan = SellingPlan(
            plan_id="plan_holiday",
            farmer_id="farmer_kavita",
            crop="soybean",
            mandi_id="mp_dewas_dewas",
            quantity_q=20.0,
            creation_date=date(2025, 4, 1),
            target_price=4700.0,
            stop_loss_price=4100.0,
            cash_deadline_date=date(2025, 4, 20),
            status="TRIGGERED_SELL",
            triggered_date=d_trig,
        )
        plan_store.save_plan(plan)

        # Day 5 is closed
        panel_closed = _make_panel([d_closed], prices=[4750.0], is_open=[False])
        ev_closed = monitor_daily_plans(d_closed, plan_store, panel_closed)
        assert len(ev_closed) == 0
        p = plan_store.get_plan("plan_holiday")
        assert p.status == "TRIGGERED_SELL"
        assert p.executed_date is None

        # Day 6 is open
        panel_open = _make_panel([d_open], prices=[4720.0], is_open=[True])
        ev_open = monitor_daily_plans(d_open, plan_store, panel_open)
        assert len(ev_open) == 1
        assert ev_open[0]["event_type"] == "EXECUTED"
        p = plan_store.get_plan("plan_holiday")
        assert p.status == "EXECUTED"
        assert p.executed_date == d_open
        assert p.executed_price == 4720.0
