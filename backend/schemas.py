"""
"Pydantic models for request validation."
"Enforces strict typing for incoming webhook payloads."
"""

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class AlertTypeEnum(str, Enum):
    account_lockout = "account_lockout"
    impossible_travel = "impossible_travel"
    phishing_report = "phishing_report"
    malware_detected = "malware_detected"
    suspicious_behavior = "suspicious_behavior"
    mass_download = "mass_download"


class JiraWebhookPayload(BaseModel):
    ticket_id: str = Field(..., description="Unique identifier for the Jira ticket.")
    user_email: str = Field(..., description="Email of the affected user.")
    reporter_email: str | None = Field(default=None, description="Email of the user who reported the issue.")
    alert_type: AlertTypeEnum = Field(..., description="Categorized security event type.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Time of event ingestion.",
    )