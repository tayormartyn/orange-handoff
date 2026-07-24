"""
Hard MANAGEMENT firewall — all-or-nothing gate before any amend/close/cancel. ONE failed check blocks.
Independent of the entry-order gate: it requires ORDER_MANAGEMENT_ENABLED (a SEPARATE lock) plus a
verified position/order match. With ORDER_MANAGEMENT_ENABLED=False it can never pass, so no management
protobuf is built or sent. No live-endpoint fallback.
"""
from __future__ import annotations

import config as CFG
from models import Check, FirewallResult
import disable_guard

_SUPPORTED = ("MOVE_SL_BREAKEVEN", "PARTIAL_CLOSE", "CANCEL_PENDING", "COMPOSITE")


def management_firewall(*, approved, account, endpoint_host, endpoint_port, permission_scope,
                        position_match, quote_fresh, update_fresh, plan_unexpired, replay_status,
                        operator_approval_completed, permit_valid, lease_valid, disable_path=None,
                        order_management_enabled=None):
    ome = CFG.ORDER_MANAGEMENT_ENABLED if order_management_enabled is None else order_management_enabled
    scope_ok = str(permission_scope).upper() == CFG.REQUIRED_PERMISSION_SCOPE
    needs_position = approved.action in ("MOVE_SL_BREAKEVEN", "PARTIAL_CLOSE", "COMPOSITE")
    checks = [
        Check("environment_is_demo", account.environment == CFG.REQUIRED_ENVIRONMENT, account.environment),
        Check("endpoint_is_demo_host", endpoint_host == CFG.DEMO_ENDPOINT_HOST, str(endpoint_host)),
        Check("endpoint_is_demo_port", endpoint_port == CFG.DEMO_ENDPOINT_PORT, str(endpoint_port)),
        Check("account_allowlisted", account.account_id in CFG.DEMO_ALLOWLIST_ACCOUNT_IDS, str(account.account_id)),
        Check("account_not_live", account.is_live is False, f"isLive={account.is_live}"),
        Check("permission_scope_trade", scope_ok, str(permission_scope)),
        Check("instrument_is_xauusd", str(approved.symbol_name).upper() == CFG.XAUUSD_NAME, approved.symbol_name),
        Check("action_supported", approved.action in _SUPPORTED, approved.action),
        Check("position_or_order_matched", position_match == "VERIFIED", str(position_match)),
        Check("order_management_enabled", bool(ome), "DISABLED_THIS_PHASE" if not ome else "ok"),
        disable_guard.disabled_check(disable_path),
        Check("quote_fresh", quote_fresh is True, ""),
        Check("update_fresh", update_fresh is True, ""),
        Check("plan_unexpired", plan_unexpired is True, ""),
        Check("no_replay_status", replay_status != "REPLAY_VALIDATION_ONLY", str(replay_status)),
        Check("guarded_operator_approval_completed", operator_approval_completed is True, ""),
        Check("valid_management_permit", permit_valid is True, ""),
        Check("valid_management_lease", lease_valid is True, ""),
    ]
    if needs_position:
        checks.append(Check("broker_position_id_present", bool(approved.broker_position_id),
                            str(approved.broker_position_id)))
    if approved.action == "CANCEL_PENDING":
        checks.append(Check("broker_order_id_present", bool(approved.broker_order_id),
                            str(approved.broker_order_id)))
    return FirewallResult(checks, all(c.passed for c in checks))
