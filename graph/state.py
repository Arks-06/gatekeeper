"""
"Defines the strictly typed state schema for the LangGraph orchestrator."
"Acts as the short-term memory structure passed between execution nodes."
"""
from typing import Any, TypedDict


class GatekeeperState(TypedDict):
    ticket_id: str
    user_email: str
    alert_type: str
    investigative_evidence: dict[str, Any] | None
    summary: str | None
    risk_score: int | None
    proposed_action: str | None
    human_approved: bool | None
    execution_log: list[str] | None