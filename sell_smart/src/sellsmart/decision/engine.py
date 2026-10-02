"""
sell_smart.decision.engine
Core decision engine: rank options, apply constraints, produce recommendation.

Product: SELL NOW | WAIT | SWITCH MANDI | HOLD SUSPENDED
Numbers come only from deterministic backend code (R1, R6).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

from sellsmart.decision.options import SellingOption
from sellsmart.common.logging import get_logger

logger = get_logger(__name__)


class Recommendation(str, Enum):
    SELL_NOW = "sell_now"
    WAIT = "wait"
    SWITCH_MANDI = "switch_mandi"
    HOLD_SUSPENDED = "hold_suspended"
    ACCEPT = "accept"  # near-parity with trader offer


@dataclass
class DecisionResult:
    recommendation: Recommendation
    best_option: Optional[SellingOption]
    all_options: list[SellingOption]
    confidence_label: str
    confidence_score: float
    trader_offer_comparison: dict
    reasoning: list[str]
    is_placeholder: bool
    demo_ready: bool
    modal_price_proxy_note: str = (
        "Modal price is a market-level reference, not a guaranteed realisation price."
    )
    disclaimers: list[str] = field(default_factory=list)


def decide(
    options: list[SellingOption],
    crop: str,
    crops_config: dict,
    trader_offer_per_q: float | None = None,
    cash_deadline_days: int | None = None,
    shock_detected: bool = False,
    confidence_score: float = 0.5,
    confidence_label: str = "MEDIUM",
) -> DecisionResult:
    """
    Core decision logic.

    Strategy:
    1. If shock_detected → HOLD_SUSPENDED
    2. Filter options: only open days, within deadline
    3. Sort by net_return_per_q descending
    4. Best option:
       - If best is today (days_from_now == 0) → SELL_NOW (or ACCEPT if trader offer matches)
       - If best is today but different mandi → SWITCH_MANDI
       - If best is future → WAIT
    5. Compare with trader_offer if provided

    All numbers from deterministic code. No LLM involvement (R1).
    """
    is_placeholder = any(o.is_placeholder for o in options) if options else True
    demo_ready = not is_placeholder

    if shock_detected:
        return DecisionResult(
            recommendation=Recommendation.HOLD_SUSPENDED,
            best_option=None,
            all_options=options,
            confidence_label="LOW",
            confidence_score=0.0,
            trader_offer_comparison={},
            reasoning=["Market shock detected. Hold suspended pending reassessment."],
            is_placeholder=is_placeholder,
            demo_ready=demo_ready,
        )

    if not options:
        return DecisionResult(
            recommendation=Recommendation.SELL_NOW,
            best_option=None,
            all_options=[],
            confidence_label="LOW",
            confidence_score=0.0,
            trader_offer_comparison={},
            reasoning=["No viable options found. Default: sell now at nearest mandi."],
            is_placeholder=True,
            demo_ready=False,
        )

    # Sort by net_return_per_q descending
    ranked = sorted(options, key=lambda o: o.net_return_per_q, reverse=True)
    best = ranked[0]

    reasoning = []

    # Nearest mandi today baseline (no-offer baseline per PRD)
    today_options = [o for o in options if o.days_from_now == 0]
    nearest_today = max(today_options, key=lambda o: o.net_return_per_q) if today_options else None

    # Determine recommendation
    if best.days_from_now == 0:
        # Check if it's a different mandi from first option today
        if nearest_today and best.mandi_id != nearest_today.mandi_id:
            rec = Recommendation.SWITCH_MANDI
            reasoning.append(
                f"Higher net return at {best.mandi_id} today "
                f"(₹{best.net_return_per_q:.0f}/q vs ₹{nearest_today.net_return_per_q:.0f}/q)"
            )
        else:
            rec = Recommendation.SELL_NOW
            reasoning.append(f"Best net return is today at {best.mandi_id}.")
    else:
        # Wait: verify holding is allowed for crop
        hold_allowed = crops_config.get(crop, {}).get("hold_allowed_default", False)
        if not hold_allowed:
            # Force sell now if hold not recommended
            best_today = nearest_today or ranked[0]
            reasoning.append(
                f"Holding not recommended for {crop} (hold_allowed_default=false). "
                "Recommending sell at best available today."
            )
            if nearest_today and best_today.mandi_id != (today_options[0].mandi_id if today_options else ""):
                rec = Recommendation.SWITCH_MANDI
            else:
                rec = Recommendation.SELL_NOW
            best = best_today
        else:
            rec = Recommendation.WAIT
            reasoning.append(
                f"Best net return in {best.days_from_now} days at {best.mandi_id}: "
                f"₹{best.net_return_per_q:.0f}/q"
            )

    # Trader offer comparison
    trader_comparison = {}
    if trader_offer_per_q is not None and nearest_today:
        diff = nearest_today.net_return_per_q - trader_offer_per_q
        trader_comparison = {
            "trader_offer_per_q": trader_offer_per_q,
            "mandi_net_return_today": nearest_today.net_return_per_q,
            "difference_per_q": round(diff, 2),
            "recommendation": "accept_trader" if diff < 0 else "reject_trader",
        }
        if diff < 0:
            reasoning.append(
                f"Trader offer (₹{trader_offer_per_q}/q) exceeds mandi net return today. "
                "Consider accepting."
            )
            rec = Recommendation.ACCEPT

    # Cash deadline warning
    if cash_deadline_days is not None and best.days_from_now > cash_deadline_days:
        reasoning.append(
            f"⚠ Best option (day {best.days_from_now}) is beyond cash deadline "
            f"({cash_deadline_days} days). Falling back to best option within deadline."
        )
        within_deadline = [o for o in ranked if o.days_from_now <= cash_deadline_days]
        if within_deadline:
            best = within_deadline[0]

    from sellsmart.common.disclaimers import get_disclaimers
    disclaimers = get_disclaimers(demo_ready=demo_ready, has_synthetic=False)

    return DecisionResult(
        recommendation=rec,
        best_option=best,
        all_options=ranked[:10],
        confidence_label=confidence_label,
        confidence_score=confidence_score,
        trader_offer_comparison=trader_comparison,
        reasoning=reasoning,
        is_placeholder=is_placeholder,
        demo_ready=demo_ready,
        disclaimers=disclaimers,
    )
