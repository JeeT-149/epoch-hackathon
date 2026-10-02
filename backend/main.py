from fastapi import FastAPI, Request
from typing import Dict
import uvicorn

app = FastAPI()

@app.post("/webhook")
async def twilio_webhook(request: Request) -> Dict[str, str]:
    form_data = await request.form()

    incoming_msg = form_data.get("Body", "")
    sender = form_data.get("From", "")

    print(f"Received from {sender}: {incoming_msg}")

    return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
