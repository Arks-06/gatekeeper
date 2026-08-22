"""
"Configures custom Prometheus metrics for operational observability."
"Exposes resolution rates and fallback triggers for Grafana integration."
"""
from prometheus_client import Counter

TICKETS_INGESTED_TOTAL = Counter(
    "gatekeeper_tickets_ingested_total", 
    "Total tickets received from Jira webhook trigger"
)

TICKETS_AUTO_RESOLVED_TOTAL = Counter(
    "gatekeeper_tickets_auto_resolved_total", 
    "Total tickets successfully remediated and synced back to Jira"
)

FALLBACK_TRIGGER_TOTAL = Counter(
    "gatekeeper_fallback_trigger_total", 
    "Total times the fallback node was activated due to execution failure"
)