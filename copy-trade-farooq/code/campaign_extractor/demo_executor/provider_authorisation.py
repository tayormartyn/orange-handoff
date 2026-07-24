"""
Provider (Farouk) sender authorisation — FAIL CLOSED. The monitored Telegram channel carries posts
from many traders; ONLY an explicitly allowlisted Farouk sender identity may create NEW_SIGNAL
eligibility, an order preview, a Shadow Zone Campaign or a Strike & Trap campaign. Every other sender
(and any message whose sender is unknown/uncaptured) is preserved and classified but marked
UNAUTHORISED_PROVIDER_SOURCE with execution_eligible=false / may_create_proposal=false / NO_CAMPAIGN /
NO_BROKER_ACTION. Farouk is NEVER inferred from the channel id or message wording.

Farouk's stable Telegram sender id is NOT yet confirmed -> the allowlist is EMPTY -> the gate fails
closed and reports that OPERATOR CONFIRMATION is required before it can be configured.
"""
from __future__ import annotations

# EMPTY until an operator confirms Farouk's stable numeric Telegram sender id. Do NOT populate from
# channel id or message text — only from an out-of-band, operator-verified sender id.
FAROUK_AUTHORISED_SENDER_IDS = ()

AUTHORISATION_CONFIGURED = bool(FAROUK_AUTHORISED_SENDER_IDS)


def is_authorised_provider(sender_id):
    """Return (authorised, reason). Fail closed: no configured Farouk id -> nobody is authorised."""
    if not FAROUK_AUTHORISED_SENDER_IDS:
        return False, "OPERATOR_CONFIRMATION_REQUIRED"        # Farouk sender id not yet configured
    if sender_id is None or str(sender_id).strip() == "":
        return False, "SENDER_NOT_CAPTURED"
    if str(sender_id) in {str(s) for s in FAROUK_AUTHORISED_SENDER_IDS}:
        return True, None
    return False, "UNAUTHORISED_PROVIDER_SOURCE"


def authorisation_decision(sender_id):
    """Full fail-closed decision for the advisory bridge. Unauthorised => no eligibility, no proposal,
    no campaign, no broker action — the message is still preserved and classified."""
    ok, reason = is_authorised_provider(sender_id)
    return {
        "provider_authorised": ok,
        "provider_auth_reason": reason,
        "authorisation_configured": AUTHORISATION_CONFIGURED,
        "operator_confirmation_required": (not AUTHORISATION_CONFIGURED),
        # when unauthorised these HARD-OVERRIDE any interpretation eligibility
        "execution_eligible": ok,
        "may_create_proposal": ok,
        "no_campaign": (not ok),
        "no_broker_action": True,
    }
