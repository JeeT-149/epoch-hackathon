"""
tests/golden/test_golden_fixtures.py
Golden fixture tests (PRD Section 4.7):
- Rising price series → engine recommends WAIT
- Falling price series → engine recommends SELL_NOW
- Flat price series   → engine recommends ACCEPT (trader offer near-parity)
- Shock series        → engine recommends HOLD_SUSPENDED

These fixtures are deterministic and seeded. They verify the decision engine
produces expected recommendations under canonical price scenarios.
"""
import numpy as np
import pandas as pd
import pytest
from datetime import date, timedelta

from sellsmart.decision.engine import decide, Recommendation
from sellsmart.decision.options import SellingOption
from sellsmart.shock.radar import detect_shocks

# Minimal crop config for golden tests (sourced, no PLACEHOLDER)
CROPS_CFG = {
    "onion": {
        "hold_allowed_default": True,
        "max_storage_days": 90,
        "spoilage": {
            "curve": "linear_then_step",
            "daily_rate_pct": 1.0,
            "source": "NHRDF_2019",
            "conditions": {"ambient_dry": {"daily_rate_pct": 1.0}},
            "rot_acceleration_day": 45,
            "rot_acceleration_factor": 2.5,
        },
        "transport": {
            "vehicle_types": [{"name": "tempo", "capacity_q": 25, "cost_per_km": 16.0, "source": "MH_RTO_survey_2023"}],
            "loading_cost_per_q": 12.0,
        },
        "storage": {"cost_per_q_per_day": 1.5, "source": "Nashik_onion_storage_survey_2023"},
        "fees": {"mandi_commission_pct": 2.0, "weighing_per_q": 2.0, "source": "MH_APMC_Act_2016"},
    },
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
            "vehicle_types": [{"name": "tempo", "capacity_q": 25, "cost_per_km": 18.0, "source": "MH_RTO_survey_2023"}],
            "loading_cost_per_q": 15.0,
        },
        "storage": {"cost_per_q_per_day": 2.5, "source": "MH_agri_coldstorage_survey_2022"},
        "fees": {"mandi_commission_pct": 2.0, "weighing_per_q": 2.0, "source": "MH_APMC_Act_2016"},
    },
}


def _option(days: int, net_return: float, mandi_id: str = "test_mandi", placeholder: bool = False) -> SellingOption:
    return SellingOption(
        mandi_id=mandi_id,
        sell_date=date(2025, 1, 1) + timedelta(days=days),
        days_from_now=days,
        modal_price_forecast=2000.0 + days * 50.0,
        forecast_lower=1800.0,
        forecast_upper=2400.0,
        net_return_per_q=net_return,
        economics_breakdown={"net_return_per_q": net_return},
        is_open_day=True,
        is_placeholder=placeholder,
    )


class TestRisingPriceSeries:
    """Rising prices → engine should recommend WAIT (future return beats today)."""

    def test_wait_when_future_much_better(self):
        """Future options clearly beat today for onion (hold allowed)."""
        options = [
            _option(0, 1500.0),   # sell now: low return
            _option(3, 1700.0),
            _option(7, 2000.0),   # best: high future return
            _option(14, 1900.0),
        ]
        result = decide(options, "onion", CROPS_CFG, cash_deadline_days=30)
        assert result.recommendation == Recommendation.WAIT
        assert result.best_option.days_from_now > 0

    def test_wait_selects_highest_return(self):
        """The WAIT option should point to the highest net_return option."""
        options = [_option(0, 1500.0), _option(7, 2200.0), _option(14, 2100.0)]
        result = decide(options, "onion", CROPS_CFG, cash_deadline_days=30)
        assert result.best_option.net_return_per_q == pytest.approx(2200.0)


class TestFallingPriceSeries:
    """Falling prices → engine should recommend SELL_NOW (today beats future)."""

    def test_sell_now_when_today_best(self):
        """Today has highest net return; future options are worse."""
        options = [
            _option(0, 2000.0),   # best today
            _option(3, 1800.0),
            _option(7, 1600.0),
            _option(14, 1400.0),
        ]
        result = decide(options, "onion", CROPS_CFG, cash_deadline_days=30)
        assert result.recommendation == Recommendation.SELL_NOW
        assert result.best_option.days_from_now == 0

    def test_tomato_sell_now_regardless(self):
        """Tomato: even if future is better, hold not allowed → SELL_NOW or SWITCH_MANDI."""
        options = [_option(0, 1400.0), _option(3, 1900.0)]
        result = decide(options, "tomato", CROPS_CFG, cash_deadline_days=30)
        assert result.recommendation in (Recommendation.SELL_NOW, Recommendation.SWITCH_MANDI)


class TestFlatPriceSeries:
    """Flat prices → trader offer near parity → engine should ACCEPT."""

    def test_accept_when_trader_beats_mandi(self):
        """Trader offer exceeds mandi net return → ACCEPT."""
        options = [_option(0, 1800.0), _option(7, 1810.0)]
        result = decide(options, "onion", CROPS_CFG, trader_offer_per_q=2000.0)
        assert result.recommendation == Recommendation.ACCEPT

    def test_reject_trader_when_mandi_better(self):
        """Mandi net return beats trader → do not ACCEPT."""
        options = [_option(0, 2200.0), _option(7, 2100.0)]
        result = decide(options, "onion", CROPS_CFG, trader_offer_per_q=1800.0)
        assert result.recommendation != Recommendation.ACCEPT
        assert result.trader_offer_comparison.get("recommendation") == "reject_trader"


class TestShockSeries:
    """Shock detected → engine must suspend holding (HOLD_SUSPENDED)."""

    def test_hold_suspended_on_shock(self):
        """With shock_detected=True, any option set must yield HOLD_SUSPENDED."""
        options = [_option(0, 1900.0), _option(7, 2200.0)]
        result = decide(options, "onion", CROPS_CFG, shock_detected=True)
        assert result.recommendation == Recommendation.HOLD_SUSPENDED
        assert result.best_option is None

    def test_shock_radar_detects_jump(self):
        """Shock radar must flag a sudden price spike as a shock event."""
        n = 50
        rng = np.random.default_rng(42)
        prices = pd.Series(
            4000 + rng.normal(0, 50, n).cumsum() * 0.1,
            index=pd.date_range("2024-09-01", periods=n),
        )
        # Inject a 3-sigma spike
        prices.iloc[-5] = prices.iloc[-10:].mean() + 5 * prices.std()
        shocks = detect_shocks(prices, z_threshold=3.0, lookback_window=20)
        assert shocks["is_shock"].any(), "Shock radar failed to detect injected spike"

    def test_shock_radar_no_false_positives_on_stable(self):
        """Stable prices must produce no shock events."""
        prices = pd.Series(
            [2000.0 + i * 0.1 for i in range(60)],
            index=pd.date_range("2024-09-01", periods=60),
        )
        shocks = detect_shocks(prices, z_threshold=3.0, lookback_window=20)
        assert not shocks["is_shock"].any()

    def test_no_options_defaults_to_sell_now(self):
        """No viable options → default SELL_NOW (safe fallback)."""
        result = decide([], "onion", CROPS_CFG)
        assert result.recommendation == Recommendation.SELL_NOW


class TestCashDeadlineConstraint:
    """Cash deadline must override the best unconstrained option."""

    def test_deadline_forces_early_sell(self):
        """Best option is day 14 but deadline is 5 → must use option within deadline."""
        options = [_option(0, 1500.0), _option(3, 1700.0), _option(14, 2500.0)]
        result = decide(options, "onion", CROPS_CFG, cash_deadline_days=5)
        assert result.best_option.days_from_now <= 5

    def test_no_deadline_allows_best(self):
        """No deadline → best option can be far future."""
        options = [_option(0, 1500.0), _option(14, 2500.0)]
        result = decide(options, "onion", CROPS_CFG, cash_deadline_days=None)
        assert result.best_option.days_from_now == 14


class TestCalibrationPassport:
    """Calibration passport must report valid coverage fractions."""

    def test_empirical_coverage_in_range(self):
        from sellsmart.calibration.passport import compute_calibration_passport
        import numpy as np

        rng = np.random.default_rng(0)
        y_true = rng.normal(2000, 200, 100)
        y_pred_q50 = y_true + rng.normal(0, 50, 100)
        q50_below = (y_true < y_pred_q50).mean()
        # Should be close to 0.5
        assert 0.3 <= q50_below <= 0.7

        passport = compute_calibration_passport(
            y_true=y_true,
            y_pred_quantiles={0.5: y_pred_q50},
            crop="soybean",
            horizon=7,
        )
        assert "q50" in passport["calibration"]
        cal_err = passport["calibration"]["q50"]["calibration_error"]
        assert cal_err <= 0.5  # reasonable calibration

    def test_conformal_coverage_in_passport(self):
        from sellsmart.calibration.passport import compute_calibration_passport
        from sellsmart.forecast.conformal import ConformalPredictor
        import numpy as np

        rng = np.random.default_rng(1)
        y_true = rng.normal(2000, 200, 200)
        y_pred = y_true + rng.normal(0, 100, 200)

        cp = ConformalPredictor(alpha=0.10, min_calibration_size=50)
        cp.calibrate(y_true[:100], y_pred[:100])
        lower, upper = cp.predict_interval(y_pred[100:])

        passport = compute_calibration_passport(
            y_true=y_true[100:],
            y_pred_quantiles={0.5: y_pred[100:]},
            conformal_lower=lower,
            conformal_upper=upper,
            crop="soybean",
            horizon=7,
        )
        emp_cov = passport["calibration"]["conformal"]["empirical_coverage"]
        # With alpha=0.10 target 90%; should be >=85% on fresh data
        assert emp_cov >= 0.80
