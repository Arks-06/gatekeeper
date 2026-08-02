"""
FastAPI application entry point.
Configures baseline server instance, JSON logging, and Prometheus telemetry.
"""
import logging
from fastapi import FastAPI
from pythonjsonlogger import jsonlogger
from prometheus_fastapi_instrumentator import Instrumentator

logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# This 'app' variable is exactly what Uvicorn is looking for.
app = FastAPI(title="Gatekeeper Backend")

Instrumentator().instrument(app).expose(app)

@app.get("/health")
async def health_check():
    logger.info("Health check endpoint accessed")
    return {"status": "ok"}