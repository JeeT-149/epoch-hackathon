import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from backend.main import app
from backend.schemas import ParsedRequest

# Ensure TELEGRAM_WEBHOOK_SECRET is set for tests
os.environ["TELEGRAM_WEBHOOK_SECRET"] = "test_secret_123"

client = TestClient(app)

def test_missing_secret_rejected():
    response = client.post(
        "/telegram/webhook",
        json={"message": {"text": "hello", "chat": {"id": 123}}}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid Telegram secret token"

def test_invalid_secret_rejected():
    response = client.post(
        "/telegram/webhook",
        headers={"x-telegram-bot-api-secret-token": "wrong_secret"},
        json={"message": {"text": "hello", "chat": {"id": 123}}}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid Telegram secret token"

def test_missing_message_ignored():
    response = client.post(
        "/telegram/webhook",
        headers={"x-telegram-bot-api-secret-token": "test_secret_123"},
        json={"edited_message": {"text": "hello", "chat": {"id": 123}}}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}

@patch("backend.main.download_telegram_media", new_callable=AsyncMock)
@patch("backend.main.convert_to_wav")
@patch("backend.main.call_sarvam_stt", new_callable=AsyncMock)
@patch("backend.main.send_telegram_message")
@patch("backend.main.parse_request")
@patch("backend.main.format_advice")
def test_voice_update_detected(mock_format, mock_parse, mock_send, mock_stt, mock_convert, mock_dl):
    mock_dl.return_value = True
    mock_convert.return_value = True
    mock_stt.return_value = ("Majhyakade 25 quintal kanda ahe", "mr-IN")
    
    mock_parse.return_value = ParsedRequest(
        crop="onion", quantity=25, unit="quintal", village_text="Unknown",
        trader_offer_per_q=None, language="mr"
    )
    mock_format.return_value = "Mocked voice reply for Telegram"

    response = client.post(
        "/telegram/webhook",
        headers={"x-telegram-bot-api-secret-token": "test_secret_123"},
        json={"message": {"voice": {"file_id": "123", "duration": 15}, "chat": {"id": 456}}}
    )
    assert response.status_code == 200
    mock_dl.assert_called_once()
    mock_convert.assert_called_once()
    mock_stt.assert_called_once()
    mock_parse.assert_called_once_with("Majhyakade 25 quintal kanda ahe")
    mock_format.assert_called_once()
    mock_send.assert_called_once_with(456, "Mocked voice reply for Telegram")

@patch("backend.main.send_telegram_message")
@patch("backend.main.parse_request")
@patch("backend.main.format_advice")
def test_valid_text_update_pipeline(mock_format, mock_parse, mock_send):
    mock_parse.return_value = ParsedRequest(
        crop="onion", quantity=25, unit="quintal", village_text="Niphad",
        trader_offer_per_q=1400, language="mr"
    )
    mock_format.return_value = "Mocked Marathi reply with 1550 rupees."

    response = client.post(
        "/telegram/webhook",
        headers={"x-telegram-bot-api-secret-token": "test_secret_123"},
        json={"message": {"text": "Majhyakade 25 quintal kanda ahe", "chat": {"id": 789}}}
    )
    
    assert response.status_code == 200
    mock_parse.assert_called_once_with("Majhyakade 25 quintal kanda ahe")
    mock_format.assert_called_once()
    mock_send.assert_called_once()
    args, _ = mock_send.call_args
    assert args[0] == 789
    # check that formatter output is sent
    assert "1550" in args[1]

@patch("backend.main.send_telegram_message")
@patch("backend.main.parse_request")
def test_scope_guard_invoked(mock_parse, mock_send):
    response = client.post(
        "/telegram/webhook",
        headers={"x-telegram-bot-api-secret-token": "test_secret_123"},
        json={"message": {"text": "Write Python code for me", "chat": {"id": 999}}}
    )
    
    assert response.status_code == 200
    mock_parse.assert_not_called()
    mock_send.assert_called_once()
    args, _ = mock_send.call_args
    assert "I can only help with crop selling" in args[1]

def test_telegram_api_failure_handled():
    import asyncio
    from backend.telegram_api import send_telegram_message
    
    os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
    # Mock httpx to return ok=False
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": False, "description": "Bad Request"}
        mock_post.return_value = mock_response
        
        result = asyncio.run(send_telegram_message(123, "test"))
        assert result is False
