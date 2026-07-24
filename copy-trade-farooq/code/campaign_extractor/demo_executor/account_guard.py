"""
Absolute demo firewall. ANY future submission route must call this and refuse unless EVERY check
passes. There is no live-endpoint fallback anywhere in this package. Secrets are never included.
"""
from __future__ import annotations

import config as CFG
from models import Check, FirewallResult
import disable_guard


def token_is_trade_capable_demo(scope):
    s = (scope or "").lower()
    return "trade" in s          # a trade-capable demo scope; view-only ("") is refused


def demo_firewall(*, account, instrument, token_scope, disable_path=None, order_sending_enabled=None):
    """account: AccountSnapshot. Returns FirewallResult (all_passed only if every check green)."""
    ose = CFG.ORDER_SENDING_ENABLED if order_sending_enabled is None else order_sending_enabled
    checks = [
        Check("environment_is_demo", (account.environment == CFG.REQUIRED_ENVIRONMENT),
              account.environment),
        Check("account_not_live", account.is_live is False, f"isLive={account.is_live}"),
        Check("account_allowlisted", account.account_id in CFG.DEMO_ALLOWLIST_ACCOUNT_IDS,
              str(account.account_id)),
        Check("token_trade_capable_demo_scope", token_is_trade_capable_demo(token_scope),
              "trade" if token_is_trade_capable_demo(token_scope) else "NOT_TRADE_CAPABLE"),
        Check("instrument_is_xauusd", str(instrument).upper() == CFG.XAUUSD_NAME, str(instrument)),
        disable_guard.disabled_check(disable_path),
        # phase lock: order sending disabled -> a submission may NEVER pass; preview/dry-run still allowed
        Check("order_sending_enabled", bool(ose), "DRY_RUN_PHASE_SENDING_DISABLED" if not ose else "ok"),
    ]
    return FirewallResult(checks, all(c.passed for c in checks))


def firewall_allows_preview(fw):
    """Preview/dry-run is allowed when every check EXCEPT the phase send-lock passes (so Martyn can
    review a proposal even though sending is disabled this phase)."""
    return all(c.passed for c in fw.checks if c.name != "order_sending_enabled")
