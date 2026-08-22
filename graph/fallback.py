"""
"Handles orchestrator exceptions and conditional fallback routing."
"Safely parks failed executions into a persistent human-review state."
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metrics import FALLBACK_TRIGGER_TOTAL

from .state import GatekeeperState


async def execute_fallback(state: GatekeeperState) -> GatekeeperState:
    error = state.get("error_message", "Unknown critical failure occurred.")
    
    execution_log = state.get("execution_log", []) or []
    execution_log.append(f"SYSTEM FALLBACK TRIGGERED: {error}")
    
    state["execution_log"] = execution_log
    state["human_approved"] = False
    state["jira_sync_status"] = "Pending Manual SOC Review"
    
    FALLBACK_TRIGGER_TOTAL.inc()
    
    return state