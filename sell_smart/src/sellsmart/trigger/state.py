"""
sell_smart.trigger.state
State machine for daily monitoring: WATCHING → TRIGGERED → HOLD_SUSPENDED → EXPIRED.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum


class TriggerState(str, Enum):
    WATCHING = "watching"
    TRIGGERED_SELL = "triggered_sell"
    TRIGGERED_WAIT = "triggered_wait"
    HOLD_SUSPENDED = "hold_suspended"
    EXPIRED = "expired"


@dataclass
class TriggerStateRecord:
    mandi_id: str
    crop: str
    state: TriggerState = TriggerState.WATCHING
    entry_date: date | None = None
    last_update: date | None = None
    timeout_days: int = 30
    events: list[dict] = field(default_factory=list)

    def transition(self, new_state: TriggerState, event_date: date, reason: str) -> None:
        self.events.append({
            "from": self.state.value,
            "to": new_state.value,
            "date": str(event_date),
            "reason": reason,
        })
        self.state = new_state
        self.last_update = event_date

    def is_expired(self, today: date) -> bool:
        if self.entry_date is None:
            return False
        return (today - self.entry_date).days > self.timeout_days

    def check_timeout(self, today: date) -> bool:
        if self.is_expired(today) and self.state != TriggerState.EXPIRED:
            self.transition(TriggerState.EXPIRED, today, "state_timeout")
            return True
        return False
