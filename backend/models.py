"""
SQLModel database schema definitions.
Maps Python objects to PostgreSQL tables.
"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel


class Ticket(SQLModel, table=True):
    __tablename__ = "tickets"

    id: int | None = Field(default=None, primary_key=True)
    ticket_id: str = Field(
        unique=True, index=True, description="Jira ticket identifier"
    )
    user_email: str = Field(index=True)
    alert_type: str = Field(index=True)
    status: str = Field(default="pending", description="Current workflow status")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: int | None = Field(default=None, primary_key=True)
    ticket_id: str = Field(foreign_key="tickets.ticket_id")
    action: str = Field(description="Action taken by system or analyst")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
