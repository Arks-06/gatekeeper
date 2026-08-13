"""
"Minimal Streamlit dashboard entry point."
"Renders UI foundation and provides a visual health ping status alongside an alert feed."
"""
import asyncio
import json
import os
import time

import pandas as pd
import requests
import streamlit as st
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client

st.set_page_config(page_title="Gatekeeper", layout="wide")
st.title("Gatekeeper Engine")
st.write("Frontend System Status: Online")

backend_url = os.getenv("BACKEND_URL", "http://backend:8000")
mcp_url = os.getenv("MCP_URL", "http://mcpserver:9000/sse")

tab_ledger, tab_inspector, tab_diagram = st.tabs(["Alert Ledger", "Developer MCP Inspector", "Agent State Diagram"])

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
                        st.write(f"**Created At:** {alert.get('created_at')}")
                        
                        try:
                            state_response = requests.get(f"{backend_url}/api/v1/graph/state/{thread_id}", timeout=5)
                            if state_response.status_code == 200:
                                raw_response = state_response.json()
                                
                                if isinstance(raw_response, dict):
                                    if "values" in raw_response:
                                        state_data = raw_response["values"]
                                    elif "state" in raw_response:
                                        state_data = raw_response["state"]
                                    else:
                                        state_data = raw_response
                                else:
                                    state_data = {}

                                if isinstance(state_data, str):
                                    try:
                                        state_data = json.loads(state_data)
                                    except json.JSONDecodeError:
                                        state_data = {}

                                if isinstance(state_data, dict) and ("investigative_evidence" in state_data or "summary" in state_data or "ticket_id" in state_data):
                                    evidence = state_data.get("investigative_evidence", {})
                                    
                                    st.markdown("### Investigative Evidence")
                                    if evidence:
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            ad_data = evidence.get("active_directory", {})
                                            if ad_data:
                                                st.metric(label="Active Directory Status", value=ad_data.get("status", "Unknown"))
                                                st.caption(f"Source: {ad_data.get('source', 'N/A')}")
                                            else:
                                                st.info("No Active Directory data retrieved.")
                                        
                                        with col2:
                                            vpn_logs = evidence.get("vpn_logs", [])
                                            if vpn_logs:
                                                st.write("Recent VPN Activity")
                                                df = pd.DataFrame(vpn_logs)
                                                st.dataframe(df, use_container_width=True, hide_index=True)
                                            else:
                                                st.info("No VPN logs retrieved.")
                                    else:
                                        st.info("Agent is actively gathering evidence...")

                                    st.markdown("### AI Analysis Summary")
                                    
                                    risk_score = state_data.get('risk_score')
                                    if risk_score:
                                        st.metric(label="Calculated Threat Risk", value=f"{risk_score}/100")
                                        
                                    st.markdown(f"> **Investigation Summary:** {state_data.get('summary', 'Pending...')}")
                                    st.markdown(f"> **Proposed Action:** `{state_data.get('proposed_action', 'Pending...')}`")
                                    
                                    if state_data.get('summary'):
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
                                            st.success("Authorization Granted.")
                                            st.markdown("### Live Execution Log")
                                            execution_logs = state_data.get('execution_log', [])
                                            if execution_logs:
                                                for log_entry in execution_logs:
                                                    st.code(log_entry)
                                            else:
                                                st.info("Awaiting execution logs...")
                                        elif human_approved is False:
                                            st.error("Authorization Denied. Workflow Terminated.")
                                            
                                else:
                                    st.info("Workflow state pending initialization or unrecognized structure.")
                                    with st.expander("Developer Debug: Raw API Response"):
                                        st.json(raw_response)
                            else:
                                st.warning("Unable to fetch checkpoint state.")
                        except requests.exceptions.RequestException:
                            st.warning("Backend timeout while retrieving state.")
        else:
            st.error(f"Failed to fetch alerts. Status code: {feed_response.status_code}")
    except requests.exceptions.RequestException:
        st.error("Backend connection lost. Retrying...")

with tab_inspector:
    st.subheader("Execute Local Mock Tools")
    selected_tool = st.selectbox("Select Tool", ["query_active_directory", "query_vpn_logs"])
    target_input = st.text_input("Target Email", value="employee@company.com")

    if "mcp_result" not in st.session_state:
        st.session_state.mcp_result = None

    if st.button("Execute Tool"):
        async def execute_tool(tool_name: str, target: str):
            try:
                async with sse_client(mcp_url) as streams:  # noqa: SIM117
                    async with ClientSession(streams[0], streams[1]) as session:
                        await session.initialize()
                        response = await session.call_tool(tool_name, arguments={"target_email": target})
                        return response.content[0].text
            except Exception as e:  # noqa: BLE001
                return str(e)

        with st.spinner("Executing over MCP boundary..."):
            st.session_state.mcp_result = asyncio.run(execute_tool(selected_tool, target_input))

    if st.session_state.mcp_result:
        st.write("Execution Payload Details:")
        try:
            parsed_result = json.loads(st.session_state.mcp_result)
            st.json(parsed_result)
        except (TypeError, json.JSONDecodeError):
            st.code(st.session_state.mcp_result)

with tab_diagram:
    st.subheader("LangGraph Execution Blueprint")
    st.write("Real-time logical workflow of the autonomous orchestration engine.")
    if st.button("Fetch Architecture Schema"):
        try:
            schema_response = requests.get(f"{backend_url}/api/v1/graph/schema", timeout=5)
            if schema_response.status_code == 200:
                mermaid_syntax = schema_response.text
                mermaid_syntax = mermaid_syntax.replace("<p>", "").replace("</p>", "").replace("&nbsp;", " ")
                
                st.markdown(f"```mermaid\n{mermaid_syntax}\n```")
            else:
                st.error(f"Failed to fetch schema. Status: {schema_response.status_code}")
        except requests.exceptions.RequestException as error:
            st.error(f"Schema endpoint unreachable: {error}")

time.sleep(5)
st.rerun()