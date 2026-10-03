from datetime import date, timedelta
from .schemas import AdviceRequest, AdviceResponse, ReferenceStatus, BestNow, ChosenOption, Quantiles, TriggerPlan, Message, MessageSlots, Meta

def mock_decision_engine(request: AdviceRequest) -> AdviceResponse:
    # A deterministic mock decision engine returning PRD-compliant data.
    # We use a simple conditional to show different statuses if needed, 
    # but primarily default to WAIT_WITH_TRIGGER for demonstration.
    
    current_date = request.as_of or date.today()
    target_date = current_date + timedelta(days=6)
    
    status = "WAIT_WITH_TRIGGER"
    mandi = "mh_nashik_lasalgaon"
    
    offer = request.trader_offer_per_q or 1400.0
    
    return AdviceResponse(
        status=status,
        reference=ReferenceStatus(
            type="trader_offer" if request.trader_offer_per_q else "nearest_mandi",
            net_per_q=offer
        ),
        best_now=BestNow(
            mandi_id=mandi,
            net_per_q=offer + 15.0,
            h=0
        ),
        chosen=ChosenOption(
            mandi_id=mandi,
            h=6,
            date=target_date,
            net_per_q=Quantiles(p10=offer + 50.0, p50=offer + 140.0, p90=offer + 220.0),
            gain_vs_reference_per_q=Quantiles(p10=50.0, p50=140.0, p90=220.0),
            p_beat=0.74
        ),
        confidence="Medium",
        reason_codes=["HOLD_GAIN_EXCEEDS_SPOILAGE", "CASH_DEADLINE_BINDING"],
        trigger=TriggerPlan(
            target_price_per_q=offer + 140.0,
            deadline=target_date,
            fallback="SELL_AT_BEST_AVAILABLE"
        ),
        caution_flags=["modal_price_proxy"],
        demo_ready=False,
        synthetic_inputs=["trader_offer_proxy"],
        message=Message(
            template_id="wait_with_trigger_offer",
            language=request.language,
            slots=MessageSlots(
                offer=offer,
                days=6,
                mandi="Lasalgaon",
                gain_med=140.0,
                gain_low=50.0,
                gain_high=220.0,
                confidence="Medium",
                target_price=offer + 140.0,
                caution="modal_price_proxy"
            ),
            text="Mock engine recommendation: Wait for 6 days. Target price is ₹{target}.".format(target=offer + 140.0)
        ),
        meta=Meta(
            as_of=current_date
        )
    )
