from __future__ import annotations

import os
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# ============================================================
# Environment
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
ENV_PATH = BACKEND_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=True)

print(
    "DEBUG: TWILIO_VALIDATION_ENABLED:",
    os.getenv("TWILIO_VALIDATION_ENABLED", "true (default)"),
)
print(
    "Effective GROQ model:",
    os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
)

# ============================================================
# FastAPI / Pydantic
# ============================================================

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.security import APIKeyHeader
from typing import Dict
import uvicorn
from .schemas import AdviceRequest, AdviceResponse
from .mock_engine import mock_decision_engine

app = FastAPI()

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key(api_key_header: str = Depends(api_key_header)):
    expected_api_key = os.getenv("SELLSMART_API_KEY", "epoch_demo_secret_2026")
    if api_key_header != expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Could not validate credentials"
        )
    return api_key_header

from fastapi import Response
from xml.sax.saxutils import escape
from .parser import parse_request
from .formatter import format_advice
from .scope_guard import is_in_scope
from .twilio_utils import validate_twilio_request
from .twilio_api import send_whatsapp_reply
from .telegram_api import send_telegram_message
from .voice import (
    call_sarvam_stt,
    convert_to_wav,
    download_telegram_media,
    download_twilio_media,
)

from xml.sax.saxutils import escape

# ============================================================
# Optional real ML engine integration
# ============================================================

# Friend's ML project is expected at:
#     <project-root>/src/sellsmart/
#
# The fallback path supports the older structure that appeared in
# the merge-conflict branch:
#     <project-root>/sell_smart/src/sellsmart/
#
# IMPORTANT:
# We only IMPORT it here. We do not modify any ML files.

ML_SRC_CANDIDATES = [
    PROJECT_ROOT / "src",
    PROJECT_ROOT / "sell_smart" / "src",
]

SELL_SMART_SRC: Optional[Path] = None

for candidate in ML_SRC_CANDIDATES:
    if candidate.exists():
        SELL_SMART_SRC = candidate
        break

if SELL_SMART_SRC is not None:
    src_string = str(SELL_SMART_SRC)
    if src_string not in sys.path:
        sys.path.insert(0, src_string)

try:
    from sellsmart.service.api import AdviceService

    advice_service: Optional[AdviceService] = AdviceService()
    REAL_ML_AVAILABLE = True
    print(f"ML: AdviceService available from {SELL_SMART_SRC}")

except Exception as exc:
    advice_service = None
    REAL_ML_AVAILABLE = False

    print("ML: AdviceService unavailable; mock engine remains available.")
    print(f"ML import reason: {type(exc).__name__}: {exc}")


ML_MODE = os.getenv("ML_MODE", "mock").strip().lower()

if ML_MODE not in {"mock", "live"}:
    print(f"ML: invalid ML_MODE={ML_MODE!r}; defaulting to mock.")
    ML_MODE = "mock"


# ============================================================
# FastAPI application
# ============================================================

app = FastAPI(
    title="Sell Smart Decision Intelligence API",
    description="APMC mandi decision support and trigger intelligence engine.",
    version="1.0.0",
)


# ============================================================
# Health
# ============================================================

@app.get("/health")
def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "sell_smart",
        "ml_mode": ML_MODE,
        "real_ml_available": REAL_ML_AVAILABLE,
        "provenance": {
            "soybean": {
                "price_source": "real",
                "is_synthetic": False,
            },
            "onion": {
                "price_source": "synthetic",
                "is_synthetic": True,
            },
            "tomato": {
                "price_source": "synthetic",
                "is_synthetic": True,
            },
        },
        "governance_rule": (
            "Headline Rs claims allowed only for crops with real prices "
            "(ADR-001)"
        ),
    }


# ============================================================
# API Key
# ============================================================

API_KEY_NAME = "X-API-Key"

api_key_header = APIKeyHeader(
    name=API_KEY_NAME,
    auto_error=False,
)


def get_api_key(
    api_key: Optional[str] = Depends(api_key_header),
) -> str:
    expected_api_key = os.getenv(
        "SELLSMART_API_KEY",
        "epoch_demo_secret_2026",
    )

    if api_key != expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    return api_key


# ============================================================
# Decision engine abstraction
# ============================================================

def run_decision_engine(req: AdviceRequest) -> AdviceResponse:
    """
    Choose between the friend's real ML engine and the existing
    deterministic mock engine.

    ML_MODE=mock:
        existing mock_decision_engine

    ML_MODE=live:
        friend's AdviceService
    """

    if ML_MODE == "live":
        if advice_service is None:
            raise HTTPException(
                status_code=503,
                detail="Real ML engine is unavailable.",
            )

        try:
            response = advice_service.get_advice(
                crop=req.crop,
                quantity_q=req.quantity_q,
                village_text=req.village.text if req.village else "",
                village_lat=req.village.lat if req.village else None,
                village_lon=req.village.lon if req.village else None,
                cash_deadline_days=req.cash_deadline_days,
                trader_offer_per_q=req.trader_offer_per_q,
                storage_available=req.storage_available,
                storage_condition=req.storage_condition,
                quality_factor=req.quality_factor,
                as_of=req.as_of,
                language=req.language,
            )

            # Validate friend's output against our canonical contract.
            return AdviceResponse.model_validate(response)

        except HTTPException:
            raise

        except Exception as exc:
            print("ML: real AdviceService failed")
            traceback.print_exc()

            raise HTTPException(
                status_code=502,
                detail="Real ML decision engine failed.",
            ) from exc

    # Default / demo mode.
    return mock_decision_engine(req)


# ============================================================
# Structured advice API
# ============================================================

@app.post(
    "/v1/advice",
    response_model=AdviceResponse,
)
def advice_endpoint(
    req: AdviceRequest,
    _: str = Depends(get_api_key),
) -> AdviceResponse:
    """
    Main structured decision endpoint.

    Uses:
        ML_MODE=mock  -> deterministic mock engine
        ML_MODE=live  -> friend's AdviceService
    """

    return run_decision_engine(req)


# ============================================================
# Language utilities
# ============================================================

def normalize_language_code(lang_code: Optional[str]) -> str:
    if not lang_code:
        return "en"

    lang = lang_code.strip().lower()

    if lang.startswith("mr"):
        return "mr"

    if lang.startswith("hi"):
        return "hi"

    if lang.startswith("en"):
        return "en"

    return "en"


def get_oos_message(lang_code: str) -> str:
    lang = normalize_language_code(lang_code)

    if lang == "mr":
        return (
            "मी फक्त शेतमाल विक्री, बाजारभाव, पीक, प्रमाण, गाव/मंडी, "
            "व्यापाऱ्याची ऑफर, साठवण आणि विक्रीच्या निर्णयाशी संबंधित "
            "मदत करू शकतो."
        )

    if lang == "hi":
        return (
            "मैं केवल फसल बिक्री, मंडी भाव, मात्रा, गाँव/मंडी, "
            "व्यापारी की ऑफर, भंडारण और बिक्री के फैसले से जुड़ी "
            "मदद कर सकता हूँ।"
        )

    return (
        "I can only help with crop selling, market prices, quantity, "
        "village/mandi, trader offers, storage, and selling decisions."
    )


# ============================================================
# Shared text processing pipeline
# ============================================================

def process_text_message(
    incoming_msg: str,
    detected_lang: str = "en",
) -> str:
    if not incoming_msg or not incoming_msg.strip():
        return "Please send a text message or a voice note."

    incoming_msg = incoming_msg.strip()

    # --------------------------------------------------------
    # Layer 1: deterministic domain gate
    # --------------------------------------------------------

    if not is_in_scope(incoming_msg):
        print("PIPELINE: Out of scope request blocked")
        return get_oos_message(detected_lang)

    try:
        # ----------------------------------------------------
        # Layer 2: parser
        # ----------------------------------------------------

        print("PIPELINE: starting parser")

        parsed = parse_request(incoming_msg)

        print("PIPELINE: parser completed")
        print("PIPELINE: ParsedRequest validated")

        # ----------------------------------------------------
        # Layer 3: post-parser safety check
        # ----------------------------------------------------

        if not (
            parsed.crop
            or parsed.quantity
            or parsed.village_text
            or parsed.trader_offer_per_q
        ):
            print(
                "PIPELINE: Out of scope request blocked "
                "(post-parse)"
            )

            return get_oos_message(
                normalize_language_code(
                    parsed.language or detected_lang
                )
            )

        print("PIPELINE: scope check passed")

        final_lang = normalize_language_code(
            parsed.language or detected_lang
        )

        # ----------------------------------------------------
        # Convert parser result → canonical AdviceRequest
        # ----------------------------------------------------

        advice_req = AdviceRequest(
            crop=parsed.crop or "onion",
            quantity_q=parsed.quantity or 1.0,
            village={
                "text": parsed.village_text or "Unknown"
            },
            cash_deadline_days=(
                parsed.cash_deadline_days
                if parsed.cash_deadline_days is not None
                else 7
            ),
            trader_offer_per_q=parsed.trader_offer_per_q,
            language=final_lang,
        )

        print(
            f"PIPELINE: decision engine started "
            f"(mode={ML_MODE})"
        )

        # ----------------------------------------------------
        # ML decision
        # ----------------------------------------------------

        decision = run_decision_engine(advice_req)

        print("PIPELINE: decision completed")

        # ----------------------------------------------------
        # Deterministic formatter
        # ----------------------------------------------------

        print("PIPELINE: formatter started")

        reply_text = format_advice(decision)

        print("PIPELINE: response generated")

        return reply_text

    except ValueError:
        print("PIPELINE ERROR at parsing/validation:")
        traceback.print_exc()

        return (
            "Sorry, I couldn't understand that properly. "
            "Could you please specify crop, quantity, and your location?"
        )

    except HTTPException:
        raise

    except Exception:
        print("PIPELINE ERROR (unexpected):")
        traceback.print_exc()

        return (
            "Sorry, an internal error occurred while "
            "processing your request."
        )


# ============================================================
# Telegram webhook
# ============================================================

@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(
        default=None
    ),
):
    print("TELEGRAM WEBHOOK: received request")

    expected_secret = os.getenv(
        "TELEGRAM_WEBHOOK_SECRET"
    )

    if (
        not expected_secret
        or x_telegram_bot_api_secret_token != expected_secret
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid Telegram secret token",
        )

    update = await request.json()
    message = update.get("message")

    if not message:
        return {"status": "ignored"}

    chat_id = message.get("chat", {}).get("id")

    if not chat_id:
        return {"status": "ignored"}

    reply_text: Optional[str] = None

    # ========================================================
    # Telegram voice
    # ========================================================

    if "voice" in message:
        print("VOICE: media detected")

        duration = message["voice"].get("duration", 0)

        if duration > 30:
            reply_text = (
                "Sorry, please send a voice note under "
                "30 seconds."
            )

        else:
            file_id = message["voice"].get("file_id")

            if not file_id:
                reply_text = "Sorry, couldn't process the audio."

            else:
                with tempfile.TemporaryDirectory() as tmpdir:
                    input_path = os.path.join(
                        tmpdir,
                        "input.ogg",
                    )

                    wav_path = os.path.join(
                        tmpdir,
                        "output.wav",
                    )

                    dl_success = await download_telegram_media(
                        file_id,
                        input_path,
                    )

                    if not dl_success:
                        reply_text = (
                            "Sorry, there was an issue "
                            "downloading your voice note."
                        )

                    else:
                        conv_success = convert_to_wav(
                            input_path,
                            wav_path,
                        )

                        if not conv_success:
                            reply_text = (
                                "Sorry, there was an issue "
                                "processing your audio format."
                            )

                        else:
                            transcript, lang_code = (
                                await call_sarvam_stt(
                                    wav_path,
                                    "unknown",
                                )
                            )

                            if not transcript:
                                reply_text = (
                                    "Sorry, I couldn't understand "
                                    "the audio. Please try speaking "
                                    "again or send a text message."
                                )

                            else:
                                print(
                                    f"VOICE: transcript = "
                                    f"{transcript}"
                                )

                                final_lang = (
                                    normalize_language_code(
                                        lang_code
                                    )
                                )

                                reply_text = process_text_message(
                                    transcript,
                                    detected_lang=final_lang,
                                )

    # ========================================================
    # Telegram text
    # ========================================================

    elif "text" in message:
        incoming_msg = (
            message.get("text", "").strip()
        )

        if not incoming_msg:
            return {"status": "ignored"}

        reply_text = process_text_message(
            incoming_msg,
            detected_lang="en",
        )

    # ========================================================
    # Send Telegram reply
    # ========================================================

    if reply_text:
        print("TELEGRAM: sending reply")

        await send_telegram_message(
            chat_id,
            reply_text,
        )

        print("TELEGRAM: reply sent")

    return {"status": "ok"}


# ============================================================
# Twilio webhook
# ============================================================

@app.post("/webhook")
async def twilio_webhook(
    request: Request,
):
    print("WEBHOOK: received request")

    body_bytes = await request.body()

    if not validate_twilio_request(
        request,
        body_bytes,
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid Twilio signature",
        )

    form_data = await request.form()

    incoming_msg = (
        form_data.get("Body", "").strip()
    )

    sender = form_data.get(
        "From",
        "",
    )

    twilio_number = form_data.get(
        "To",
        "",
    )

    try:
        num_media = int(
            form_data.get("NumMedia", 0)
        )
    except (TypeError, ValueError):
        num_media = 0

    print("WEBHOOK: body extracted")

    reply_text: Optional[str] = None

    # ========================================================
    # Twilio audio
    # ========================================================

    if num_media > 0:
        print("VOICE: media detected")

        media_content_type = (
            form_data.get(
                "MediaContentType0",
                "",
            )
        )

        media_url = form_data.get(
            "MediaUrl0",
            "",
        )

        if not media_content_type.startswith("audio/"):
            reply_text = (
                "Please send a text message or an "
                "audio voice note."
            )

        elif not media_url:
            reply_text = (
                "Sorry, couldn't process the audio URL."
            )

        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                input_path = os.path.join(
                    tmpdir,
                    "input.media",
                )

                wav_path = os.path.join(
                    tmpdir,
                    "output.wav",
                )

                dl_success = await download_twilio_media(
                    media_url,
                    input_path,
                )

                if not dl_success:
                    reply_text = (
                        "Sorry, there was an issue "
                        "downloading your voice note."
                    )

                else:
                    conv_success = convert_to_wav(
                        input_path,
                        wav_path,
                    )

                    if not conv_success:
                        reply_text = (
                            "Sorry, there was an issue "
                            "processing your audio format."
                        )

                    else:
                        transcript, lang_code = (
                            await call_sarvam_stt(
                                wav_path,
                                "unknown",
                            )
                        )

                        if not transcript:
                            reply_text = (
                                "Sorry, I couldn't understand "
                                "the audio. Please try speaking "
                                "again or send a text message."
                            )

                        else:
                            print(
                                f"VOICE: transcript = "
                                f"{transcript}"
                            )

                            final_lang = (
                                normalize_language_code(
                                    lang_code
                                )
                            )

                            reply_text = process_text_message(
                                transcript,
                                detected_lang=final_lang,
                            )

    # ========================================================
    # Twilio text
    # ========================================================

    elif not incoming_msg:
        reply_text = (
            "Please send a text message or a voice note."
        )

    else:
        reply_text = process_text_message(
            incoming_msg,
            detected_lang="en",
        )

    # ========================================================
    # Outbound WhatsApp
    # ========================================================

    if reply_text:
        print("WEBHOOK: sending WhatsApp reply")

        send_whatsapp_reply(
            sender,
            twilio_number,
            reply_text,
        )

        print("WEBHOOK: WhatsApp reply submitted")

    # ========================================================
    # TwiML acknowledgement
    # ========================================================

    xml_response = """<?xml version="1.0" encoding="UTF-8"?>
<Response></Response>"""

    print(
        "WEBHOOK: empty TwiML generated to close connection"
    )

    return Response(
        content=xml_response,
        media_type="application/xml"
    )

@app.post("/v1/advice", response_model=AdviceResponse)
async def advice_endpoint(request: AdviceRequest, api_key: str = Depends(get_api_key)):
    # Call the mock decision engine
    return mock_decision_engine(request)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )