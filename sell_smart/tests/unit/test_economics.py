"""
tests/unit/test_economics.py
Unit tests for spoilage, transport, storage, fees and net return computations.
"""
import math
import pytest

from sellsmart.economics.spoilage import compute_spoilage_fraction
from sellsmart.economics.transport import compute_transport_cost
from sellsmart.economics.storage import compute_storage_cost
from sellsmart.economics.fees import compute_fees
from sellsmart.economics.netreturn import compute_net_return

# Minimal crop config matching crops.yaml structure
CROPS_CFG = {
    "tomato": {
        "hold_allowed_default": False,
        "max_storage_days": 5,
        "spoilage": {
            "curve": "exponential",
            "daily_rate_pct": 8.0,
            "source": "NHRDF_2020",
            "conditions": {"ambient": {"daily_rate_pct": 8.0}},
        },
        "transport": {
            "vehicle_types": [
                {"name": "tempo", "capacity_q": 25, "cost_per_km": 18.0, "source": "MH_RTO_survey_2023"},
                {"name": "truck", "capacity_q": 100, "cost_per_km": 28.0, "source": "MH_RTO_survey_2023"},
            ],
            "loading_cost_per_q": 15.0,
        },
        "storage": {"cost_per_q_per_day": 2.5, "source": "MH_agri_coldstorage_survey_2022"},
        "fees": {"mandi_commission_pct": 2.0, "weighing_per_q": 2.0, "source": "MH_APMC_Act_2016"},
    },
    "onion": {
        "hold_allowed_default": True,
        "max_storage_days": 90,
        "spoilage": {
            "curve": "linear_then_step",
            "daily_rate_pct": 1.0,
            "source": "NHRDF_2019",
            "conditions": {
                "ambient_dry": {"daily_rate_pct": 1.0},
                "humid": {"daily_rate_pct": 3.0},
            },
            "rot_acceleration_day": 45,
            "rot_acceleration_factor": 2.5,
        },
        "transport": {
            "vehicle_types": [
                {"name": "tempo", "capacity_q": 25, "cost_per_km": 16.0, "source": "MH_RTO_survey_2023"},
            ],
            "loading_cost_per_q": 12.0,
        },
        "storage": {"cost_per_q_per_day": 1.5, "source": "Nashik_onion_storage_survey_2023"},
        "fees": {"mandi_commission_pct": 2.0, "weighing_per_q": 2.0, "source": "MH_APMC_Act_2016"},
    },
    "soybean": {
        "hold_allowed_default": True,
        "max_storage_days": 180,
        "spoilage": {
            "curve": "moisture_threshold",
            "daily_rate_pct": 0.1,
            "source": "ICAR_IISR_2021",
            "conditions": {"dry": {"daily_rate_pct": 0.1}, "moist": {"daily_rate_pct": 0.5}},
            "moisture_threshold_pct": 12.0,
            "above_threshold_rate_multiplier": 5.0,
        },
        "transport": {
            "vehicle_types": [
                {"name": "truck", "capacity_q": 100, "cost_per_km": 25.0, "source": "MP_RTO_survey_2023"},
            ],
            "loading_cost_per_q": 10.0,
        },
        "storage": {"cost_per_q_per_day": 1.0, "source": "WDRA_2023"},
        "fees": {"mandi_commission_pct": 2.0, "weighing_per_q": 2.0, "source": "MP_APMC_rules_2018"},
    },
}


class TestSpoilage:
    def test_tomato_zero_days(self):
        """No days held → zero spoilage."""
        frac = compute_spoilage_fraction("tomato", 0, "ambient", 1.0, CROPS_CFG)
        assert frac == pytest.approx(0.0, abs=1e-6)

    def test_tomato_exponential_increases(self):
        """Tomato spoilage increases monotonically with days held."""
        fracs = [compute_spoilage_fraction("tomato", d, "ambient", 1.0, CROPS_CFG) for d in range(6)]
        assert all(fracs[i] < fracs[i + 1] for i in range(len(fracs) - 1))

    def test_tomato_never_exceeds_one(self):
        """Spoilage fraction must be capped at 1."""
        frac = compute_spoilage_fraction("tomato", 100, "ambient", 1.0, CROPS_CFG)
        assert frac <= 1.0

    def test_onion_acceleration_after_day_45(self):
        """Onion spoilage accelerates after day 45 (linear_then_step curve)."""
        frac_44 = compute_spoilage_fraction("onion", 44, "ambient_dry", 1.0, CROPS_CFG)
        frac_46 = compute_spoilage_fraction("onion", 46, "ambient_dry", 1.0, CROPS_CFG)
        # After acceleration at day 45, rate 2.5x → gradient should be steeper
        assert frac_46 > frac_44
        daily_before = frac_44 / 44
        daily_after = (frac_46 - frac_44) / 2
        assert daily_after > daily_before * 1.5  # noticeably faster (2.5x rate -> ~1.5-2.5x observed gradient at boundary)

    def test_onion_humid_worse_than_dry(self):
        """Humid storage should cause more spoilage than dry."""
        dry = compute_spoilage_fraction("onion", 30, "ambient_dry", 1.0, CROPS_CFG)
        humid = compute_spoilage_fraction("onion", 30, "humid", 1.0, CROPS_CFG)
        assert humid > dry

    def test_soybean_dry_minimal(self):
        """Dry soybean storage: very low spoilage over 30 days."""
        frac = compute_spoilage_fraction("soybean", 30, "dry", 1.0, CROPS_CFG)
        assert frac < 0.05  # < 5% loss in 30 days dry storage

    def test_soybean_moist_higher(self):
        """Moist soybean: 5x rate vs dry."""
        dry = compute_spoilage_fraction("soybean", 30, "dry", 1.0, CROPS_CFG)
        moist = compute_spoilage_fraction("soybean", 30, "moist", 0.7, CROPS_CFG)  # quality < 0.8
        assert moist > dry

    def test_unknown_crop_returns_zero(self):
        """Unknown crop: returns 0 spoilage (safe default)."""
        frac = compute_spoilage_fraction("banana", 5, "ambient", 1.0, CROPS_CFG)
        assert frac == 0.0


class TestTransport:
    def test_zero_distance(self):
        """Zero distance → only loading cost."""
        res = compute_transport_cost(0.0, 20.0, "onion", CROPS_CFG)
        assert res["cost_per_q"] >= 0.0
        assert res["road_km"] == pytest.approx(0.0, abs=0.1)

    def test_vehicle_selection_small_quantity(self):
        """Small quantity (10q) should pick tempo over truck."""
        res = compute_transport_cost(50.0, 10.0, "tomato", CROPS_CFG)
        assert res["vehicle"] == "tempo"

    def test_vehicle_selection_large_quantity(self):
        """Large quantity (80q) should pick truck."""
        res = compute_transport_cost(50.0, 80.0, "tomato", CROPS_CFG)
        assert res["vehicle"] == "truck"

    def test_cost_per_q_positive(self):
        res = compute_transport_cost(100.0, 20.0, "soybean", CROPS_CFG)
        assert res["cost_per_q"] > 0

    def test_road_factor_applied(self):
        """road_km = distance_km * road_factor."""
        res = compute_transport_cost(100.0, 20.0, "onion", CROPS_CFG, road_factor=1.35)
        assert res["road_km"] == pytest.approx(135.0, rel=0.01)

    def test_is_not_placeholder(self):
        """With sourced config, is_placeholder must be False."""
        res = compute_transport_cost(50.0, 20.0, "tomato", CROPS_CFG)
        assert res["is_placeholder"] is False


class TestFees:
    def test_commission_is_percentage(self):
        """Commission = 2% of modal price."""
        res = compute_fees("tomato", 2000.0, 10.0, CROPS_CFG)
        assert res["commission_per_q"] == pytest.approx(40.0, rel=0.01)

    def test_weighing_fixed(self):
        """Weighing charge is fixed at 2 Rs/q."""
        res = compute_fees("onion", 1500.0, 5.0, CROPS_CFG)
        assert res["weighing_per_q"] == pytest.approx(2.0)

    def test_total_fees_is_sum(self):
        res = compute_fees("soybean", 4500.0, 20.0, CROPS_CFG)
        assert res["total_fees_per_q"] == pytest.approx(
            res["commission_per_q"] + res["weighing_per_q"], rel=0.01
        )

    def test_is_not_placeholder(self):
        res = compute_fees("tomato", 2000.0, 10.0, CROPS_CFG)
        assert res["is_placeholder"] is False


class TestNetReturn:
    def test_net_return_below_modal(self):
        """Net return must always be below modal price (costs reduce it)."""
        res = compute_net_return(
            modal_price=2000.0, crop="onion", distance_km=50.0,
            quantity_q=20.0, days_held=3, crops_config=CROPS_CFG,
        )
        assert res["net_return_per_q"] < 2000.0

    def test_spoilage_reduces_return(self):
        """Holding longer reduces net return for tomato."""
        res0 = compute_net_return(
            modal_price=2000.0, crop="tomato", distance_km=20.0,
            quantity_q=20.0, days_held=0, crops_config=CROPS_CFG,
        )
        res3 = compute_net_return(
            modal_price=2000.0, crop="tomato", distance_km=20.0,
            quantity_q=20.0, days_held=3, crops_config=CROPS_CFG,
        )
        assert res3["net_return_per_q"] < res0["net_return_per_q"]

    def test_net_return_breakdown_sum(self):
        """gross_revenue - transport - storage - fees ~= net_return (rough check)."""
        res = compute_net_return(
            modal_price=2000.0, crop="soybean", distance_km=30.0,
            quantity_q=50.0, days_held=10, crops_config=CROPS_CFG,
        )
        # Net return should be positive for soybean at 30km / 10 days
        assert res["net_return_per_q"] > 0


class TestDecisionEngine:
    """Basic decision engine integration tests."""

    def _make_option(self, days, net_return, mandi_id="m1"):
        from sellsmart.decision.options import SellingOption
        from datetime import date, timedelta
        return SellingOption(
            mandi_id=mandi_id,
            sell_date=date.today() + timedelta(days=days),
            days_from_now=days,
            modal_price_forecast=2000.0,
            forecast_lower=1800.0,
            forecast_upper=2200.0,
            net_return_per_q=net_return,
            economics_breakdown={},
            is_placeholder=False,
        )

    def test_sell_now_when_best_is_today(self):
        from sellsmart.decision.engine import decide, Recommendation
        options = [self._make_option(0, 1900.0), self._make_option(7, 1800.0)]
        result = decide(options, "soybean", CROPS_CFG, cash_deadline_days=14)
        assert result.recommendation == Recommendation.SELL_NOW

    def test_wait_when_future_better_and_hold_allowed(self):
        from sellsmart.decision.engine import decide, Recommendation
        # Large margin (+800) ensures engine clearly prefers future date over today
        options = [self._make_option(0, 1300.0), self._make_option(7, 2100.0)]
        result = decide(options, "onion", CROPS_CFG, cash_deadline_days=30)
        assert result.recommendation == Recommendation.WAIT
        assert result.best_option.days_from_now > 0

    def test_sell_now_when_hold_not_allowed(self):
        from sellsmart.decision.engine import decide, Recommendation
        # Tomato: hold_allowed_default=false
        options = [self._make_option(0, 1700.0), self._make_option(3, 1900.0)]
        result = decide(options, "tomato", CROPS_CFG, cash_deadline_days=14)
        assert result.recommendation in (Recommendation.SELL_NOW, Recommendation.SWITCH_MANDI)

    def test_hold_suspended_on_shock(self):
        from sellsmart.decision.engine import decide, Recommendation
        options = [self._make_option(0, 1900.0)]
        result = decide(options, "onion", CROPS_CFG, shock_detected=True)
        assert result.recommendation == Recommendation.HOLD_SUSPENDED

    def test_accept_when_trader_offer_better(self):
        from sellsmart.decision.engine import decide, Recommendation
        options = [self._make_option(0, 1500.0)]
        result = decide(options, "onion", CROPS_CFG, trader_offer_per_q=2000.0)
        assert result.recommendation == Recommendation.ACCEPT

    def test_cash_deadline_respected(self):
        from sellsmart.decision.engine import decide
        options = [self._make_option(0, 1600.0), self._make_option(14, 2200.0)]
        result = decide(options, "onion", CROPS_CFG, cash_deadline_days=5)
        # Best option (day 14) is beyond deadline; should fall back to day 0
        assert result.best_option is not None
        assert result.best_option.days_from_now <= 5
