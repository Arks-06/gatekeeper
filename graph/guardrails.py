"""
"Strict whitelist guardrail validation layer."
"Enforces execution boundaries before granting MCP write operations."
"""

class RemediationGuardrailError(Exception):
    pass

# Hardcoded registry of permitted state-mutating actions mapped to alert types.
WHITELIST_REGISTRY = {
    "account_lockout": ["unlock_account", "reset_user_password"],
    "impossible_travel": ["revoke_active_sessions", "force_mfa_challenge"]
}

def validate_action(alert_type: str, proposed_action: str) -> str:
    valid_actions = WHITELIST_REGISTRY.get(alert_type, [])
    if proposed_action not in valid_actions:
        raise RemediationGuardrailError(
            f"Execution Blocked: Action '{proposed_action}' is not whitelisted for alert type '{alert_type}'."
        )
    return proposed_action