"""
sell_smart.regret.receipt
Regret Receipt: after sell decision, compute actual vs recommended outcome.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class RegretReceipt:
    crop: str
    mandi_id: str
    decision_date: date
    sell_date: date
    recommended_action: str
    actual_price_received: float
    actual_net_return: float
    counterfactual_price: float  # price if different action taken
    counterfactual_net_return: float
    regret_per_q: float  # actual - counterfactual (negative = regret)
    days_held: int
    is_placeholder: bool

    def to_dict(self) -> dict:
        return {
            "crop": self.crop,
            "mandi_id": self.mandi_id,
            "decision_date": str(self.decision_date),
            "sell_date": str(self.sell_date),
            "recommended_action": self.recommended_action,
            "actual_price_received": self.actual_price_received,
            "actual_net_return": round(self.actual_net_return, 2),
            "counterfactual_price": self.counterfactual_price,
            "counterfactual_net_return": round(self.counterfactual_net_return, 2),
            "regret_per_q": round(self.regret_per_q, 2),
            "days_held": self.days_held,
            "is_placeholder": self.is_placeholder,
            "note": "Regret is difference between actual outcome and best available alternative at decision time.",
        }


def compute_regret(
    actual_net_return: float,
    counterfactual_net_return: float,
    **kwargs,
) -> RegretReceipt:
    regret = actual_net_return - counterfactual_net_return
    return RegretReceipt(
        actual_net_return=actual_net_return,
        counterfactual_net_return=counterfactual_net_return,
        regret_per_q=regret,
        **kwargs,
    )
