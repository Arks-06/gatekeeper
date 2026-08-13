"""
"Asynchronous background task execution module."
"Handles non-blocking LangGraph workflow resumptions securely."
"""
import logging
import os
import sys

from langgraph.types import Command
from psycopg_pool import AsyncConnectionPool

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# isort: off
from database import DATABASE_URL
from graph.workflow import build_graph
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
# isort: on

logger = logging.getLogger(__name__)

async def resume_workflow(thread_id: str, decision: str):
    psycopg_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    
    async with AsyncConnectionPool(conninfo=psycopg_url) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        graph = build_graph(checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        
        resume_payload = {"action": decision}
        
        try:
            await graph.ainvoke(Command(resume=resume_payload), config)
            logger.info(f"Successfully resumed thread {thread_id} with decision: {decision}")
        except Exception as error:  # noqa: BLE001
            logger.error(f"Failed to resume workflow for thread {thread_id}: {error!s}")