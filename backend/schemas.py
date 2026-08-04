"""
Pydantic models for request validation.
Enforces strict typing for incoming webhook payloads.
"""
from datetime import datetime, UTC
from pydantic import BaseModel, Field

class JiraWebhookPayload(BaseModel):
    ticket_id: str = Field(..., description="Unique identifier for the Jira ticket.")
    user_email: str = Field(..., description="Email of the affected user.")
    alert_type: str = Field(..., description="Categorized security event type.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), 
        description="Time of event ingestion."
    )