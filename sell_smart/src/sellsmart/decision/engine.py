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
    # Five canonical statuses (Step 4 & PRD)
    ACCEPT_OFFER = "ACCEPT_OFFER"
    SWITCH_MARKET_NOW = "SWITCH_MARKET_NOW"
    WAIT_WITH_TRIGGER = "WAIT_WITH_TRIGGER"
    SELL_NOW_NEAREST = "SELL_NOW_NEAREST"
    NO_CONFIDENT_ADVICE = "NO_CONFIDENT_ADVICE"

    # Backward-compatible aliases for test fixtures and legacy callers
    ACCEPT = "ACCEPT_OFFER"
    SWITCH_MANDI = "SWITCH_MARKET_NOW"
    WAIT = "WAIT_WITH_TRIGGER"
    SELL_NOW = "SELL_NOW_NEAREST"
    HOLD_SUSPENDED = "NO_CONFIDENT_ADVICE"


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
    crop: str = ""
    is_synthetic: bool = False
    price_source: str = "real"
    headline_gain_claim: Optional[str] = None
    simulation_notice: Optional[str] = None
    advice_message: str = ""

    def to_api_response(self) -> dict:
        """
        Produce /v1/advice JSON response payload per PRD Section 8.7 & 15.1.
        Visibly carries per-crop price_source, is_synthetic, and simulated price disclaimers.
        """
        return {
            "status": self.recommendation.value.upper(),
            "recommendation": self.recommendation.value,
            "crop": self.crop,
            "is_synthetic": self.is_synthetic,
            "price_source": self.price_source,
            "confidence": self.confidence_label,
            "confidence_score": round(self.confidence_score, 3),
            "advice_message": self.advice_message,
            "headline_gain_claim": self.headline_gain_claim,
            "simulation_notice": self.simulation_notice,
            "demo_ready": self.demo_ready,
            "best_option": {
                "mandi_id": self.best_option.mandi_id,
                "days_from_now": self.best_option.days_from_now,
                "sell_date": str(self.best_option.sell_date),
                "expected_net_return_per_q": round(float(self.best_option.net_return_per_q), 2),
            } if self.best_option else None,
            "trader_offer_comparison": self.trader_offer_comparison,
            "reasoning": self.reasoning,
            "disclaimers": self.disclaimers,
            "meta": {
                "pricing_rule": "Headline ₹ claims allowed only for crops with real prices (ADR-001)",
                "modal_price_proxy_note": self.modal_price_proxy_note,
            },
        }


def decide(
    options: list[SellingOption],
    crop: str,
    crops_config: dict,
    trader_offer_per_q: float | None = None,
    cash_deadline_days: int | None = None,
    shock_detected: bool = False,
    confidence_score: float = 0.5,
    confidence_label: str = "MEDIUM",
    forecast_usable: bool = True,
    decision_params: dict | None = None,
) -> DecisionResult:
    """
    Core decision logic incorporating tuned validation parameters (PRD Step 4).

    Statuses:
    1. ACCEPT_OFFER: Trader offer meets or beats mandi net return (with parity buffer).
    2. SWITCH_MARKET_NOW: Today at alternative mandi provides net gain >= min_gain_to_switch_rs.
    3. WAIT_WITH_TRIGGER: Future holding provides net gain >= min_gain_to_hold_rs and hold is permitted.
    4. SELL_NOW_NEAREST: Immediate local mandi sale is optimal or fallback.
    5. NO_CONFIDENT_ADVICE: Shock detected or confidence below min_confidence_score.
    """
    d_params = decision_params or {}
    min_switch_gain = float(d_params.get("min_gain_to_switch_rs", 25.0))
    min_hold_gain = float(d_params.get("min_gain_to_hold_rs", 50.0))
    parity_buffer = float(d_params.get("trader_offer_parity_buffer_rs", 10.0))
    min_conf_score = float(d_params.get("min_confidence_score", 0.20))

    is_placeholder = any(o.is_placeholder for o in options) if options else True
    demo_ready = not is_placeholder
    reasoning = []

    if not forecast_usable:
        # PRD Gating: Model failed skill or calibration gate; restrict to spatial-only (h=0)
        options = [o for o in options if o.days_from_now == 0]
        reasoning.append(
            "Forecast gating rule: Model did not beat baseline or pass calibration gate. "
            "Answering 'WHERE' to sell today only; 'WHEN' (hold) recommendations are disabled."
        )

    is_synthetic = crop.lower() in ["onion", "tomato"]
    price_source = "synthetic" if is_synthetic else "real"
    simulation_notice = (
        f"SIMULATED PRICES: {crop.capitalize()} price series are synthetic by human decision "
        f"(time constraint, ADR-001). Real-world headline ₹ claims are disabled."
    ) if is_synthetic else None

    # Shock detection check (PRD Section 11)
    if shock_detected:
        advice_msg = f"Hold suspended for {crop} pending market shock resolution."
        if is_synthetic:
            advice_msg = f"[SIMULATED PRICES: {crop.capitalize()} prices are simulated.] " + advice_msg
        return DecisionResult(
            recommendation=Recommendation.NO_CONFIDENT_ADVICE,
            best_option=None,
            all_options=options,
            confidence_label="LOW",
            confidence_score=0.0,
            trader_offer_comparison={},
            reasoning=["Market shock detected. Hold suspended pending reassessment."],
            is_placeholder=is_placeholder,
            demo_ready=demo_ready,
            crop=crop,
            is_synthetic=is_synthetic,
            price_source=price_source,
            simulation_notice=simulation_notice,
            advice_message=advice_msg,
        )

    # Empty options fallback
    if not options:
        advice_msg = f"No viable options found for {crop}. Default: sell now at nearest mandi."
        if is_synthetic:
            advice_msg = f"[SIMULATED PRICES: {crop.capitalize()} prices are simulated.] " + advice_msg
        return DecisionResult(
            recommendation=Recommendation.SELL_NOW_NEAREST,
            best_option=None,
            all_options=[],
            confidence_label="LOW",
            confidence_score=0.0,
            trader_offer_comparison={},
            reasoning=["No viable options found. Default: sell now at nearest mandi."],
            is_placeholder=True,
            demo_ready=False,
            crop=crop,
            is_synthetic=is_synthetic,
            price_source=price_source,
            simulation_notice=simulation_notice,
            advice_message=advice_msg,
        )

    # Low confidence guard: produce NO_CONFIDENT_ADVICE if model/data confidence is below tuned threshold
    if confidence_score < min_conf_score:
        advice_msg = f"Low confidence in current market projections for {crop}. Proceed with caution."
        if is_synthetic:
            advice_msg = f"[SIMULATED PRICES: {crop.capitalize()} prices are simulated.] " + advice_msg
        return DecisionResult(
            recommendation=Recommendation.NO_CONFIDENT_ADVICE,
            best_option=None,
            all_options=options,
            confidence_label=confidence_label,
            confidence_score=confidence_score,
            trader_offer_comparison={},
            reasoning=[f"Confidence score {confidence_score:.2f} below tuned threshold {min_conf_score:.2f}."],
            is_placeholder=is_placeholder,
            demo_ready=demo_ready,
            crop=crop,
            is_synthetic=is_synthetic,
            price_source=price_source,
            simulation_notice=simulation_notice,
            advice_message=advice_msg,
        )

    # Sort by net_return_per_q descending
    ranked = sorted(options, key=lambda o: o.net_return_per_q, reverse=True)
    best = ranked[0]

    # Nearest mandi today baseline (no-offer baseline per PRD)
    today_options = [o for o in options if o.days_from_now == 0]
    nearest_today = max(today_options, key=lambda o: o.net_return_per_q) if today_options else None

    # Determine recommendation
    if best.days_from_now == 0:
        # Check if it's a different mandi with significant gain
        if nearest_today and best.mandi_id != nearest_today.mandi_id and (best.net_return_per_q - nearest_today.net_return_per_q) >= min_switch_gain:
            rec = Recommendation.SWITCH_MARKET_NOW
            reasoning.append(
                f"Higher net return at {best.mandi_id} today "
                f"(₹{best.net_return_per_q:.0f}/q vs ₹{nearest_today.net_return_per_q:.0f}/q, "
                f"+₹{best.net_return_per_q - nearest_today.net_return_per_q:.0f}/q exceeds switch hurdle ₹{min_switch_gain:.0f}/q)"
            )
        else:
            rec = Recommendation.SELL_NOW_NEAREST
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
            if nearest_today and best_today.mandi_id != (today_options[0].mandi_id if today_options else "") and (best_today.net_return_per_q - nearest_today.net_return_per_q) >= min_switch_gain:
                rec = Recommendation.SWITCH_MARKET_NOW
            else:
                rec = Recommendation.SELL_NOW_NEAREST
            best = best_today
        else:
            expected_gain = (best.net_return_per_q - nearest_today.net_return_per_q) if nearest_today else 0.0
            if expected_gain >= min_hold_gain:
                rec = Recommendation.WAIT_WITH_TRIGGER
                reasoning.append(
                    f"Best net return in {best.days_from_now} days at {best.mandi_id}: "
                    f"₹{best.net_return_per_q:.0f}/q (+₹{expected_gain:.0f}/q over immediate sale)"
                )
            else:
                rec = Recommendation.SELL_NOW_NEAREST
                reasoning.append(
                    f"Expected holding gain (+₹{expected_gain:.0f}/q) does not exceed hurdle "
                    f"₹{min_hold_gain:.0f}/q. Recommending sell now at nearest mandi."
                )
                best = nearest_today or best

    # Trader offer comparison (PRD Section 8.4)
    trader_comparison = {}
    if trader_offer_per_q is not None and nearest_today:
        effective_trader_return = trader_offer_per_q + parity_buffer
        diff = nearest_today.net_return_per_q - effective_trader_return
        trader_comparison = {
            "trader_offer_per_q": trader_offer_per_q,
            "mandi_net_return_today": nearest_today.net_return_per_q,
            "parity_buffer_per_q": parity_buffer,
            "difference_per_q": round(diff, 2),
            "recommendation": "accept_trader" if diff < 0 else "reject_trader",
        }
        if diff < 0:
            reasoning.append(
                f"Trader offer (₹{trader_offer_per_q}/q) meets or beats mandi net return today "
                f"(₹{nearest_today.net_return_per_q:.0f}/q). Consider accepting on farm."
            )
            rec = Recommendation.ACCEPT_OFFER

    # Cash deadline warning
    if cash_deadline_days is not None and best.days_from_now > cash_deadline_days:
        reasoning.append(
            f"⚠ Best option (day {best.days_from_now}) is beyond cash deadline "
            f"({cash_deadline_days} days). Falling back to best option within deadline."
        )
        within_deadline = [o for o in ranked if o.days_from_now <= cash_deadline_days]
        if within_deadline:
            best = within_deadline[0]

    # Headline gain claim rule: allowed ONLY for real crops (Soybean)
    headline_gain_claim = None
    if is_synthetic:
        reasoning.append(
            f"Data provenance notice: {crop.capitalize()} prices are simulated by human decision (time constraint). "
            f"Real-world headline ₹ claims are disabled per ADR-001."
        )
    else:
        # Real prices (Soybean): headline claim allowed if outperforming immediate baseline
        if best and best.days_from_now > 0 and nearest_today:
            gain = best.net_return_per_q - nearest_today.net_return_per_q
            if gain > 0:
                headline_gain_claim = f"+₹{gain:.0f}/quintal projected gain over immediate sale"

    # Human-readable advice message
    if is_synthetic:
        advice_message = (
            f"[SIMULATED PRICES: {crop.capitalize()} prices are simulated by human decision (time constraint). "
            f"Real-world headline ₹ claims disabled.] "
            f"Recommendation: {rec.value.upper()} at {best.mandi_id if best else 'nearest mandi'}. "
            f"Note: Price levels for {crop} are synthetic simulation benchmarks."
        )
    else:
        gain_str = f" ({headline_gain_claim})" if headline_gain_claim else ""
        advice_message = (
            f"Recommendation: {rec.value.upper()} at {best.mandi_id if best else 'nearest mandi'}."
            f"{gain_str} Expected net return: ₹{best.net_return_per_q:.0f}/q."
        )

    from sellsmart.common.disclaimers import get_disclaimers
    disclaimers = get_disclaimers(demo_ready=demo_ready, has_synthetic=is_synthetic, is_synthetic_crop=is_synthetic)

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
        crop=crop,
        is_synthetic=is_synthetic,
        price_source=price_source,
        headline_gain_claim=headline_gain_claim,
        simulation_notice=simulation_notice,
        advice_message=advice_message,
    )
