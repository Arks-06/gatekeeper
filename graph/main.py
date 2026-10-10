"""
"Standalone CLI execution tool for the GateKeeper graph."
"Allows local testing of the AI workflow and human-in-the-loop breakpoints."
"""
import asyncio
import os
import sys
import uuid

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

# Ensure backend root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graph.workflow import build_graph


async def main():
    print("--- GateKeeper Standalone Graph CLI ---")
    
    # Use an in-memory checkpointer for local CLI testing instead of Postgres
    checkpointer = MemorySaver()
    graph = build_graph(checkpointer)
    
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    # Mock Jira webhook payload
    initial_state = {
        "ticket_id": "SEC-CLI-001",
        "user_email": "test.user@company.com",
        "alert_type": "impossible_travel"
    }
    
    print(f"\n[+] Dispatching synthetic alert: {initial_state['ticket_id']}")
    
    # Execute graph and stream node updates to the terminal
    async for event in graph.astream(initial_state, config, stream_mode="updates"):
        for node, state_update in event.items():
            print(f"\n[Node: {node}]")
            if "proposed_action" in state_update:
                print(f" -> AI Proposed Action: {state_update.get('proposed_action')}")
            if "risk_score" in state_update:
                print(f" -> Risk Score: {state_update.get('risk_score')}")
            if "error_message" in state_update:
                print(f" -> ERROR: {state_update.get('error_message')}")

    # Check if the graph parked itself at the human_approval node
    state_snapshot = await graph.aget_state(config)
    
    if state_snapshot.next and state_snapshot.next[0] == "human_approval":
        print("\n[!] WORKFLOW INTERRUPTED: High Risk Threshold Met.")
        decision = input("Approve remediation? (y/n): ").strip().lower()
        
        action = "approve" if decision == "y" else "reject"
        print(f"\n[+] Resuming workflow with decision: {action.upper()}")
        
        # Inject the human decision back into the paused thread
        async for event in graph.astream(Command(resume={"action": action}), config, stream_mode="updates"):
            for node, state_update in event.items():
                print(f"\n[Node: {node}]")
                if state_update.get("execution_log"):
                    print(f" -> Log: {state_update['execution_log'][-1]}")
                    
    print("\n[+] Workflow Execution Complete.")
    final_state = await graph.aget_state(config)
    print(f"Final Status: {final_state.values.get('jira_sync_status', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(main())