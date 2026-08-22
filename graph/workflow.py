"""
"Initializes the LangGraph StateGraph and defines execution nodes."
"Establishes deterministic routing and the human-in-the-loop breakpoint."
"""
import json
import os
import sys

import instructor
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from openai import AsyncOpenAI

from .fallback import execute_fallback
from .guardrails import WHITELIST_REGISTRY, validate_action
from .jira_sync import sync_jira_ticket
from .llm_schemas import RemediationPlan
from .state import GatekeeperState

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from metrics import TICKETS_AUTO_RESOLVED_TOTAL

MCP_URL = os.getenv("MCP_INTERNAL_URL", "http://mcpserver:9000/sse")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


async def investigate_alert(state: GatekeeperState) -> GatekeeperState:
    evidence = {}
    target_email = state.get("user_email")

    if not target_email:
        state["investigative_evidence"] = evidence
        return state

    try:
        async with sse_client(MCP_URL) as streams:  # noqa: SIM117
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                
                ad_response = await session.call_tool(
                    "query_active_directory", 
                    arguments={"target_email": target_email}
                )
                if ad_response.content:
                    evidence["active_directory"] = json.loads(ad_response.content[0].text)

                vpn_response = await session.call_tool(
                    "query_vpn_logs", 
                    arguments={"target_email": target_email}
                )
                if vpn_response.content:
                    evidence["vpn_logs"] = [json.loads(vpn_response.content[0].text)]
                    
    except Exception as error:  # noqa: BLE001
        evidence["error"] = str(error)
        state["error_message"] = f"Investigation Error: {error!s}"
    
    state["investigative_evidence"] = evidence
    return state


async def synthesize_and_propose(state: GatekeeperState) -> GatekeeperState:
    if state.get("error_message"):
        return state

    client = instructor.from_openai(
        AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=GROQ_API_KEY,
        )
    )

    alert_type = state.get('alert_type')
    allowed_actions = WHITELIST_REGISTRY.get(alert_type, [])

    prompt = (
        f"Alert Type: {alert_type}\n"
        f"Evidence: {json.dumps(state.get('investigative_evidence'))}\n"
        f"Allowed Actions: {allowed_actions}"
    )
    
    try:
        response = await client.chat.completions.create(
            model="openai/gpt-oss-120b",
            response_model=RemediationPlan,
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "Analyze security alerts and output structured remediation plans. "
                        "The proposed_action field MUST exactly match one of the provided Allowed Actions. "
                        "Do not use conversational language for the proposed_action."
                    )
                },
                {"role": "user", "content": prompt}
            ],
        )
        state["summary"] = response.summary
        state["risk_score"] = response.risk_score
        state["proposed_action"] = response.proposed_action
    except Exception as error:  # noqa: BLE001
        state["error_message"] = f"Synthesis Error: {error!s}"
    
    return state


def await_human_approval(state: GatekeeperState) -> GatekeeperState:
    if state.get("error_message"):
        return state

    human_decision = interrupt("Human approval required before remediation execution.")
    
    if isinstance(human_decision, dict) and human_decision.get("action") == "approve":
        state["human_approved"] = True
    else:
        state["human_approved"] = False
        
    return state


async def execute_remediation(state: GatekeeperState) -> GatekeeperState:
    alert_type = state.get("alert_type")
    proposed_action = state.get("proposed_action")
    target_email = state.get("user_email")
    execution_log = state.get("execution_log", []) or []

    try:
        validate_action(alert_type, proposed_action)
        
        async with sse_client(MCP_URL) as streams:  # noqa: SIM117
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                response = await session.call_tool(
                    proposed_action, 
                    arguments={"target_email": target_email}
                )
                if response.content:
                    execution_log.append(f"SUCCESS: {response.content[0].text}")
                    
    except Exception as error:  # noqa: BLE001
        execution_log.append(f"FAILURE: {error!s}")
        state["error_message"] = f"Execution Error: {error!s}"

    state["execution_log"] = execution_log
    return state


def check_approval(state: GatekeeperState) -> str:
    if state.get("error_message"):
        return "fallback"
    if state.get("human_approved"):
        return "execute"
    return "end"


def route_post_remediation(state: GatekeeperState) -> str:
    if state.get("error_message"):
        return "fallback"
    return "jira_sync"


def route_post_jira(state: GatekeeperState) -> str:
    if state.get("error_message") or "Failed" in str(state.get("jira_sync_status", "")):
        return "fallback"
    TICKETS_AUTO_RESOLVED_TOTAL.inc()
    return "end"


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    workflow = StateGraph(GatekeeperState)

    workflow.add_node("investigate", investigate_alert)
    workflow.add_node("synthesize", synthesize_and_propose)
    workflow.add_node("human_approval", await_human_approval)
    workflow.add_node("remediate", execute_remediation)
    workflow.add_node("jira_sync", sync_jira_ticket)
    workflow.add_node("fallback", execute_fallback)

    workflow.set_entry_point("investigate")
    
    workflow.add_edge("investigate", "synthesize")
    workflow.add_edge("synthesize", "human_approval")

    workflow.add_conditional_edges(
        "human_approval",
        check_approval,
        {"execute": "remediate", "end": END, "fallback": "fallback"},
    )
    
    workflow.add_conditional_edges(
        "remediate", 
        route_post_remediation, 
        {"jira_sync": "jira_sync", "fallback": "fallback"}
    )
    
    workflow.add_conditional_edges(
        "jira_sync", 
        route_post_jira, 
        {"end": END, "fallback": "fallback"}
    )
    
    workflow.add_edge("fallback", END)

    if checkpointer:
        return workflow.compile(checkpointer=checkpointer)

    return workflow.compile()