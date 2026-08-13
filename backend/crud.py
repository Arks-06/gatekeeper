"""
"Asynchronous database operation abstractions."
"Handles creation and retrieval of entity records."
"""
import uuid6
from models import Ticket
from schemas import JiraWebhookPayload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select


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