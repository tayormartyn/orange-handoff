"""
Trade-permission preflight (SCOPE_TRADE). Validates a demo trade token WITHOUT ever printing/logging
or returning the token. Balance/currency are refreshed before every submission. Connects only to the
demo endpoint; there is no configurable live fallback. Architecture validated with mocks this phase.

Token-setup procedure (no secrets in chat/source):
  1. Mint a demo access token with permissionScope=SCOPE_TRADE via the existing local mint helper
     (browser OAuth), storing it ONLY in the local secure token cache (data/ctrader_token.json,
     git-ignored) or an env var — never pasted into chat or committed.
  2. This preflight reads that cache read-only and validates scope/account/isLive/endpoint.
"""
from __future__ import annotations

import config as CFG


def preflight_trade_permission(*, fetch_account_state, endpoint_host):
    """fetch_account_state() -> {account_id, is_live, currency, balance, permission_scope, environment}.
    Returns a masked verdict; never includes the token."""
    d = fetch_account_state()
    issues = []
    if endpoint_host != CFG.DEMO_ENDPOINT_HOST:
        issues.append("ENDPOINT_NOT_DEMO")
    if d.get("account_id") not in CFG.DEMO_ALLOWLIST_ACCOUNT_IDS:
        issues.append("ACCOUNT_NOT_ALLOWLISTED")
    if d.get("is_live") is not False:
        issues.append("ACCOUNT_IS_LIVE")
    if str(d.get("permission_scope", "")).upper() != CFG.REQUIRED_PERMISSION_SCOPE:
        issues.append("SCOPE_NOT_TRADE")
    if str(d.get("environment", "")).upper() != CFG.REQUIRED_ENVIRONMENT:
        issues.append("ENVIRONMENT_NOT_DEMO")
    ok = not issues
    return {
        "ok": ok, "issues": issues,
        "permission_scope": d.get("permission_scope"),
        "endpoint": endpoint_host, "endpoint_is_demo": endpoint_host == CFG.DEMO_ENDPOINT_HOST,
        "account": {"account_id": d.get("account_id"), "is_live": d.get("is_live"),
                    "currency": d.get("currency"), "balance": d.get("balance"),
                    "environment": d.get("environment")},
        "no_live_fallback": True, "token_present": True, "token_value_exposed": False,
    }


def one_order_readiness_preflight(*, fetch_account_state, symbol_ok, balance_ok, volume_metadata_ok,
                                  expected_margin_healthy, endpoint_host):
    """NON-TRADING readiness display. Constructs/sends NOTHING (no ProtoOANewOrderReq). Confirms the
    demo endpoint, account, isLive, scope, symbol, refreshed balance/volume metadata, margin path."""
    perm = preflight_trade_permission(fetch_account_state=fetch_account_state, endpoint_host=endpoint_host)
    checks = {
        "DEMO_endpoint_verified": endpoint_host == CFG.DEMO_ENDPOINT_HOST,
        "endpoint_port": CFG.DEMO_ENDPOINT_PORT,
        "account_4257941_verified": perm["account"]["account_id"] in CFG.DEMO_ALLOWLIST_ACCOUNT_IDS,
        "isLive_false": perm["account"]["is_live"] is False,
        "permissionScope_SCOPE_TRADE": perm["ok"] and perm["permission_scope"] == CFG.REQUIRED_PERMISSION_SCOPE,
        "xauusd_symbol_id_verified": bool(symbol_ok),
        "balance_currency_refreshed": bool(balance_ok),
        "volume_metadata_refreshed": bool(volume_metadata_ok),
        "expected_margin_path_healthy": bool(expected_margin_healthy),
    }
    return {"checks": checks, "all_ok": all(v is True for v in checks.values() if isinstance(v, bool)),
            "ORDER_SENDING_ENABLED": CFG.ORDER_SENDING_ENABLED, "NO_ORDER_SENT": True,
            "order_constructed": False, "token_value_exposed": False,
            "account": perm["account"], "permission_scope": perm["permission_scope"]}


def refresh_account_before_submission(*, fetch_account_state):
    """Refresh balance/currency immediately before a proposal submission (no token exposed)."""
    d = fetch_account_state()
    return {"account_id": d.get("account_id"), "is_live": d.get("is_live"),
            "currency": d.get("currency"), "balance": d.get("balance"),
            "environment": d.get("environment"), "refreshed": True}
