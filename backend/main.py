"""
"FastAPI application entry point."
"Configures baseline server instance, JSON logging, and Prometheus telemetry."
"""
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Annotated

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crud import create_ticket, get_all_tickets
from database import DATABASE_URL, get_session, init_db
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from models import Ticket
from prometheus_fastapi_instrumentator import Instrumentator
from pythonjsonlogger import jsonlogger
from schemas import JiraWebhookPayload
from sqlalchemy.ext.asyncio import AsyncSession
from tasks import resume_workflow

from graph.workflow import build_graph

logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

CHECKPOINTER_URI = DATABASE_URL.replace("postgresql+asyncpg", "postgresql")

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
    try:
        logger.info(f"Received webhook for ticket: {payload.ticket_id}")
        ticket = await create_ticket(session, payload)
        
        async with AsyncPostgresSaver.from_conn_string(CHECKPOINTER_URI) as checkpointer:
            graph = build_graph(checkpointer)
            config = {"configurable": {"thread_id": ticket.thread_id}}
            await graph.ainvoke(
                {"ticket_id": ticket.ticket_id, "user_email": ticket.user_email, "alert_type": ticket.alert_type},
                config
            )

        return {"status": "success", "message": "Payload validated and orchestrated", "thread_id": ticket.thread_id}
    except Exception as error:  # noqa: BLE001
        logger.error(f"Error processing webhook: {error!s}")
        raise HTTPException(status_code=500, detail="Internal server error during ingestion")

@app.get("/api/v1/webhooks/jira", response_model=list[Ticket])
async def get_queued_alerts(
    session: Annotated[AsyncSession, Depends(get_session)]
):
    tickets = await get_all_tickets(session)
    return tickets

@app.post("/api/v1/tickets/{thread_id}/approve", status_code=202)
async def approve_ticket_execution(thread_id: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(resume_workflow, thread_id, "approve")
    return {"status": "accepted", "message": "Approval callback received, resuming orchestration."}

@app.post("/api/v1/tickets/{thread_id}/reject", status_code=202)
async def reject_ticket_execution(thread_id: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(resume_workflow, thread_id, "reject")
    return {"status": "accepted", "message": "Rejection callback received, terminating execution."}

@app.get("/api/v1/graph/schema", response_class=PlainTextResponse)
async def get_graph_schema():
    logger.info("Exporting LangGraph architecture schema")
    graph = build_graph(None)
    return graph.get_graph().draw_mermaid()

@app.get("/api/v1/graph/state/{thread_id}")
async def get_graph_state(thread_id: str):
    try:
        from psycopg_pool import AsyncConnectionPool
        psycopg_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        
        async with AsyncConnectionPool(conninfo=psycopg_url) as pool:
            checkpointer = AsyncPostgresSaver(pool)
            graph = build_graph(checkpointer)
            config = {"configurable": {"thread_id": thread_id}}
            
            snapshot = await graph.aget_state(config)
            return snapshot.values
            
    except Exception as e:   # noqa: BLE001
        logger.error(f"Error retrieving state for {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving state")