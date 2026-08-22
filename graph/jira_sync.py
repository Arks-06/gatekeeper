"""
"Constructs markdown audit trails and dispatches outbound Jira API requests."
"Finalizes ticket resolution post-remediation execution."
"""
import os

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from .state import GatekeeperState

JIRA_API_URL = os.getenv("JIRA_API_URL", "http://mock-jira.internal/api")
JIRA_API_KEY = os.getenv("JIRA_API_KEY", "mock_key")

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def push_to_jira(ticket_id: str, payload: dict) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{JIRA_API_URL}/issue/{ticket_id}/resolve",
            json=payload,
            headers={"Authorization": f"Bearer {JIRA_API_KEY}"},
            timeout=10.0
        )
        response.raise_for_status()

async def sync_jira_ticket(state: GatekeeperState) -> GatekeeperState:
    ticket_id = state.get("ticket_id")
    execution_log = state.get("execution_log", []) or []
    summary = state.get("summary", "")
    
    audit_trail = f"**GateKeeper Autonomous Resolution**\n\n**Summary:**\n{summary}\n\n**Execution Log:**\n"
    if execution_log:
        for log in execution_log:
            audit_trail += f"- {log}\n"
    else:
        audit_trail += "- No actions executed.\n"

    payload = {
        "status": "Resolved",
        "comment": audit_trail
    }

    try:
        await push_to_jira(ticket_id, payload)
        state["jira_sync_status"] = "Success"
    except Exception as error:  # noqa: BLE001
        state["jira_sync_status"] = f"Failed: {error!s}"
        state["error_message"] = f"Jira Outbound Sync Error: {error!s}"

    return state