"""
Tests for Synthetic Decision Governance & Provenance Tagging (ADR-001).
Verifies:
1. Onion and Tomato advice responses visibly state that prices are simulated.
2. Every advice response carries is_synthetic and price_source per crop.
3. Headline Rs claims are strictly disabled for synthetic crops.
4. FastAPI endpoint /v1/advice produces compliant payload.
"""
import pytest
from datetime import date

from sellsmart.decision.engine import decide, Recommendation
from sellsmart.decision.options import SellingOption
from sellsmart.service.api import AdviceService
from backend.main import app
from fastapi.testclient import TestClient


def test_onion_advice_visibly_says_prices_are_simulated():
    crops_cfg = {"onion": {"hold_allowed_default": True}}
    opt = SellingOption(
        mandi_id="mh_nashik_lasalgaon", sell_date=date(2025, 4, 15), days_from_now=0,
        modal_price_forecast=2000.0, forecast_lower=1900.0, forecast_upper=2100.0,
        net_return_per_q=1900.0, economics_breakdown={}, is_open_day=True, is_placeholder=False,
    )
    res = decide([opt], crop="onion", crops_config=crops_cfg)
    api_resp = res.to_api_response()

    # Per-crop flags
    assert api_resp["crop"] == "onion"
    assert api_resp["is_synthetic"] is True
    assert api_resp["price_source"] == "synthetic"

    # Visible simulation notice in advice message
    assert "[SIMULATED PRICES" in api_resp["advice_message"]
    assert "simulated" in api_resp["advice_message"].lower()

    # Simulation notice field
    assert api_resp["simulation_notice"] is not None
    assert "SIMULATED PRICES" in api_resp["simulation_notice"]
    assert "ADR-001" in api_resp["simulation_notice"]

    # Disclaimers visibly include simulated prices notice
    assert any("SIMULATED PRICES" in d for d in api_resp["disclaimers"])

    # Headline Rs claim is disabled
    assert api_resp["headline_gain_claim"] is None


def test_soybean_advice_carries_real_provenance():
    crops_cfg = {"soybean": {"hold_allowed_default": True}}
    opt_today = SellingOption(
        mandi_id="mp_dewas", sell_date=date(2025, 4, 15), days_from_now=0,
        modal_price_forecast=4800.0, forecast_lower=4700.0, forecast_upper=4900.0,
        net_return_per_q=4700.0, economics_breakdown={}, is_open_day=True, is_placeholder=False,
    )
    opt_future = SellingOption(
        mandi_id="mp_dewas", sell_date=date(2025, 4, 22), days_from_now=7,
        modal_price_forecast=5100.0, forecast_lower=4900.0, forecast_upper=5300.0,
        net_return_per_q=4950.0, economics_breakdown={}, is_open_day=True, is_placeholder=False,
    )
    res = decide([opt_today, opt_future], crop="soybean", crops_config=crops_cfg)
    api_resp = res.to_api_response()

    assert api_resp["crop"] == "soybean"
    assert api_resp["is_synthetic"] is False
    assert api_resp["price_source"] == "real"
    assert api_resp["simulation_notice"] is None
    # Real crop allows headline claim
    assert api_resp["headline_gain_claim"] is not None
    assert "+₹" in api_resp["headline_gain_claim"]
    assert "gain over immediate sale" in api_resp["headline_gain_claim"]


def test_api_v1_advice_endpoint_onion_visible_simulation():
    client = TestClient(app)
    req_body = {
        "crop": "onion",
        "quantity_q": 20,
        "village": {"text": "Niphad, Nashik", "lat": 20.08, "lon": 74.11},
        "cash_deadline_days": 7,
        "trader_offer_per_q": 1480,
    }
    response = client.post("/v1/advice", json=req_body)
    assert response.status_code == 200
    data = response.json()

    assert data["crop"] == "onion"
    assert data["is_synthetic"] is True
    assert data["price_source"] == "synthetic"
    assert "[SIMULATED PRICES" in data["advice_message"]
    assert "simulated" in data["advice_message"].lower()
    assert any("SIMULATED PRICES" in d for d in data["disclaimers"])
    assert data["headline_gain_claim"] is None
