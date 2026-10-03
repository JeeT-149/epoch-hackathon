import os
import json
import pytest
from unittest.mock import MagicMock

from backend.parser import parse_request, normalize_crop
from backend.schemas import ParsedRequest

def test_normalize_crop():
    assert normalize_crop("Majhyakade 25 quintal kanda ahe") == "onion"
    assert normalize_crop("mera pyaz bikwa do") == "onion"
    assert normalize_crop("dungri for sale") == "onion"
    assert normalize_crop("mujhe tamatar bechna hai") == "tomato"
    assert normalize_crop("soyabean price kya hai") == "soybean"
    assert normalize_crop("no crop mentioned") is None

def test_parse_request_mocked():
    mock_groq = MagicMock()
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps({
        "crop": None,
        "quantity": 25,
        "unit": "quintal",
        "village_text": "Niphad",
        "trader_offer_per_q": 1400,
        "cash_deadline_days": None,
        "language": "mr",
        "missing_fields": ["cash_deadline_days"],
        "parse_confidence": 0.95
    })
    
    mock_groq.chat.completions.create.return_value = mock_response
    
    text = "Majhyakade 25 quintal kanda ahe, Niphad madhe. Vapari 1400 deto ahe"
    result = parse_request(text, groq_client=mock_groq)
    
    # Assert deterministic override of crop
    assert result.crop == "onion"
    assert result.quantity == 25
    assert result.village_text == "Niphad"
    assert result.trader_offer_per_q == 1400
    assert result.language == "mr"
    
def test_invalid_json():
    mock_groq = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "not json"
    mock_groq.chat.completions.create.return_value = mock_response
    
    with pytest.raises(ValueError, match="LLM returned invalid JSON"):
        parse_request("hello", groq_client=mock_groq)

def test_invalid_schema():
    mock_groq = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    # Missing required fields that might cause schema validation error
    # Actually all fields are optional or have defaults in ParsedRequest, 
    # but let's pass a bad type to force ValidationError
    mock_response.choices[0].message.content = json.dumps({
        "quantity": "twenty-five" # Should be float
    })
    mock_groq.chat.completions.create.return_value = mock_response
    
    with pytest.raises(ValueError, match="failed schema validation"):
        parse_request("hello", groq_client=mock_groq)
