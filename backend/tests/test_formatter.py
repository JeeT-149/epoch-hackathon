import pytest
from datetime import date

from backend.formatter import format_advice
from backend.schemas import AdviceResponse, Message, MessageSlots, ReferenceStatus, Meta

def test_format_advice_wait():
    # Setup minimal AdviceResponse with needed fields
    response = AdviceResponse(
        status="WAIT_WITH_TRIGGER",
        reference=ReferenceStatus(type="trader_offer", net_per_q=1400.0),
        confidence="Medium",
        reason_codes=[],
        caution_flags=["modal_price_proxy"],
        message=Message(
            template_id="wait_with_trigger_offer",
            language="en",
            slots=MessageSlots(
                offer=1400.0,
                days=6,
                mandi="Lasalgaon",
                gain_med=140.0,
                gain_low=50.0,
                gain_high=220.0,
                confidence="Medium",
                target_price=1540.0
            ),
            text=""
        ),
        meta=Meta(as_of=date.today())
    )
    
    formatted = format_advice(response)
    
    assert "Trader offer: Rs 1400.0/quintal" in formatted
    assert "Hold 6 days" in formatted
    assert "Lasalgaon" in formatted
    assert "gain Rs 140.0/quintal" in formatted
    assert "target_price" not in formatted # Just to be sure the literal placeholder isn't there
    assert "Rs 1540.0" in formatted
    assert "Based on market (modal) prices" in formatted # Footer was appended

def test_format_advice_missing_template():
    response = AdviceResponse(
        status="ACCEPT_OFFER",
        reference=ReferenceStatus(type="trader_offer", net_per_q=1400.0),
        confidence="Medium",
        reason_codes=[],
        message=Message(
            template_id="unknown_template",
            language="en",
            slots=MessageSlots(),
            text=""
        ),
        meta=Meta(as_of=date.today())
    )
    formatted = format_advice(response)
    assert "Error: Template unknown_template not found." in formatted
