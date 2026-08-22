"""
"Standalone testing harness for end-to-end alert simulation."
"Dispatches synthetic payloads to the FastAPI ingestion endpoint."
"""
import asyncio
import random
import uuid

import httpx

API_URL = "http://localhost:8000/api/v1/webhooks/jira"

async def trigger_synthetic_alert() -> None:
    ticket_id = f"SEC-{random.randint(1000, 9999)}"
    alert_types = ["account_lockout", "impossible_travel"]
    
    payload = {
        "ticket_id": ticket_id,
        "user_email": f"target_{uuid.uuid4().hex[:6]}@company.com",
        "alert_type": random.choice(alert_types)
    }
    
    print(f"Dispatching synthetic alert: {ticket_id} ({payload['alert_type']})")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(API_URL, json=payload, timeout=5.0)
            print(f"Server Response [{response.status_code}]: {response.json()}")
        except Exception as error:  # noqa: BLE001
            print(f"Simulation Failed: {error!s}")

if __name__ == "__main__":
    asyncio.run(trigger_synthetic_alert())