import os
from twilio.request_validator import RequestValidator
from fastapi import Request

def validate_twilio_request(request: Request, body: bytes) -> bool:
    """
    Validates that the incoming request is actually from Twilio.
    Default behavior is ENABLED. Can be bypassed during local manual testing
    by setting TWILIO_VALIDATION_ENABLED=false in the environment.
    This bypass is ONLY for local development testing.
    """
    validation_enabled = os.getenv("TWILIO_VALIDATION_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    
    if not validation_enabled:
        return True
        
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not auth_token:
        # If token is not set, we can't validate. Fails closed.
        return False
        
    validator = RequestValidator(auth_token)
    
    # URL that Twilio accessed. (In production behind ngrok, you might need to handle X-Forwarded headers properly, but for this hackathon we take the base URL from the request)
    # Reconstruct the URL using forwarded headers if present
    forwarded_proto = request.headers.get("X-Forwarded-Proto")
    forwarded_host = request.headers.get("X-Forwarded-Host")
    
    if forwarded_proto and forwarded_host:
        url = f"{forwarded_proto}://{forwarded_host}{request.url.path}"
    else:
        url = str(request.url)
        
    # Twilio signature
    signature = request.headers.get("X-Twilio-Signature", "")
    
    # Parse the form data
    from urllib.parse import parse_qsl
    post_vars = dict(parse_qsl(body.decode('utf-8')))
    
    return validator.validate(url, post_vars, signature)
