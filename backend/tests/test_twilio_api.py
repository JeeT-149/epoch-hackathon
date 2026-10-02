import os
import json
import pytest
from unittest.mock import patch, MagicMock
from twilio.base.exceptions import TwilioRestException
from backend.twilio_api import send_whatsapp_reply

@pytest.fixture
def mock_env():
    # Setup test environment variables
    os.environ["TWILIO_ACCOUNT_SID"] = "test_account_sid"
    os.environ["TWILIO_AUTH_TOKEN"] = "test_auth_token"
    yield
    # Cleanup
    for key in ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_USE_TEMPLATE", "TWILIO_CONTENT_SID"]:
        if key in os.environ:
            del os.environ[key]

@patch("backend.twilio_api.Client")
def test_trial_template_mode(mock_client_class, mock_env):
    os.environ["TWILIO_USE_TEMPLATE"] = "true"
    os.environ["TWILIO_CONTENT_SID"] = "HX1234567890abcdef"
    
    mock_client = mock_client_class.return_value
    mock_messages = mock_client.messages
    mock_create = mock_messages.create
    mock_create.return_value = MagicMock(sid="SM12345")
    
    sid = send_whatsapp_reply("whatsapp:+12345", "whatsapp:+54321", "Test reply")
    
    assert sid == "SM12345"
    mock_create.assert_called_once_with(
        from_="whatsapp:+54321",
        to="whatsapp:+12345",
        content_sid="HX1234567890abcdef",
        content_variables=json.dumps({"1": "Test reply"})
    )

@patch("backend.twilio_api.Client")
def test_paid_body_mode(mock_client_class, mock_env):
    os.environ["TWILIO_USE_TEMPLATE"] = "false"
    
    mock_client = mock_client_class.return_value
    mock_messages = mock_client.messages
    mock_create = mock_messages.create
    mock_create.return_value = MagicMock(sid="SM98765")
    
    sid = send_whatsapp_reply("whatsapp:+12345", "whatsapp:+54321", "Test reply")
    
    assert sid == "SM98765"
    mock_create.assert_called_once_with(
        body="Test reply",
        from_="whatsapp:+54321",
        to="whatsapp:+12345"
    )

@patch("backend.twilio_api.Client")
def test_21654_handled_cleanly(mock_client_class, mock_env, capsys):
    os.environ["TWILIO_USE_TEMPLATE"] = "false"
    
    mock_client = mock_client_class.return_value
    mock_messages = mock_client.messages
    mock_create = mock_messages.create
    
    # Simulate error 21654
    error = TwilioRestException(400, "https://twilio.com", "ContentSid Required", code=21654)
    mock_create.side_effect = error
    
    sid = send_whatsapp_reply("whatsapp:+12345", "whatsapp:+54321", "Test reply")
    
    assert sid is None
    
    captured = capsys.readouterr()
    assert "Twilio trial requires ContentSid" in captured.out
    # Ensure no secrets logged
    assert "test_account_sid" not in captured.out
    assert "test_auth_token" not in captured.out
