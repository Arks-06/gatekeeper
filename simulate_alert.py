"""
"Standalone testing harness for end-to-end alert simulation."
"Dispatches synthetic payloads to the FastAPI ingestion endpoint."
"""

import asyncio
import random
import httpx

API_URL = "http://localhost:8000/api/v1/webhooks/jira"

async def trigger_synthetic_alert(scenario: str, user_email: str, reporter_email: str, alert_type: str) -> None:
    ticket_id = f"SEC-{random.randint(1000, 9999)}"
    
    payload = {
        "ticket_id": ticket_id,
        "user_email": user_email,
        "reporter_email": reporter_email,
        "alert_type": alert_type
    }
    
    print(f"\nDispatching {scenario}: {ticket_id} ({payload['alert_type']})")
    print(f"Target: {user_email} | Reporter: {reporter_email}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(API_URL, json=payload, timeout=5.0)
            print(f"Server Response [{response.status_code}]: {response.json()}")
        except Exception as error:  # noqa: BLE001
            print(f"Simulation Failed: {error!s}")

async def run_tests():
    test_cases = [
        # 1. Authorized self-service (Should pass and remediate)
        ("[AUTHORIZED]", "standard.user@company.com", "standard.user@company.com", "account_lockout"),
        
        # 2. Unauthorized privilege escalation on VIP (Should block via guardrail)
        ("[UNAUTHORIZED VIP]", "ceo@company.com", "intern@company.com", "account_lockout"),
        
        # 3. Phishing report from a standard user (Should pass and quarantine)
        ("[PHISHING]", "sales.rep@company.com", "sales.rep@company.com", "phishing_report"),
        
        # 4. Impossible travel detected by system (Should pass and evaluate risk)
        ("[IMPOSSIBLE TRAVEL]", "remote.worker@company.com", "system_monitor", "impossible_travel"),
        
        # 5. Malware detected by EDR (Should pass and isolate)
        ("[MALWARE]", "developer@company.com", "system_monitor", "malware_detected"),
        
        # 6. Suspicious behavior detected by SIEM (Should route based on score)
        ("[SUSPICIOUS BEHAVIOR]", "contractor@company.com", "system_monitor", "suspicious_behavior"),
        
        # 7. Mass download detected by DLP (Should route based on score)
        ("[MASS DOWNLOAD]", "departing.employee@company.com", "system_monitor", "mass_download")
    ]

    for scenario, user, reporter, alert in test_cases:
        await trigger_synthetic_alert(scenario, user, reporter, alert)
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(run_tests())