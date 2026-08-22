"""
"Minimal Streamlit dashboard entry point."
"Renders UI foundation, Jira synchronization status, and embedded SOC metrics."
"""
import json
import os
import time

import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Gatekeeper", layout="wide")
st.title("Gatekeeper Engine")
st.write("Frontend System Status: Online")

backend_url = os.getenv("BACKEND_URL", "http://backend:8000")
mcp_url = os.getenv("MCP_URL", "http://mcpserver:9000/sse")

tab_ledger, tab_executive = st.tabs([
    "Alert Ledger", 
    # "Developer MCP Inspector", 
    # "Agent State Diagram", 
    "Executive Analytics"
])

with tab_ledger:
    st.subheader("System Telemetry")
    if st.button("Ping Backend Health"):
        try:
            response = requests.get(f"{backend_url}/health", timeout=5)
            if response.status_code == 200:
                st.success("Backend connection established.")
            else:
                st.error(f"Backend HTTP error: {response.status_code}")
        except requests.exceptions.RequestException as error:
            st.error(f"Backend unreachable: {error}")

    st.divider()
    st.subheader("Incoming Alert Ledger")

    try:
        feed_response = requests.get(f"{backend_url}/api/v1/webhooks/jira", timeout=5)
        if feed_response.status_code == 200:
            alerts = feed_response.json()
            if not alerts:
                st.info("No active alerts in database.")
            else:
                for alert in alerts:
                    thread_id = alert.get("thread_id")
                    with st.expander(f"Ticket: {alert.get('ticket_id')} - {alert.get('alert_type')} ({alert.get('status')})"):
                        st.write(f"**Thread ID:** `{thread_id}`")
                        st.write(f"**User Email:** {alert.get('user_email')}")
                        
                        try:
                            state_response = requests.get(f"{backend_url}/api/v1/graph/state/{thread_id}", timeout=5)
                            if state_response.status_code == 200:
                                raw_response = state_response.json()
                                
                                state_data = raw_response.get("values", raw_response.get("state", raw_response))
                                if isinstance(state_data, str):
                                    state_data = json.loads(state_data)

                                if isinstance(state_data, dict):
                                    error_msg = state_data.get('error_message')
                                    if error_msg:
                                        st.error(f"Critical System Fault: {error_msg}")
                                        # st.toast("Workflow routed to fallback node.", icon="🚨")
                                        if st.button("Emergency Manual Override", key=f"override_{thread_id}"):
                                            st.info("System parked. Awaiting manual SOC intervention.")

                                    jira_status = state_data.get('jira_sync_status')
                                    if jira_status == "Success":
                                        st.success("Jira Synchronization: Completed - Status Resolved")
                                    elif jira_status:
                                        st.warning(f"Jira Synchronization: {jira_status}")

                                    # Maintain previous evidence rendering logic here
                                    evidence = state_data.get("investigative_evidence", {})
                                    st.markdown("### AI Analysis Summary")
                                    st.markdown(f"> **Investigation Summary:** {state_data.get('summary', 'Pending...')}")
                                    st.markdown(f"> **Proposed Action:** `{state_data.get('proposed_action', 'Pending...')}`")
                                    
                                    if state_data.get('summary') and not error_msg:
                                        human_approved = state_data.get('human_approved')
                                        st.divider()
                                        
                                        if human_approved is None:
                                            st.markdown("#### Human Authorization Required")
                                            btn_col1, btn_col2 = st.columns(2)
                                            with btn_col1:
                                                if st.button("Approve & Execute", type="primary", key=f"approve_{thread_id}"):
                                                    requests.post(f"{backend_url}/api/v1/tickets/{thread_id}/approve", timeout=5)
                                                    st.success("Approval staged. Executing...")
                                            with btn_col2:
                                                if st.button("Reject Ticket", key=f"reject_{thread_id}"):
                                                    requests.post(f"{backend_url}/api/v1/tickets/{thread_id}/reject", timeout=5)
                                                    st.error("Remediation blocked. Halting workflow.")
                                        elif human_approved is True:
                                            st.markdown("### Live Execution Log")
                                            for log_entry in state_data.get('execution_log', []):
                                                st.code(log_entry)
                        except requests.exceptions.RequestException:
                            st.warning("Backend timeout while retrieving state.")
        else:
            st.error(f"Failed to fetch alerts. Status code: {feed_response.status_code}")
    except requests.exceptions.RequestException:
        st.error("Backend connection lost. Retrying...")

# with tab_inspector:
#     st.info("Developer MCP tool execution retained as configured.")

# with tab_diagram:
#     st.subheader("LangGraph Execution Blueprint")
#     if st.button("Fetch Architecture Schema"):
#         try:
#             schema_response = requests.get(f"{backend_url}/api/v1/graph/schema", timeout=5)
#             if schema_response.status_code == 200:
#                 mermaid_syntax = schema_response.text.replace("<p>", "").replace("</p>", "").replace("&nbsp;", " ")
#                 st.markdown(f"```mermaid\n{mermaid_syntax}\n```")
#         except Exception:
#             st.error("Schema endpoint unreachable")

with tab_executive:
    st.subheader("SOC Operations Executive Metrics")
    st.write("Live operational data ingested via Prometheus and visualized natively.")
    components.iframe(src="http://localhost:4000/d-solo/gatekeeper/soc-metrics?orgId=1&panelId=1&theme=light", height=500)
    components.iframe(src="http://localhost:4000/d-solo/gatekeeper/soc-metrics?orgId=1&panelId=2&theme=light", height=300)

time.sleep(5)
st.rerun()