"""
FastAPI application entry point.
Configures baseline server instance, JSON logging, and Prometheus telemetry.
"""
import logging
from typing import List

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from pythonjsonlogger import jsonlogger

from schemas import JiraWebhookPayload

logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

app = FastAPI(title="Gatekeeper Backend")

Instrumentator().instrument(app).expose(app)

# Temporary in-memory state.
# to be replaced with asyncpg database list operations.
alert_queue: List[JiraWebhookPayload] = []

@app.get("/health")
async def health_check():
    logger.info("Health check endpoint accessed")
    return {"status": "ok"}

@app.post("/api/v1/webhooks/jira", response_model=dict, status_code=201)
async def ingest_jira_webhook(payload: JiraWebhookPayload):
    logger.info(f"Received webhook for ticket: {payload.ticket_id}")
    # append to be replaced with asyncpg insert query.
    alert_queue.append(payload)
    return {"status": "success", "message": "Payload validated and queued"}

@app.get("/api/v1/webhooks/jira", response_model=List[JiraWebhookPayload])
async def get_queued_alerts():
    # to be replaced with asyncpg select query.
    return alert_queue