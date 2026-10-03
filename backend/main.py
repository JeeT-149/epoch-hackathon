import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv


# Explicitly load backend/.env so variables like TWILIO_VALIDATION_ENABLED are read correctly
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

print(f"DEBUG: TWILIO_VALIDATION_ENABLED is currently seen as: {os.getenv('TWILIO_VALIDATION_ENABLED', 'true (default)')}")
print(f"Effective GROQ model: {os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b')}")

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
import httpx
from typing import Dict
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field
import uvicorn
from .schemas import AdviceRequest, AdviceResponse
from .mock_engine import mock_decision_engine

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
from .twilio_utils import validate_twilio_request
import traceback

from .scope_guard import is_in_scope

from .twilio_api import send_whatsapp_reply
from .telegram_api import send_telegram_message

def normalize_language_code(lang_code: str) -> str:
    if not lang_code:
        return "en"
    lang = lang_code.lower()
    if lang.startswith("mr"):
        return "mr"
    if lang.startswith("hi"):
        return "hi"
    return "en"

def get_oos_message(lang_code: str) -> str:
    if lang_code == "mr":
        return "मी फक्त शेतमाल विक्री, बाजारभाव, पीक, प्रमाण, गाव/मंडी, व्यापाऱ्याची ऑफर, साठवण आणि विक्रीच्या निर्णयाशी संबंधित मदत करू शकतो."
    elif lang_code == "hi":
        return "मैं केवल फसल बिक्री, मंडी भाव, मात्रा, गाँव/मंडी, व्यापारी की ऑफर, भंडारण और बिक्री के फैसले से जुड़ी मदद कर सकता हूँ।"
    else:
        return "I can only help with crop selling, market prices, quantity, village/mandi, trader offers, storage, and selling decisions."


def process_text_message(incoming_msg: str, detected_lang: str = "en") -> str:
    if not incoming_msg:
        return "Please send a text message or a voice note."
        
    oos_msg = get_oos_message(detected_lang)
        
    if not is_in_scope(incoming_msg):
        print("PIPELINE: Out of scope request blocked")
        return oos_msg
        
    try:
        print("PIPELINE: starting parser")
        parsed = parse_request(incoming_msg)
        print("PIPELINE: parser completed")
        
        # Post-parse safety check for agricultural intent
        if not (parsed.crop or parsed.quantity or parsed.village_text or parsed.trader_offer_per_q):
            print("PIPELINE: Out of scope request blocked (post-parse)")
            return get_oos_message(normalize_language_code(parsed.language or detected_lang))
        
        print("PIPELINE: scope check passed")
        
        final_lang = normalize_language_code(parsed.language or detected_lang)
        
        advice_req = AdviceRequest(
            crop=parsed.crop or "onion",
            quantity_q=parsed.quantity or 1.0,
            village={"text": parsed.village_text or "Unknown"},
            cash_deadline_days=parsed.cash_deadline_days or 7,
            trader_offer_per_q=parsed.trader_offer_per_q,
            language=final_lang
        )
        
        print("PIPELINE: mock engine started")
        decision = mock_decision_engine(advice_req)
        print("PIPELINE: decision completed")
        
        print("PIPELINE: formatter started")
        reply_text = format_advice(decision)
        print("PIPELINE: response generated")
        return reply_text
        
    except ValueError as e:
        print("PIPELINE ERROR at parsing/validation:")
        traceback.print_exc()
        return "Sorry, I couldn't understand that properly. Could you please specify crop, quantity, and your location?"
    except Exception as e:
        print("PIPELINE ERROR (unexpected):")
        traceback.print_exc()
        return "Sorry, an internal error occurred while processing your request."

from fastapi import Header
import tempfile
from .voice import download_twilio_media, download_telegram_media, convert_to_wav, call_sarvam_stt

@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(None)
):
    print("TELEGRAM WEBHOOK: received request")
    
    expected_secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
    if not expected_secret or x_telegram_bot_api_secret_token != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid Telegram secret token")
        
    update = await request.json()
    message = update.get("message")
    
    if not message:
        return {"status": "ignored"}
        
    chat_id = message.get("chat", {}).get("id")
    if not chat_id:
        return {"status": "ignored"}
        
    reply_text = None
    
    if "voice" in message:
        print("VOICE: media detected")
        # Check duration if available
        duration = message["voice"].get("duration", 0)
        if duration > 30:
            reply_text = "Sorry, please send a voice note under 30 seconds."
        else:
            file_id = message["voice"].get("file_id")
            if not file_id:
                reply_text = "Sorry, couldn't process the audio."
            else:
                with tempfile.TemporaryDirectory() as tmpdir:
                    input_path = os.path.join(tmpdir, "input.ogg")
                    wav_path = os.path.join(tmpdir, "output.wav")
                    
                    dl_success = await download_telegram_media(file_id, input_path)
                    if dl_success:
                        conv_success = convert_to_wav(input_path, wav_path)
                        if conv_success:
                            transcript, lang_code = await call_sarvam_stt(wav_path, "unknown")
                            if transcript:
                                final_lang = normalize_language_code(lang_code)
                                reply_text = process_text_message(transcript, detected_lang=final_lang)
                            else:
                                reply_text = "Sorry, I couldn't understand the audio. Please try speaking again or send a text message."
                        else:
                            reply_text = "Sorry, there was an issue processing your audio format."
                    else:
                        reply_text = "Sorry, there was an issue downloading your voice note."
                        
    elif "text" in message:
        incoming_msg = message.get("text", "").strip()
        if not incoming_msg:
            return {"status": "ignored"}
        reply_text = process_text_message(incoming_msg)
        
    if reply_text:
        print("VOICE: reply sent")
        await send_telegram_message(chat_id, reply_text)
    
    return {"status": "ok"}

@app.post("/webhook")
async def twilio_webhook(request: Request):
    print("WEBHOOK: received request")
    body_bytes = await request.body()
    if not validate_twilio_request(request, body_bytes):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
        
    form_data = await request.form()
    
    incoming_msg = form_data.get("Body", "").strip()
    sender = form_data.get("From", "")
    twilio_number = form_data.get("To", "")
    num_media = int(form_data.get("NumMedia", 0))
    print("WEBHOOK: body extracted")
    
    reply_text = None
    
    if num_media > 0:
        print("VOICE: media detected")
        media_content_type = form_data.get("MediaContentType0", "")
        media_url = form_data.get("MediaUrl0", "")
        
        if not media_content_type.startswith("audio/"):
            reply_text = "Please send a text message or an audio voice note."
        elif not media_url:
            reply_text = "Sorry, couldn't process the audio URL."
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                input_path = os.path.join(tmpdir, "input.media")
                wav_path = os.path.join(tmpdir, "output.wav")
                
                dl_success = await download_twilio_media(media_url, input_path)
                if dl_success:
                    conv_success = convert_to_wav(input_path, wav_path)
                    if conv_success:
                        transcript, lang_code = await call_sarvam_stt(wav_path, "unknown")
                        if transcript:
                            final_lang = normalize_language_code(lang_code)
                            reply_text = process_text_message(transcript, detected_lang=final_lang)
                        else:
                            reply_text = "Sorry, I couldn't understand the audio. Please try speaking again or send a text message."
                    else:
                        reply_text = "Sorry, there was an issue processing your audio format."
                else:
                    reply_text = "Sorry, there was an issue downloading your voice note."
    elif not incoming_msg:
        reply_text = "Please send a text message or a voice note."
    else:
        reply_text = process_text_message(incoming_msg)
            
    # Send via Twilio Messages API for Trial environment
    if reply_text:
        print("VOICE: reply sent")
        send_whatsapp_reply(sender, twilio_number, reply_text)
    
    # Return empty TwiML so Twilio doesn't error out on the webhook
    xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response></Response>"""
    print("WEBHOOK: empty TwiML generated to close connection")

    return Response(
        content=xml_response,
        media_type="application/xml"
    )

@app.post("/v1/advice", response_model=AdviceResponse)
async def advice_endpoint(request: AdviceRequest, api_key: str = Depends(get_api_key)):
    # Call the mock decision engine
    return mock_decision_engine(request)
    incoming_msg = form_data.get("Body", "")
    sender = form_data.get("From", "")
    print(f"Received from {sender}: {incoming_msg}")
    return {"status": "success"}


class CropAnalysisRequest(BaseModel):
    image_data: str
    crop: str = "onion"
    language: str = "en"


def _language_name(code: str) -> str:
    return {"mr": "Marathi", "hi": "Hindi", "en": "English"}.get(code, "English")


@app.post("/analyze-crop")
async def analyze_crop(payload: CropAnalysisRequest) -> dict:
    """Analyze a crop photo without exposing the Groq key to the browser."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY is not configured on the server")
    if not payload.image_data.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="Please upload an image")
    if len(payload.image_data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image is too large")

    language = _language_name(payload.language)
    prompt = f"""You are a careful agricultural assistant. Inspect this photo of {payload.crop}.
Return only a JSON object with these keys: crop_name, ripeness, damage, sell_timing, price_range, confidence, notes.
Write every value in {language}. Keep it simple for a small farmer.
Describe visible ripeness and damage conservatively. Do not claim certainty from a photo.
For price_range, say 'not available from photo' unless a price range is supplied by a market-data system.
For sell_timing, give a practical suggestion based only on visible condition, such as 'sell now', 'sell within 1-2 days', or 'can wait'.
Use confidence as HIGH, MEDIUM, or LOW. Mention that the photo cannot replace an in-person quality check in notes."""
    request_body = {
        "model": os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.8-27b"),
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": payload.image_data}},
        ]}],
        "temperature": 0.2,
        "max_completion_tokens": 600,
        "response_format": {"type": "json_object"},
    }
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=request_body,
            )
        if response.is_error:
            try:
                groq_detail = response.json().get("error", {}).get("message", response.text)
            except json.JSONDecodeError:
                groq_detail = response.text
            raise HTTPException(status_code=502, detail=f"Groq rejected the photo request: {groq_detail}")
        content = response.json()["choices"][0]["message"]["content"]
        match = re.search(r"\{.*\}", content, re.DOTALL)
        result = json.loads(match.group(0) if match else content)
        if not isinstance(result, dict):
            raise ValueError("Groq returned JSON in an unexpected shape")
        result["source"] = "Groq vision"
        return result
    except HTTPException:
        raise
    except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"Crop analysis failed: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Crop analysis service error: {exc}") from exc


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

