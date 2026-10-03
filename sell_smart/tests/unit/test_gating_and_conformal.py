"""
Tests for Conformalized Quantile Regression (CQR) and Forecast Gating (PRD Sections 6.4, 6.6, 6.8 & Section 14).
"""
import numpy as np
import pytest

from sellsmart.forecast.conformal import CQRCalibrator, ConformalPredictor
from sellsmart.forecast.gating import pinball_loss, wilson_interval, evaluate_forecast_gate
from sellsmart.decision.engine import decide, Recommendation
from sellsmart.decision.options import SellingOption
from datetime import date


def test_pinball_loss_symmetry_and_values():
    # At q=0.5, pinball loss is 0.5 * mean absolute error
    y_true = np.array([100.0, 110.0, 120.0])
    y_pred = np.array([105.0, 110.0, 115.0])
    # diffs = [-5, 0, 5] -> absolute errors = [5, 0, 5] -> mean abs = 10/3 -> * 0.5 = 5/3
    loss = pinball_loss(y_true, y_pred, 0.5)
    assert pytest.approx(loss, rel=1e-3) == (10.0 / 3.0) * 0.5


def test_wilson_interval():
    low, high = wilson_interval(80, 100, confidence=0.95)
    assert 0.70 < low < 0.80
    assert 0.80 < high < 0.90


def test_cqr_calibration_and_prediction():
    np.random.seed(42)
    n = 100
    y_true = np.random.normal(2000, 100, n)
    q_preds = {
        0.10: y_true - 120,
        0.25: y_true - 50,
        0.50: y_true,
        0.75: y_true + 50,
        0.90: y_true + 120,
    }
    calibrator = CQRCalibrator(min_calibration_size=30)
    margins = calibrator.calibrate(y_true, q_preds, pairs=[(0.10, 0.90), (0.25, 0.75)])
    assert (0.10, 0.90) in margins
    assert (0.25, 0.75) in margins

    intervals = calibrator.predict_intervals(q_preds)
    low, high = intervals[(0.10, 0.90)]
    coverage = ((y_true >= low) & (y_true <= high)).mean()
    assert coverage >= 0.80


def test_evaluate_forecast_gate_pass_and_fail():
    n = 100
    y_true = np.linspace(2000, 2500, n)
    # Perfect model
    m1_preds = {
        0.05: y_true - 50,
        0.10: y_true - 30,
        0.50: y_true,
        0.90: y_true + 30,
        0.95: y_true + 50,
    }
    b0_preds = {q: np.full(n, 2000.0) for q in m1_preds}
    
    gate_pass = evaluate_forecast_gate(y_true, m1_preds, b0_preds, crop="soybean", horizon=7)
    assert gate_pass["skill_vs_b0"] > 0
    
    # Degraded model (negative skill vs b0)
    m1_terrible = {q: np.random.normal(5000, 1000, n) for q in m1_preds}
    gate_fail = evaluate_forecast_gate(y_true, m1_terrible, b0_preds, crop="soybean", horizon=7)
    assert gate_fail["forecast_usable"] is False
    assert "FAILED" in gate_fail["gate_reason"]


def test_decision_engine_respects_forecast_usable_gate():
    crops_cfg = {"onion": {"hold_allowed_default": True}}
    # Two options: one today (d=0), one in future (d=5) with higher return
    opt_today = SellingOption(
        mandi_id="m1", sell_date=date(2025, 4, 15), days_from_now=0,
        modal_price_forecast=2000.0, forecast_lower=1900.0, forecast_upper=2100.0,
        net_return_per_q=1900.0, economics_breakdown={}, is_open_day=True, is_placeholder=False,
    )
    opt_future = SellingOption(
        mandi_id="m1", sell_date=date(2025, 4, 20), days_from_now=5,
        modal_price_forecast=2500.0, forecast_lower=2300.0, forecast_upper=2700.0,
        net_return_per_q=2300.0, economics_breakdown={}, is_open_day=True, is_placeholder=False,
    )
    
    # When forecast is usable: should recommend WAIT (d=5)
    res_usable = decide([opt_today, opt_future], crop="onion", crops_config=crops_cfg, forecast_usable=True)
    assert res_usable.recommendation == Recommendation.WAIT
    assert res_usable.best_option.days_from_now == 5

    # When forecast is NOT usable: PRD says answer WHERE not WHEN -> hold disabled, restricted to today (d=0)
    res_gated = decide([opt_today, opt_future], crop="onion", crops_config=crops_cfg, forecast_usable=False)
    assert res_gated.recommendation == Recommendation.SELL_NOW
    assert res_gated.best_option.days_from_now == 0
    assert any("Forecast gating rule" in r for r in res_gated.reasoning)
