"""
"Strict whitelist guardrail validation layer."
"Enforces execution boundaries before granting MCP write operations."
"""

class SecurityGuardrailError(Exception):
    """Raised when an automated action fails security policy validation."""

# The existing whitelist
WHITELIST_REGISTRY = {
    "account_lockout": ["reset_user_password", "unlock_account"],
    "impossible_travel": ["force_mfa_reauth", "suspend_account"],
    "phishing_report": ["quarantine_email", "suspend_account"],
    "malware_detected": ["isolate_host", "quarantine_file"],
    "suspicious_behavior": ["suspend_account", "monitor_account", "revoke_tokens"],
    "mass_download": ["suspend_account", "revoke_tokens"]
}

# High-privilege targets that require strict authorization
PROTECTED_ENTITIES = ["ceo@company.com", "cfo@company.com", "admin@company.com"]

def validate_action(alert_type: str, proposed_action: str, target_email: str | None, reporter_email: str | None = None):
    """
    Validates both the functional whitelist and the identity/authorization scope.
    """
    # 1. Whitelist Verification (Existing)
    allowed_actions = WHITELIST_REGISTRY.get(alert_type, [])
    if proposed_action not in allowed_actions:
        raise SecurityGuardrailError(
            f"Action '{proposed_action}' is not permitted for alert type '{alert_type}'."
        )

    # 2. Protected Entity Guard (New)
    if target_email in PROTECTED_ENTITIES:  # noqa: SIM102
        if reporter_email != "security_admin@company.com":
            raise SecurityGuardrailError(
                f"Unauthorized: Standard automation cannot execute '{proposed_action}' on protected entity '{target_email}'."
            )

    # 3. Self-Service Identity Verification (New)
    # If a user is reported to be locked out, ensure the reporter is either the target or an authorized system
    if proposed_action == "reset_user_password":  # noqa: SIM102
        if reporter_email and reporter_email != target_email and reporter_email != "system_monitor":
            raise SecurityGuardrailError(
                f"Identity Mismatch: Reporter '{reporter_email}' is not authorized to reset password for '{target_email}'."
            )