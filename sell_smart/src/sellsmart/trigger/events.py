"""
sell_smart.trigger.events
Trigger event log: structured events produced by the trigger engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class TriggerEvent:
    event_type: str  # price_drop | price_rise | shock | timeout | sell_signal
    mandi_id: str
    crop: str
    event_date: date
    price: float
    reference_price: float
    pct_change: float
    message: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "mandi_id": self.mandi_id,
            "crop": self.crop,
            "event_date": str(self.event_date),
            "price": self.price,
            "reference_price": self.reference_price,
            "pct_change": round(self.pct_change, 4),
            "message": self.message,
            **self.metadata,
        }
