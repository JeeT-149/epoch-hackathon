import os
import json
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

def send_whatsapp_reply(sender: str, twilio_number: str, reply_text: str) -> str | None:
    """
    Sends a WhatsApp message using the Twilio Messages API.
    Supports Mode 1 (Trial) via ContentSid and Mode 2 (Full) via body.
    """
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    use_template = os.environ.get("TWILIO_USE_TEMPLATE", "true").lower() == "true"
    content_sid = os.environ.get("TWILIO_CONTENT_SID")
    
    if not account_sid or not auth_token:
        print("WEBHOOK ERROR: Twilio credentials not found in environment.")
        return None

    try:
        client = Client(account_sid, auth_token)
        print("WEBHOOK: sending WhatsApp reply via Twilio API")
        
        if use_template:
            if not content_sid:
                print("WEBHOOK TWILIO API ERROR: Trial mode enabled but TWILIO_CONTENT_SID is not set.")
                return None
                
            # Mode 1: Twilio Trial
            # Assuming the template accepts a single variable '1' for the text. 
            # This should match the variables supported by the exact template in Twilio.
            message = client.messages.create(
                from_=twilio_number,
                to=sender,
                content_sid=content_sid,
                content_variables=json.dumps({"1": reply_text})
            )
        else:
            # Mode 2: Full / Paid Account
            message = client.messages.create(
                body=reply_text,
                from_=twilio_number,
                to=sender
            )
        
        print(f"WEBHOOK: Twilio message SID: {message.sid}")
        print("WEBHOOK: WhatsApp reply submitted")
        return message.sid
        
    except TwilioRestException as e:
        if e.code == 21654:
            print("WEBHOOK TWILIO API ERROR: Twilio trial requires ContentSid. Please configure TWILIO_USE_TEMPLATE=true and set a valid TWILIO_CONTENT_SID.")
        else:
            print(f"WEBHOOK TWILIO API ERROR:")
            print(f"Status Code: {e.status}")
            print(f"Code: {e.code}")
            print(f"Message: {e.msg}")
        return None
    except Exception as e:
        print(f"WEBHOOK UNEXPECTED TWILIO ERROR:")
        print(f"Type: {type(e)}")
        print(f"Message: {str(e)}")
        return None
