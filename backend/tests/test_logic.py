import pytest
from graph.guardrails import validate_action
from graph.workflow import check_approval, route_post_jira, route_post_remediation


# --- check_approval tests ---
def test_check_approval_with_error():
    assert check_approval({"error_message": "Connection timeout"}) == "fallback"

def test_check_approval_approved():
    assert check_approval({"human_approved": True}) == "execute"

def test_check_approval_rejected():
    assert check_approval({"human_approved": False}) == "end"

# --- route_post_remediation tests ---
def test_route_post_remediation_with_error():
    assert route_post_remediation({"error_message": "Tool execution failed"}) == "fallback"

def test_route_post_remediation_success():
    assert route_post_remediation({}) == "jira_sync"

# --- route_post_jira tests ---
def test_route_post_jira_with_error():
    assert route_post_jira({"error_message": "Network down"}) == "fallback"

def test_route_post_jira_failed_status():
    assert route_post_jira({"jira_sync_status": "Failed to authenticate"}) == "fallback"

def test_route_post_jira_success():
    assert route_post_jira({"jira_sync_status": "Synced successfully"}) == "end"

# --- validate_action test ---
def test_validate_action_invalid_raises_exception():
    with pytest.raises(Exception): # noqa: B017
        # Assuming 'format_c_drive' is never in the whitelist for 'phishing'
        validate_action("phishing", "format_c_drive")