"""View-only connection verification. Every field is checked LOCALLY against the
allowlist, and the granted OAuth permission is reported AS OBSERVED, not as requested.

The safety-critical inversion vs. the execution lane: here a SCOPE_TRADE grant is a
REFUSAL condition (too much access was granted), not a pass condition.
"""
from . import preflight_config as cfg


class PreflightRefusal(Exception):
    """Raised when an observed field fails the view-only allowlist. Fail closed."""


def observe_scope(account):
    """Return the granted permission AS OBSERVED plus its classification. Never assumes
    the requested scope was the granted scope."""
    observed = account.get("permissionScope")
    return {
        "granted_scope_observed": observed,
        "is_view_only": observed == cfg.REQUIRED_GRANTED_SCOPE,
        "is_trading": observed == cfg.REFUSED_GRANTED_SCOPE,
    }


def check(account):
    """Five-field view-only conjunction. Returns a per-field verdict dict (all observed
    values retained for the report) and an overall ok flag. Does NOT raise — the caller
    decides whether to refuse — so the report can show exactly which field failed."""
    scope = observe_scope(account)
    fields = {
        "endpoint": {
            "observed": account.get("endpoint"),
            "expected": cfg.DEMO_ENDPOINT,
            "ok": account.get("endpoint") == cfg.DEMO_ENDPOINT,
        },
        "isLive": {
            "observed": account.get("isLive"),
            "expected": False,
            "ok": account.get("isLive") is False,
        },
        "ctidTraderAccountId": {
            "observed": account.get("ctidTraderAccountId"),
            "expected": cfg.ALLOWED_CTID_TRADER_ACCOUNT_ID,
            "ok": account.get("ctidTraderAccountId") == cfg.ALLOWED_CTID_TRADER_ACCOUNT_ID,
        },
        "broker_environment": {
            "observed": account.get("broker_environment"),
            "expected": cfg.EXPECTED_BROKER_ENVIRONMENT,
            "ok": account.get("broker_environment") == cfg.EXPECTED_BROKER_ENVIRONMENT,
        },
        # granted scope must be view-only AND must NOT be trading (report as observed)
        "granted_scope": {
            "observed": scope["granted_scope_observed"],
            "expected": cfg.REQUIRED_GRANTED_SCOPE,
            "ok": scope["is_view_only"] and not scope["is_trading"],
        },
    }
    ok = all(f["ok"] for f in fields.values())
    return {"ok": ok, "fields": fields, "scope": scope}


def require_view_only(account):
    """Fail-closed gate: refuse (raise) unless the full view-only conjunction holds.
    Refuses LOUDLY if a trading scope was granted."""
    v = check(account)
    if v["scope"]["is_trading"]:
        raise PreflightRefusal(
            "REFUSED: granted permission is SCOPE_TRADE (trading access). This tool is "
            "view-only; a trading grant is out of scope. Revoke the app authorization and "
            "re-grant with the 'accounts' (view-only) permission only.")
    if not v["ok"]:
        failed = [k for k, f in v["fields"].items() if not f["ok"]]
        raise PreflightRefusal(f"REFUSED: view-only verification failed on {failed}")
    return v
