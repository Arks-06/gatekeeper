"""
"Defines Pydantic schemas for structured LLM outputs."
"Enforces the JSON response structure from the Grok API."
"""
from pydantic import BaseModel, Field


class RemediationPlan(BaseModel):
    summary: str = Field(description="Human-readable summary of the alert and gathered evidence.")
    risk_score: int = Field(description="Calculated risk score from 1 to 100.")
    proposed_action: str = Field(description="The exact technical fix or script to execute.")