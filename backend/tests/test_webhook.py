import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from backend.main import app
from backend.schemas import ParsedRequest

# Set bypass for Twilio signature validation during tests by default
os.environ["TWILIO_VALIDATION_ENABLED"] = "false"

client = TestClient(app)

@patch("backend.main.send_whatsapp_reply")
@patch("backend.main.parse_request")
def test_webhook_text_message(mock_parse, mock_send):
    # Mock parser output
    mock_parse.return_value = ParsedRequest(
        crop="onion",
        quantity=25,
        unit="quintal",
        village_text="Niphad",
        trader_offer_per_q=1400,
        language="mr"
    )
    
    response = client.post(
        "/webhook",
        data={"Body": "Majhyakade 25 quintal kanda ahe, Niphad madhe. Vapari 1400 deto ahe", "From": "whatsapp:+1234567890", "To": "whatsapp:+0987654321", "NumMedia": "0"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/xml"
    
    # Check XML formatting and content
    xml = response.text
    assert "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" in xml
    assert "<Response></Response>" in xml
    
    # The formatter should produce this with our mock engine values and pass it to send_whatsapp_reply
    mock_send.assert_called_once()
    args, _ = mock_send.call_args
    assert args[0] == "whatsapp:+1234567890" # sender
    assert args[1] == "whatsapp:+0987654321" # twilio_number
    assert "1400.0" in args[2] # reply_text
    assert "6" in args[2] # reply_text
    
@patch("backend.main.download_twilio_media", new_callable=AsyncMock)
@patch("backend.main.convert_to_wav")
@patch("backend.main.call_sarvam_stt", new_callable=AsyncMock)
@patch("backend.main.send_whatsapp_reply")
@patch("backend.main.parse_request")
@patch("backend.main.format_advice")
def test_webhook_media_message(mock_format, mock_parse, mock_send, mock_stt, mock_convert, mock_dl):
    # Setup mocks to succeed
    mock_dl.return_value = True
    mock_convert.return_value = True
    mock_stt.return_value = ("Majhyakade 25 quintal kanda ahe", "mr-IN")
    
    # Process text mocks
    mock_parse.return_value = ParsedRequest(
        crop="onion", quantity=25, unit="quintal", village_text="Unknown",
        trader_offer_per_q=None, language="mr"
    )
    mock_format.return_value = "Mocked voice reply"
    
    response = client.post(
        "/webhook",
        data={
            "Body": "",
            "From": "whatsapp:+1234567890",
            "To": "whatsapp:+0987654321",
            "NumMedia": "1",
            "MediaContentType0": "audio/ogg",
            "MediaUrl0": "http://example.com/audio"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 200
    mock_dl.assert_called_once()
    mock_convert.assert_called_once()
    mock_stt.assert_called_once()
    mock_parse.assert_called_once_with("Majhyakade 25 quintal kanda ahe")
    mock_format.assert_called_once()
    mock_send.assert_called_once()
    args, _ = mock_send.call_args
    assert "Mocked voice reply" in args[2]

@patch("backend.main.send_whatsapp_reply")
def test_webhook_empty_message(mock_send):
    response = client.post(
        "/webhook",
        data={"Body": "   ", "From": "whatsapp:+1234567890", "To": "whatsapp:+0987654321", "NumMedia": "0"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 200
    mock_send.assert_called_once()
    args, _ = mock_send.call_args
    assert "Please send a text message or a voice note." in args[2]

@patch("backend.main.send_whatsapp_reply")
@patch("backend.main.parse_request")
def test_webhook_parser_error(mock_parse, mock_send):
    mock_parse.side_effect = ValueError("LLM returned invalid JSON")
    
    response = client.post(
        "/webhook",
        data={"Body": "Majhyakade kanda ahe pan samajhna", "From": "whatsapp:+1234567890", "To": "whatsapp:+0987654321", "NumMedia": "0"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 200
    mock_send.assert_called_once()
    args, _ = mock_send.call_args
    assert "Sorry, I couldn't understand that properly." in args[2]

def test_webhook_validation_on():
    # Temporarily enable validation
    os.environ["TWILIO_VALIDATION_ENABLED"] = "true"
    
    response = client.post(
        "/webhook",
        data={"Body": "test", "From": "whatsapp:+1234567890", "NumMedia": "0"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    # Should reject the unsigned request
    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid Twilio signature"
    
    # Restore bypass for other tests
    os.environ["TWILIO_VALIDATION_ENABLED"] = "false"

def test_webhook_validation_default_on():
    # Remove env var to test default
    if "TWILIO_VALIDATION_ENABLED" in os.environ:
        del os.environ["TWILIO_VALIDATION_ENABLED"]
        
    response = client.post(
        "/webhook",
        data={"Body": "test default on", "From": "whatsapp:+1234567890", "NumMedia": "0"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    # Should reject because default is ON
    assert response.status_code == 403
    
    # Restore bypass
    os.environ["TWILIO_VALIDATION_ENABLED"] = "false"

@patch("backend.main.download_twilio_media", new_callable=AsyncMock)
@patch("backend.main.convert_to_wav")
@patch("backend.main.call_sarvam_stt", new_callable=AsyncMock)
@patch("backend.main.send_whatsapp_reply")
@patch("backend.main.parse_request")
@patch("backend.main.format_advice")
def test_webhook_media_oos_hindi(mock_format, mock_parse, mock_send, mock_stt, mock_convert, mock_dl):
    mock_dl.return_value = True
    mock_convert.return_value = True
    mock_stt.return_value = ("मुझे Python में valid parentheses का code लिखकर दो", "hi-IN")
    
    mock_parse.return_value = ParsedRequest(
        crop=None, quantity=None, unit=None, village_text=None,
        trader_offer_per_q=None, language="hi"
    )
    
    response = client.post(
        "/webhook",
        data={
            "Body": "",
            "From": "whatsapp:+1234567890",
            "To": "whatsapp:+0987654321",
            "NumMedia": "1",
            "MediaContentType0": "audio/ogg",
            "MediaUrl0": "http://example.com/audio"
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == 200
    mock_parse.assert_called_once()
    mock_format.assert_not_called()
    mock_send.assert_called_once()
    args, _ = mock_send.call_args
    assert "मैं केवल फसल बिक्री" in args[2]

