from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
import uvicorn

# Add sell_smart/src to sys.path
SELL_SMART_SRC = Path(__file__).parent.parent / "sell_smart" / "src"
if str(SELL_SMART_SRC) not in sys.path:
    sys.path.insert(0, str(SELL_SMART_SRC))

from sellsmart.service.api import AdviceService

app = FastAPI(
    title="Sell Smart Decision Intelligence API",
    description="APMC mandi decision support and trigger intelligence engine.",
    version="1.0.0",
)

advice_service = AdviceService()


class VillageInfo(BaseModel):
    text: Optional[str] = "Nashik"
    lat: Optional[float] = None
    lon: Optional[float] = None


class AdviceRequest(BaseModel):
    crop: str = Field(..., description="Crop name: soybean, onion, or tomato")
    quantity_q: float = Field(20.0, description="Harvest quantity in quintals")
    village: Optional[VillageInfo] = None
    cash_deadline_days: int = Field(7, description="Farmer cash deadline in days")
    trader_offer_per_q: Optional[float] = Field(None, description="Local trader offer in Rs/quintal")
    storage_available: bool = Field(True, description="Whether on-farm storage is available")
    storage_condition: str = Field("ambient", description="Storage condition: ambient, dry, humid")
    quality_factor: float = Field(1.0, description="Quality factor: 1.0 (good) to 0.5 (poor)")
    as_of: Optional[str] = Field(None, description="As of date (YYYY-MM-DD) or null for latest")
    language: str = Field("en", description="Preferred response language: en, mr, hi")


@app.get("/health")
def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "sell_smart",
        "provenance": {
            "soybean": {"price_source": "real", "is_synthetic": False},
            "onion": {"price_source": "synthetic", "is_synthetic": True},
            "tomato": {"price_source": "synthetic", "is_synthetic": True},
        },
        "governance_rule": "Headline Rs claims allowed only for crops with real prices (ADR-001)",
    }


@app.post("/v1/advice")
def get_advice(req: AdviceRequest) -> Dict[str, Any]:
    """
    Main decision endpoint per PRD Section 8.7 & 15.1.
    Strictly carries per-crop is_synthetic and price_source flags.
    Visibly discloses simulated prices for Onion and Tomato and disables headline Rs claims.
    """
    v_text = req.village.text if req.village else ""
    v_lat = req.village.lat if req.village else None
    v_lon = req.village.lon if req.village else None

    response = advice_service.get_advice(
        crop=req.crop,
        quantity_q=req.quantity_q,
        village_text=v_text,
        village_lat=v_lat,
        village_lon=v_lon,
        cash_deadline_days=req.cash_deadline_days,
        trader_offer_per_q=req.trader_offer_per_q,
        storage_available=req.storage_available,
        storage_condition=req.storage_condition,
        quality_factor=req.quality_factor,
        as_of=req.as_of,
        language=req.language,
    )
    return response


@app.post("/webhook")
async def twilio_webhook(request: Request) -> Dict[str, str]:
    form_data = await request.form()
    incoming_msg = form_data.get("Body", "")
    sender = form_data.get("From", "")
    print(f"Received from {sender}: {incoming_msg}")
    return {"status": "success"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
