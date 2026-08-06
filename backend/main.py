"""
FastAPI application entry point.
Configures baseline server instance, JSON logging, and Prometheus telemetry.
"""

import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from pythonjsonlogger import jsonlogger
from sqlalchemy.ext.asyncio import AsyncSession

from crud import create_ticket, get_all_tickets
from database import get_session, init_db
from models import Ticket
from schemas import JiraWebhookPayload

logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Gatekeeper Backend", lifespan=lifespan)

Instrumentator().instrument(app).expose(app)


@app.get("/health")
async def health_check():
    logger.info("Health check endpoint accessed")
    return {"status": "ok"}


@app.post("/api/v1/webhooks/jira", response_model=dict, status_code=201)
async def ingest_jira_webhook(
    payload: JiraWebhookPayload, 
    session: Annotated[AsyncSession, Depends(get_session)]
):
    logger.info(f"Received webhook for ticket: {payload.ticket_id}")
    await create_ticket(session, payload)
    return {"status": "success", "message": "Payload validated and queued"}

@app.get("/api/v1/webhooks/jira", response_model=list[Ticket])
async def get_queued_alerts(
    session: Annotated[AsyncSession, Depends(get_session)]
):
    tickets = await get_all_tickets(session)
    return tickets