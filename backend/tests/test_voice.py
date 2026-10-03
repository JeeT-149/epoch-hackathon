import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from backend.voice import convert_to_wav, download_twilio_media, download_telegram_media, call_sarvam_stt

@patch("subprocess.run")
def test_convert_to_wav_success(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    result = convert_to_wav("input.ogg", "output.wav")
    assert result is True
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    assert "16000" in args[0]
    assert "1" in args[0] # mono
    assert "output.wav" in args[0]

@patch("subprocess.run")
def test_convert_to_wav_failure(mock_run):
    import subprocess
    mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg", stderr="error")
    result = convert_to_wav("input.ogg", "output.wav")
    assert result is False

import asyncio

def test_download_twilio_media_success():
    os.environ["TWILIO_ACCOUNT_SID"] = "sid"
    os.environ["TWILIO_AUTH_TOKEN"] = "token"
    
    async def run_test():
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.content = b"audio_data"
            mock_get.return_value = mock_response
            
            with patch("builtins.open", new_callable=MagicMock) as mock_open:
                result = await download_twilio_media("http://example.com/audio", "output.ogg")
                assert result is True
                mock_get.assert_called_once_with("http://example.com/audio", auth=("sid", "token"))
    asyncio.run(run_test())

def test_download_telegram_media_success():
    os.environ["TELEGRAM_BOT_TOKEN"] = "token"
    
    async def run_test():
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
             patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
             patch("builtins.open", new_callable=MagicMock) as mock_open:
             
            mock_post_response = MagicMock()
            mock_post_response.raise_for_status = MagicMock()
            mock_post_response.json.return_value = {"ok": True, "result": {"file_path": "voice/file.ogg"}}
            mock_post.return_value = mock_post_response
            
            mock_get_response = MagicMock()
            mock_get_response.raise_for_status = MagicMock()
            mock_get_response.content = b"audio_data"
            mock_get.return_value = mock_get_response
            
            result = await download_telegram_media("file123", "output.ogg")
            assert result is True
            mock_post.assert_called_once()
            mock_get.assert_called_once()
    asyncio.run(run_test())

def test_call_sarvam_stt_success():
    os.environ["SARVAM_API_KEY"] = "sarvam_key"
    
    async def run_test():
        with patch("builtins.open", new_callable=MagicMock) as mock_open, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
             
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {"transcript": "Marathi speech here", "language_code": "mr-IN"}
            mock_post.return_value = mock_response
            
            transcript, lang = await call_sarvam_stt("output.wav", "mr-IN")
            assert transcript == "Marathi speech here"
            assert lang == "mr-IN"
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert kwargs["data"]["language_code"] == "mr-IN"
    asyncio.run(run_test())

def test_call_sarvam_stt_empty():
    os.environ["SARVAM_API_KEY"] = "sarvam_key"
    
    async def run_test():
        with patch("builtins.open", new_callable=MagicMock) as mock_open, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
             
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {"transcript": "   "}
            mock_post.return_value = mock_response
            
            transcript, lang = await call_sarvam_stt("output.wav")
            assert transcript is None
            assert lang is None
    asyncio.run(run_test())

def test_call_sarvam_stt_429():
    os.environ["SARVAM_API_KEY"] = "sarvam_key"
    
    async def run_test():
        with patch("builtins.open", new_callable=MagicMock) as mock_open, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
             
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_post.return_value = mock_response
            
            transcript, lang = await call_sarvam_stt("output.wav")
            assert transcript is None
            assert lang is None
    asyncio.run(run_test())
