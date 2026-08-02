"""
Minimal Streamlit dashboard entry point.
Renders UI foundation and provides a visual health ping status.
"""
import os

import requests
import streamlit as st

st.title("Gatekeeper Remediation Engine")
st.write("Frontend System Status: Online")

st.divider()

st.subheader("System Telemetry")
if st.button("Ping Backend Health"):
    backend_url = os.getenv("BACKEND_URL", "http://backend:8000")
    try:
        response = requests.get(f"{backend_url}/health", timeout=5)
        if response.status_code == 200:
            st.success("Backend connection established.")
        else:
            st.error(f"Backend HTTP error: {response.status_code}")
    except requests.exceptions.RequestException as error:
        st.error(f"Backend unreachable: {error}")