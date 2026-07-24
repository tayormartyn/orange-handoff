"""
Hard submission firewall — the all-or-nothing gate immediately before any order request. ONE failed
check blocks submission. There is no live-endpoint fallback. `ORDER_SENDING_ENABLED` is one of the
required checks, so with it False the firewall can never pass and no order can be built or sent.
"""
from __future__ import annotations

import config as CFG
from models import Check, FirewallResult
import disable_guard


def submission_firewall(*, approved, account, endpoint_host, permission_scope, quote_fresh,
                        signal_fresh, proposal_unexpired, expected_margin_ok, human_confirmed_signal,
                        provider_evidence_displayed, existing_order_for_id, operator_approval_completed,
                        disable_path=None, order_sending_enabled=None):
    ose = CFG.ORDER_SENDING_ENABLED if order_sending_enabled is None else order_sending_enabled
    scope_ok = str(permission_scope).upper() == CFG.REQUIRED_PERMISSION_SCOPE
    checks = [
        Check("environment_is_demo", account.environment == CFG.REQUIRED_ENVIRONMENT, account.environment),
        Check("endpoint_is_demo", endpoint_host == CFG.DEMO_ENDPOINT_HOST, str(endpoint_host)),
        Check("account_allowlisted", account.account_id in CFG.DEMO_ALLOWLIST_ACCOUNT_IDS, str(account.account_id)),
        Check("account_not_live", account.is_live is False, f"isLive={account.is_live}"),
        Check("permission_scope_trade", scope_ok, str(permission_scope)),
        Check("instrument_is_xauusd", str(approved.symbol_name).upper() == CFG.XAUUSD_NAME, approved.symbol_name),
        Check("order_type_limit_or_stop", str(approved.order_type).upper() in ("LIMIT", "STOP"), approved.order_type),
        Check("mandatory_stop_loss_present", approved.stop_loss is not None, str(approved.stop_loss)),
        Check("risk_within_max", approved.risk_pct <= CFG.MAX_RISK_PCT, f"{approved.risk_pct}"),
        Check("order_sending_enabled", bool(ose), "DISABLED_THIS_PHASE" if not ose else "ok"),
        disable_guard.disabled_check(disable_path),
        Check("human_confirmed_signal", human_confirmed_signal is True, ""),
        Check("provider_evidence_displayed", provider_evidence_displayed is True, ""),
        Check("quote_fresh", quote_fresh is True, ""),
        Check("signal_fresh", signal_fresh is True, ""),
        Check("proposal_unexpired", proposal_unexpired is True, ""),
        Check("expected_margin_accepted", expected_margin_ok is True, ""),
        Check("no_existing_order_for_id", existing_order_for_id is False, ""),
        Check("guarded_operator_approval_completed", operator_approval_completed is True, ""),
    ]
    return FirewallResult(checks, all(c.passed for c in checks))
