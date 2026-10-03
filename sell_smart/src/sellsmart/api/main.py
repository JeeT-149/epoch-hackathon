"""
sell_smart.api.main
FastAPI service exposing the Sell Smart decision intelligence pipeline as JSON.

Endpoints:
  POST /decide       — core decision for a single farmer request
  GET  /health       — liveness check
  GET  /calibration  — calibration passport for a crop+horizon
  GET  /mandis       — list selected mandis
  GET  /shocks/{crop} — recent shock events for a crop
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure src is on path when running directly
_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(_ROOT / "src"))

from sellsmart.common.config import load_config, load_crops_config
from sellsmart.common.disclaimers import get_disclaimers
from sellsmart.common.logging import get_logger
from sellsmart.economics.netreturn import compute_net_return
from sellsmart.decision.options import generate_options
from sellsmart.decision.engine import decide
from sellsmart.decision.confidence import compute_confidence
from sellsmart.shock.radar import detect_shocks

logger = get_logger("sell_smart.api")

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Sell Smart Decision Intelligence API",
    description=(
        "Risk-aware agricultural decision engine for Indian farmers. "
        "Tells farmers: SELL NOW / WAIT / SWITCH MANDI / ACCEPT TRADER OFFER. "
        "All numbers from deterministic backend code (R1). No LLM price/forecast numbers."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Config & data loading (lazy, cached)
# ---------------------------------------------------------------------------

_config: dict | None = None
_crops_cfg: dict | None = None
_mandis: list[dict] | None = None
_silver: pd.DataFrame | None = None
_gold: pd.DataFrame | None = None
_calendar: pd.DataFrame | None = None
_calibration_passports: list[dict] | None = None

CONFIG_DIR = _ROOT / "sell_smart" / "config"
DATA_DIR   = _ROOT / "sell_smart" / "data"
ARTS_DIR   = _ROOT / "sell_smart" / "artifacts"


def _get_config() -> dict:
    global _config
    if _config is None:
        _config = load_config(config_dir=CONFIG_DIR).as_dict()
    return _config


def _get_crops_cfg() -> dict:
    global _crops_cfg
    if _crops_cfg is None:
        _crops_cfg = load_crops_config(config_dir=CONFIG_DIR)
    return _crops_cfg


def _get_mandis() -> list[dict]:
    global _mandis
    if _mandis is None:
        import yaml
        mandis_yaml = CONFIG_DIR / "mandis.yaml"
        if mandis_yaml.exists():
            with open(mandis_yaml) as f:
                _mandis = yaml.safe_load(f).get("mandis", [])
        else:
            _mandis = []
    return _mandis


def _get_gold() -> pd.DataFrame:
    global _gold
    if _gold is None:
        gold_path = DATA_DIR / "gold" / "gold_panel.parquet"
        if gold_path.exists():
            _gold = pd.read_parquet(gold_path)
        else:
            _gold = pd.DataFrame()
    return _gold


def _get_calendar() -> pd.DataFrame:
    global _calendar
    if _calendar is None:
        cal_path = DATA_DIR / "gold" / "calendar.parquet"
        if cal_path.exists():
            _calendar = pd.read_parquet(cal_path)
        else:
            _calendar = pd.DataFrame()
    return _calendar


def _get_passports() -> list[dict]:
    global _calibration_passports
    if _calibration_passports is None:
        pp = ARTS_DIR / "calibration_passport.json"
        if pp.exists():
            with open(pp) as f:
                _calibration_passports = json.load(f)
        else:
            _calibration_passports = []
    return _calibration_passports


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class DecideRequest(BaseModel):
    crop: str = Field(..., description="Crop name: 'onion', 'tomato', or 'soybean'")
    quantity_q: float = Field(..., gt=0, description="Quantity in quintals")
    village_lat: float = Field(..., description="Farmer village latitude")
    village_lon: float = Field(..., description="Farmer village longitude")
    cash_deadline_days: Optional[int] = Field(None, ge=0, description="Days until cash is needed")
    storage_condition: str = Field("ambient", description="Storage condition: ambient/dry/humid/ambient_dry")
    quality_factor: float = Field(1.0, ge=0.0, le=1.0, description="Quality factor (1.0=good, <1=degraded)")
    trader_offer_per_q: Optional[float] = Field(None, description="Trader offer price per quintal (optional)")
    today: Optional[str] = Field(None, description="Decision date ISO-8601 (default: today)")


class OptionOut(BaseModel):
    mandi_id: str
    sell_date: str
    days_from_now: int
    modal_price_forecast: float
    forecast_lower: float
    forecast_upper: float
    net_return_per_q: float
    is_placeholder: bool
    calendar_assumed: bool


class DecideResponse(BaseModel):
    recommendation: str
    confidence: str
    confidence_score: float
    best_mandi: Optional[str]
    best_sell_date: Optional[str]
    days_to_wait: int
    expected_net_return_per_q: float
    reasoning: list[str]
    trader_offer_comparison: dict
    top_options: list[OptionOut]
    disclaimers: list[str]
    demo_ready: bool
    modal_price_proxy_note: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    """Liveness check."""
    return {"status": "ok", "version": "1.0.0", "service": "sell_smart_decision_api"}


@app.get("/mandis")
def list_mandis(crop: Optional[str] = Query(None, description="Filter by crop")):
    """List selected APMC mandis with geocodes and DQ scores."""
    mandis = _get_mandis()
    if crop:
        mandis = [m for m in mandis if m.get("crop") == crop]
    return {"mandis": mandis, "count": len(mandis)}


@app.get("/calibration")
def get_calibration(
    crop: str = Query(..., description="Crop name"),
    horizon: int = Query(7, description="Forecast horizon in days"),
):
    """Return calibration passport for a crop and horizon."""
    passports = _get_passports()
    match = [p for p in passports if p.get("crop") == crop and p.get("horizon_days") == horizon]
    if not match:
        raise HTTPException(
            status_code=404,
            detail=f"No calibration passport found for crop='{crop}', horizon={horizon}d. Run pipeline first."
        )
    return match[0]


@app.get("/shocks/{crop}")
def get_shocks(
    crop: str,
    lookback_days: int = Query(30, ge=10, le=90),
    z_threshold: float = Query(3.0, ge=1.0, le=6.0),
):
    """Detect recent shock events in mandi prices for a crop."""
    gold = _get_gold()
    if gold.empty or "crop" not in gold.columns:
        return {"crop": crop, "shocks": [], "note": "No gold panel data available. Run pipeline first."}

    crop_data = gold[gold["crop"] == crop]
    if crop_data.empty:
        return {"crop": crop, "shocks": [], "note": f"No data for crop '{crop}'."}

    price_series = (
        crop_data.groupby("date")["modal_price"]
        .median()
        .sort_index()
        .dropna()
    )
    if len(price_series) < lookback_days:
        return {"crop": crop, "shocks": [], "note": f"Insufficient data ({len(price_series)} days)."}

    shocks_df = detect_shocks(price_series, z_threshold=z_threshold, lookback_window=lookback_days)
    shock_events = shocks_df[shocks_df["is_shock"]].reset_index()
    shock_events["date"] = shock_events["date"].astype(str)

    return {
        "crop": crop,
        "z_threshold": z_threshold,
        "lookback_days": lookback_days,
        "n_shocks": len(shock_events),
        "shocks": shock_events[["date", "price", "rolling_mean", "z_score"]].to_dict(orient="records"),
    }


@app.post("/decide", response_model=DecideResponse)
def decide_endpoint(req: DecideRequest):
    """
    Core decision endpoint.

    Returns SELL NOW / WAIT / SWITCH MANDI / ACCEPT TRADER / HOLD SUSPENDED
    with full reasoning, economics breakdown, and calibrated confidence.

    All numbers from deterministic backend code (R1). Modal price is a
    market-level reference, not a guaranteed realisation price (R9).
    """
    config = _get_config()
    crops_cfg = _get_crops_cfg()
    mandis = _get_mandis()
    gold = _get_gold()
    calendar = _get_calendar()

    if req.crop not in crops_cfg:
        raise HTTPException(status_code=400, detail=f"Unknown crop '{req.crop}'. Must be one of: {list(crops_cfg.keys())}")

    today_date = date.fromisoformat(req.today) if req.today else date.today()

    # Get candidate mandis for this crop
    crop_mandis = [m for m in mandis if m.get("crop") == req.crop]
    if not crop_mandis:
        raise HTTPException(
            status_code=404,
            detail=f"No mandis available for crop '{req.crop}'. Run pipeline to select mandis."
        )

    # Check for shock in the last 7 days
    shock_detected = False
    if not gold.empty and "crop" in gold.columns:
        crop_prices = gold[gold["crop"] == req.crop].sort_values("date")
        if len(crop_prices) > 30:
            price_series = crop_prices.set_index("date")["modal_price"].dropna()
            shocks_df = detect_shocks(price_series, z_threshold=3.0, lookback_window=30)
            recent_shocks = shocks_df.tail(7)["is_shock"]
            shock_detected = bool(recent_shocks.any())

    # Build economics closure
    def _econ(m_info, days_held, modal_price=None):
        m_lat = m_info.get("lat") or req.village_lat
        m_lon = m_info.get("lon") or req.village_lon
        dist = max(5.0, _haversine(req.village_lat, req.village_lon, m_lat, m_lon))
        if modal_price is None or modal_price <= 0:
            # Use last known price for this mandi/crop from gold panel
            if not gold.empty:
                sub = gold[(gold["crop"] == req.crop) & (gold["mandi_id"] == m_info.get("mandi_id", ""))]["modal_price"].dropna()
                modal_price = float(sub.iloc[-1]) if len(sub) > 0 else 2000.0
            else:
                modal_price = 2000.0
        return compute_net_return(
            modal_price=modal_price,
            crop=req.crop,
            distance_km=dist,
            quantity_q=req.quantity_q,
            days_held=days_held,
            crops_config=crops_cfg,
            storage_condition=req.storage_condition,
            quality_factor=req.quality_factor,
        )

    # Generate options (no forecasts available in live API without a trained model store)
    # Pass empty forecasts — generate_options will skip forecast-dependent options,
    # but economics options (day 0) will still be generated.
    options = generate_options(
        crop=req.crop,
        today=today_date,
        mandis=crop_mandis,
        forecasts=pd.DataFrame(columns=["date", "mandi_id", "crop"]),
        calendar_df=calendar,
        economics_fn=_econ,
        max_days=req.cash_deadline_days or 14,
        cash_deadline_days=req.cash_deadline_days,
    )

    # Confidence scoring
    dq_score = float(crop_mandis[0].get("data_quality_score", 0.5)) if crop_mandis else 0.5
    passports = _get_passports()
    passport = next((p for p in passports if p.get("crop") == req.crop and p.get("horizon_days") == 7), None)
    interval_width = 300.0
    if passport:
        interval_width = passport.get("calibration", {}).get("conformal", {}).get("mean_interval_width", 300.0)

    last_known_price = 2000.0
    if not gold.empty:
        sub = gold[gold["crop"] == req.crop]["modal_price"].dropna()
        if len(sub) > 0:
            last_known_price = float(sub.iloc[-1])

    is_ph = crops_cfg.get(req.crop, {}).get("spoilage", {}).get("source", "PLACEHOLDER") == "PLACEHOLDER"
    conf_label, conf_score = compute_confidence(
        dq_score=dq_score,
        model_interval_width=interval_width,
        modal_price=last_known_price,
        is_placeholder=is_ph,
        config=config,
    )

    result = decide(
        options=options,
        crop=req.crop,
        crops_config=crops_cfg,
        trader_offer_per_q=req.trader_offer_per_q,
        cash_deadline_days=req.cash_deadline_days,
        shock_detected=shock_detected,
        confidence_score=conf_score,
        confidence_label=conf_label,
    )

    disclaimers = get_disclaimers(demo_ready=result.demo_ready, has_synthetic=False)

    top_options = [
        OptionOut(
            mandi_id=o.mandi_id,
            sell_date=str(o.sell_date),
            days_from_now=o.days_from_now,
            modal_price_forecast=o.modal_price_forecast,
            forecast_lower=o.forecast_lower,
            forecast_upper=o.forecast_upper,
            net_return_per_q=round(o.net_return_per_q, 2),
            is_placeholder=o.is_placeholder,
            calendar_assumed=o.calendar_assumed,
        )
        for o in (result.all_options or [])[:5]
    ]

    return DecideResponse(
        recommendation=result.recommendation.value,
        confidence=result.confidence_label,
        confidence_score=round(conf_score, 3),
        best_mandi=result.best_option.mandi_id if result.best_option else None,
        best_sell_date=str(result.best_option.sell_date) if result.best_option else None,
        days_to_wait=result.best_option.days_from_now if result.best_option else 0,
        expected_net_return_per_q=round(result.best_option.net_return_per_q, 2) if result.best_option else 0.0,
        reasoning=result.reasoning,
        trader_offer_comparison=result.trader_offer_comparison,
        top_options=top_options,
        disclaimers=disclaimers,
        demo_ready=result.demo_ready,
        modal_price_proxy_note=result.modal_price_proxy_note,
    )


def _haversine(lat1, lon1, lat2, lon2) -> float:
    import math
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# Entry point for direct execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("sellsmart.api.main:app", host="0.0.0.0", port=8000, reload=True)
