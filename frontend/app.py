"""
Minimal Streamlit dashboard entry point.
Renders UI foundation and provides a visual health ping status alongside an alert feed.
"""
import os
import time

import requests
import streamlit as st

st.set_page_config(page_title="Gatekeeper", layout="wide")

st.title("Gatekeeper Engine")
st.write("Frontend System Status: Online")

st.divider()

backend_url = os.getenv("BACKEND_URL", "http://backend:8000")

with st.expander("System Telemetry", expanded=False):
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
st.subheader("Incoming Alert Feed")

try:
    feed_response = requests.get(f"{backend_url}/api/v1/webhooks/jira", timeout=5)
    if feed_response.status_code == 200:
        alerts = feed_response.json()
        if not alerts:
            st.info("No active alerts in queue.")
        else:
            for alert in reversed(alerts):
                st.json(alert)
    else:
        st.error(f"Failed to fetch alerts. Status code: {feed_response.status_code}")
except requests.exceptions.RequestException:
    st.error("Backend connection lost. Retrying...")

time.sleep(3)
st.rerun()