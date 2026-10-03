import os
import httpx

async def send_telegram_message(chat_id: int | str, text: str) -> bool:
    """
    Sends a message to a Telegram chat using the Bot API.
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("TELEGRAM ERROR: TELEGRAM_BOT_TOKEN not configured.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            data = response.json()
            if data.get("ok"):
                print("TELEGRAM: Message sent successfully.")
                return True
            else:
                print(f"TELEGRAM API ERROR: {data}")
                return False
    except Exception as e:
        print(f"TELEGRAM NETWORK ERROR: {e}")
        return False
