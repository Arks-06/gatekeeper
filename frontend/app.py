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

st.markdown(
    """
    <style>
    /* Target the core Streamlit view container */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0f2029 0%, #203a43 50%, #2c5364 100%) !important;
    }
    
    /* Make the top header completely transparent so it doesn't cut off the gradient */
    [data-testid="stHeader"] {
        background: transparent !important;
    }
    
    /* Darken expanders and add a subtle border so text stays readable over the gradient */
    [data-testid="stExpander"] {
        background-color: rgba(0, 0, 0, 0.4) !important;
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Ensure markdown text inside expanders doesn't wash out */
    [data-testid="stExpanderDetails"] {
        background-color: rgba(0, 0, 0, 0.2) !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)
st.title("Gatekeeper Engine - v3")
st.write("Frontend System Status: Online")

backend_url = os.getenv("BACKEND_URL", "http://backend:8000")
mcp_url = os.getenv("MCP_URL", "http://mcpserver:9000/sse")

tab_ledger, tab_executive = st.tabs([
    "Alert Ledger", 
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
                    db_status = alert.get('status', 'pending')
                    
                    # Map database status to colored UI labels for the minimized block
                    status_ui_map = {
                        "pending": "⏳ PENDING REVIEW",
                        "auto_resolved": "AUTO EXECUTED",
                        "human_approved": "APPROVED",
                        "human_rejected": "REJECTED",
                        "escalated": "🚨 ESCALATED (GUARDRAIL)"
                    }
                    display_status = status_ui_map.get(db_status, db_status.upper())
                    
                    state_data = {}
                    error_msg = None
                    
                    try:
                        state_response = requests.get(f"{backend_url}/api/v1/graph/state/{thread_id}", timeout=5)
                        if state_response.status_code == 200:
                            raw_response = state_response.json()
                            state_data = raw_response.get("values", raw_response.get("state", raw_response))
                            if isinstance(state_data, str):
                                state_data = json.loads(state_data)
                            if isinstance(state_data, dict):
                                error_msg = state_data.get('error_message')
                    except requests.exceptions.RequestException:
                        pass

                    # Expanded block header with wider information density
                    expander_title = f"{alert.get('ticket_id')} | {alert.get('alert_type').replace('_', ' ').title()} | Status: {display_status}"
                    
                    with st.expander(expander_title):
                        # Top Metrics Row
                        col1, col2, col3, col4 = st.columns(4)
                        
                        target_email = alert.get('user_email', 'Unknown')
                        reporter_email = state_data.get('reporter_email', 'System')
                        risk_score = state_data.get('risk_score', 'N/A')
                        
                        col1.markdown(f"**Target:** `{target_email}`")
                        col2.markdown(f"**Reporter:** `{reporter_email}`")
                        col3.markdown(f"**Thread ID:** `{thread_id[-12:]}`")
                        
                        # Apply color-coding to the Risk Score metric
                        if isinstance(risk_score, int):
                            delta_color = "inverse" if risk_score >= 70 else "normal"
                            col4.metric(label="AI Risk Score", value=risk_score, delta="High Risk" if risk_score >= 70 else "Low Risk", delta_color=delta_color)
                        else:
                            col4.metric(label="AI Risk Score", value="Calculating...")

                        if not state_data:
                            st.warning("Backend timeout or error while retrieving state.")
                        else:
                            if error_msg:
                                st.error(f"System Guardrail Fault: {error_msg}")
                            
                            jira_status = state_data.get('jira_sync_status')
                            if jira_status == "Success":
                                st.success("Jira Synchronization: Completed - Ticket Resolved")
                            elif jira_status:
                                st.warning(f"Jira Synchronization: {jira_status}")

                            st.markdown("### AI Analysis Summary")
                            st.info(f"**Investigation Reasoning:** {state_data.get('summary', 'Pending...')}")
                            st.markdown(f"**Proposed Action:** `{state_data.get('proposed_action', 'Pending...')}`")
                            
                            if state_data.get('summary') and not error_msg:
                                st.divider()
                                
                                # Strict Display Logic based on actual Database Status
                                if db_status == "pending":
                                    st.warning("⚠️ High Risk Score (≥70). Human authorization required before execution.")
                                    btn_col1, btn_col2 = st.columns(2)
                                    
                                    with btn_col1:
                                        if st.button("Approve & Execute", type="primary", key=f"approve_{thread_id}"):
                                            with st.spinner("Transmitting approval to orchestrator..."):
                                                requests.post(f"{backend_url}/api/v1/tickets/{thread_id}/approve", timeout=5)
                                            st.rerun()
                                    with btn_col2:
                                        if st.button("Reject Ticket", key=f"reject_{thread_id}"):
                                            with st.spinner("Haulting workflow and recording rejection..."):
                                                requests.post(f"{backend_url}/api/v1/tickets/{thread_id}/reject", timeout=5)
                                            st.rerun()
                                            
                                elif db_status in ["auto_resolved", "human_approved"]:
                                    st.success(f"Action Executed ({display_status})")
                                    st.markdown("#### Live Execution Log")
                                    for log_entry in state_data.get('execution_log', []):
                                        st.code(log_entry)
                                        
                                elif db_status == "human_rejected":
                                    st.error("Workflow terminated. Action rejected by SOC analyst.")
        else:
            st.error(f"Failed to fetch alerts. Status code: {feed_response.status_code}")
    except requests.exceptions.RequestException:
        st.error("Backend connection lost. Retrying...")

with tab_executive:
    st.subheader("SOC Operations Executive Metrics")
    st.write("Live operational data ingested via Prometheus and visualized natively.")
    components.iframe(src="http://localhost:4000/d-solo/gatekeeper/soc-metrics?orgId=1&panelId=1&theme=light", height=500)
    components.iframe(src="http://localhost:4000/d-solo/gatekeeper/soc-metrics?orgId=1&panelId=2&theme=light", height=300)

time.sleep(5)
st.rerun()