"""
"Handles creation and retrieval of entity records."
"""
# isort: off
import uuid6
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from models import Ticket, AuditLog
from schemas import JiraWebhookPayload
# isort: on

async def create_ticket(session: AsyncSession, payload: JiraWebhookPayload) -> Ticket:
    thread_uuid = str(uuid6.uuid7())
    ticket = Ticket(
        ticket_id=payload.ticket_id,
        thread_id=thread_uuid,
        user_email=payload.user_email,
        alert_type=payload.alert_type,
        status="pending",
    )
    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)
    return ticket

async def get_all_tickets(session: AsyncSession) -> list[Ticket]:
    statement = select(Ticket).order_by(Ticket.created_at.desc())
    result = await session.execute(statement)
    return result.scalars().all()

async def create_audit_log(session: AsyncSession, ticket_id: str, action: str) -> AuditLog:
    """Persists a single execution or decision event to the database."""
    log_entry = AuditLog(
        ticket_id=ticket_id,
        action=action
    )
    session.add(log_entry)
    await session.commit()
    await session.refresh(log_entry)
    return log_entry

async def update_ticket_status(session: AsyncSession, ticket_id: str, status: str) -> None:
    statement = select(Ticket).where(Ticket.ticket_id == ticket_id)
    result = await session.execute(statement)
    ticket = result.scalar_one_or_none()
    if ticket:
        ticket.status = status
        await session.commit()