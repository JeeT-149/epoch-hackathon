import os
import httpx
import subprocess
import json
from typing import Optional, Tuple

def convert_to_wav(input_path: str, output_path: str) -> bool:
    """
    Converts any audio file to 16kHz mono WAV using ffmpeg.
    """
    print("VOICE: ffmpeg conversion started")
    try:
        # ffmpeg -y -i input.ogg -ar 16000 -ac 1 output.wav
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", input_path, "-ar", "16000", "-ac", "1", output_path],
            check=True,
            capture_output=True,
            text=True
        )
        print("VOICE: ffmpeg conversion complete")
        return True
    except subprocess.CalledProcessError as e:
        print(f"VOICE ERROR: ffmpeg failed: {e.stderr}")
        return False
    except FileNotFoundError:
        print("VOICE ERROR: ffmpeg not found in PATH")
        return False

async def download_twilio_media(media_url: str, output_path: str) -> bool:
    """
    Downloads media from Twilio using HTTP Basic Auth.
    """
    print("VOICE: downloading from Twilio")
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    
    if not account_sid or not auth_token:
        print("VOICE ERROR: Missing Twilio credentials for download")
        return False
        
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(media_url, auth=(account_sid, auth_token))
            response.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(response.content)
        print("VOICE: download complete")
        return True
    except Exception as e:
        print(f"VOICE ERROR: Twilio media download failed: {e}")
        return False

async def download_telegram_media(file_id: str, output_path: str) -> bool:
    """
    Downloads media from Telegram using the Bot API.
    """
    print("VOICE: downloading from Telegram")
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    if not bot_token:
        print("VOICE ERROR: Missing Telegram credentials for download")
        return False
        
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # 1. Get file path
            url = f"https://api.telegram.org/bot{bot_token}/getFile"
            resp = await client.post(url, json={"file_id": file_id})
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                print(f"VOICE ERROR: Telegram getFile failed: {data}")
                return False
                
            file_path = data["result"]["file_path"]
            
            # 2. Download file
            download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
            dl_resp = await client.get(download_url)
            dl_resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(dl_resp.content)
                
        print("VOICE: download complete")
        return True
    except Exception as e:
        print(f"VOICE ERROR: Telegram media download failed: {e}")
        return False

async def call_sarvam_stt(wav_path: str, language_code: str = "unknown") -> Tuple[Optional[str], Optional[str]]:
    """
    Calls Sarvam AI STT API with the given WAV file.
    Returns (transcript, language_code).
    """
    print("VOICE: Sarvam STT started")
    sarvam_key = os.environ.get("SARVAM_API_KEY")
    if not sarvam_key:
        print("VOICE ERROR: Missing SARVAM_API_KEY")
        return None, None
        
    url = "https://api.sarvam.ai/speech-to-text"
    headers = {
        "api-subscription-key": sarvam_key
    }
    data = {
        "model": "saaras:v3",
        "mode": "transcribe",
        "language_code": language_code
    }
    
    try:
        with open(wav_path, "rb") as f:
            files = {"file": ("audio.wav", f, "audio/wav")}
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, data=data, files=files)
                
                if response.status_code == 429:
                    print("VOICE ERROR: Sarvam rate limit exceeded")
                    return None, None
                elif response.status_code >= 500:
                    print(f"VOICE ERROR: Sarvam server error {response.status_code}")
                    return None, None
                elif response.status_code >= 400:
                    print(f"VOICE ERROR: Sarvam bad request {response.status_code} - {response.text}")
                    return None, None
                    
                response.raise_for_status()
                
                res_data = response.json()
                transcript = res_data.get("transcript")
                detected_language = res_data.get("language_code")
                
                if not transcript or not str(transcript).strip():
                    print("VOICE ERROR: Sarvam returned empty transcript")
                    return None, None
                    
                transcript_text = str(transcript).strip()
                print(f"VOICE: transcript = {transcript_text[:200]}")
                if detected_language:
                    print(f"VOICE: detected language = {detected_language}")
                print("VOICE: transcript received")
                print("VOICE: Sarvam STT completed")
                return transcript_text, detected_language
    except httpx.ReadTimeout:
        print("VOICE ERROR: Sarvam STT timeout")
        return None, None
    except Exception as e:
        print(f"VOICE ERROR: Sarvam STT failed: {e}")
        return None, None
