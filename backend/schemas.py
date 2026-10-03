from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from datetime import date

class Village(BaseModel):
    text: str
    lat: Optional[float] = None
    lon: Optional[float] = None

class ParsedRequest(BaseModel):
    crop: Optional[Literal["onion", "tomato", "soybean"]] = None
    quantity: Optional[float] = None
    unit: Optional[Literal["quintal", "kg", "tonne"]] = None
    village_text: Optional[str] = None
    trader_offer_per_q: Optional[float] = None
    cash_deadline_days: Optional[int] = None
    language: Optional[Literal["mr", "hi", "en"]] = None
    missing_fields: List[str] = Field(default_factory=list)
    parse_confidence: float = 0.0

class AdviceRequest(BaseModel):
    crop: Literal["onion", "tomato", "soybean"]
    quantity_q: float
    village: Village
    cash_deadline_days: int
    trader_offer_per_q: Optional[float] = None
    storage_available: bool = False
    storage_condition: Optional[str] = None
    quality_factor: float = 1.0
    as_of: Optional[date] = None
    language: Literal["mr", "hi", "en"] = "mr"

class ReferenceStatus(BaseModel):
    type: str
    net_per_q: float

class BestNow(BaseModel):
    mandi_id: str
    net_per_q: float
    h: int = 0

class Quantiles(BaseModel):
    p10: float
    p50: float
    p90: float

class ChosenOption(BaseModel):
    mandi_id: str
    h: int
    date: date
    net_per_q: Quantiles
    gain_vs_reference_per_q: Quantiles
    p_beat: float

class TriggerPlan(BaseModel):
    target_price_per_q: float
    deadline: date
    fallback: str

class MessageSlots(BaseModel):
    offer: Optional[float] = None
    days: Optional[int] = None
    mandi: Optional[str] = None
    gain_med: Optional[float] = None
    gain_low: Optional[float] = None
    gain_high: Optional[float] = None
    confidence: Optional[str] = None
    target_price: Optional[float] = None
    caution: Optional[str] = None

class Message(BaseModel):
    template_id: str
    language: str
    slots: MessageSlots
    text: str

class Clarification(BaseModel):
    missing: List[str]
    question_id: str

class Meta(BaseModel):
    api_version: str = "1.0"
    model_versions: str = "mock-1.0"
    config_hash: str = "mockhash"
    data_hash: str = "mockhash"
    as_of: date
    demo_ready: bool = False
    confidence_validated: bool = False
    synthetic_inputs: List[str] = []
    assumptions_register_url: str = "mock_url"

class AdviceResponse(BaseModel):
    status: Literal["ACCEPT_OFFER", "SWITCH_MARKET_NOW", "WAIT_WITH_TRIGGER", "SELL_NOW_NEAREST", "NO_CONFIDENT_ADVICE"]
    reference: ReferenceStatus
    best_now: Optional[BestNow] = None
    chosen: Optional[ChosenOption] = None
    confidence: Literal["High", "Medium", "Low"]
    reason_codes: List[str]
    trigger: Optional[TriggerPlan] = None
    caution_flags: List[str] = []
    demo_ready: bool = False
    synthetic_inputs: List[str] = []
    message: Message
    clarification: Optional[Clarification] = None
    meta: Meta
