"""
Isolated cTrader demo-order transport — ProtoOANewOrderReq ONLY. It consumes an already-validated,
immutable ApprovedDemoOrderRequest and does NOT rebuild or reinterpret trade values. Blocked by the
submission firewall (which includes ORDER_SENDING_ENABLED); with that False the transport can never
send. All acceptance/rejection/timeout/reconciliation tests use a FAKE transport. No amend/close/
cancel path exists. No live endpoint.
"""
from __future__ import annotations
import hashlib

import config as CFG
import submission_firewall as SFW

READY_STATE = CFG.READY_STATE      # future; never auto-activates


def make_client_order_id(signal_id, proposal_id, account_id, symbol_id):
    raw = f"{signal_id}|{proposal_id}|{account_id}|{symbol_id}"
    return "cli-" + hashlib.sha256(raw.encode()).hexdigest()[:20]


def field_limit_report():
    """Distinguish the official cTrader contract maxima from our internal conservative limits."""
    return {
        "official_contract_max": {"label": CFG.OFFICIAL_MAX_LABEL_LEN,
                                  "comment": CFG.OFFICIAL_MAX_COMMENT_LEN,
                                  "clientOrderId": CFG.OFFICIAL_MAX_CLIENT_ORDER_ID_LEN},
        "internal_conservative_limit": {"label": CFG.INTERNAL_MAX_LABEL_LEN,
                                        "comment": CFG.INTERNAL_MAX_COMMENT_LEN,
                                        "note": "INTERNAL_CONSERVATIVE_LIMIT — stricter than the API contract"},
    }


def validate_field_lengths(approved):
    """Enforce the INTERNAL conservative limits (label 30, comment 255) and the official clientOrderId
    max (50). Internal limits are NOT the API contract maximum."""
    issues = []
    if len(approved.label) > CFG.INTERNAL_MAX_LABEL_LEN:
        issues.append("LABEL_OVER_INTERNAL_CONSERVATIVE_LIMIT")
    if len(approved.comment) > CFG.INTERNAL_MAX_COMMENT_LEN:
        issues.append("COMMENT_OVER_INTERNAL_CONSERVATIVE_LIMIT")
    if len(approved.client_order_id) > CFG.OFFICIAL_MAX_CLIENT_ORDER_ID_LEN:
        issues.append("CLIENT_ORDER_ID_OVER_OFFICIAL_MAX")
    return issues


def build_new_order_fields(approved):
    """Build the ProtoOANewOrderReq field set from the IMMUTABLE approved values (no reinterpretation).
    Returned as a plain dict; the real protobuf message is only constructed by the live send path,
    which is unreachable while ORDER_SENDING_ENABLED is False."""
    return {
        "ctidTraderAccountId": approved.account_id, "symbolId": approved.symbol_id,
        "tradeSide": approved.trade_side, "orderType": approved.order_type,
        "volume": approved.volume_raw_protocol,
        "limitPrice": approved.limit_price, "stopPrice": approved.stop_price,
        "stopLoss": approved.stop_loss, "takeProfit": approved.take_profit,
        "clientOrderId": approved.client_order_id, "label": approved.label, "comment": approved.comment,
    }


_COMPARE = ("symbol", "direction", "order_type", "volume", "entry", "stop", "take_profit", "label",
            "comment", "client_order_id")


def _requested_view(approved):
    return {"symbol": approved.symbol_name, "direction": approved.trade_side,
            "order_type": approved.order_type,
            "volume": approved.volume_raw_protocol,
            "entry": approved.limit_price if approved.order_type == "LIMIT" else approved.stop_price,
            "stop": approved.stop_loss, "take_profit": approved.take_profit, "label": approved.label,
            "comment": approved.comment, "client_order_id": approved.client_order_id}


def compare_broker_state(approved, returned):
    req = _requested_view(approved)
    diffs = [k for k in _COMPARE if k in returned and returned.get(k) != req.get(k)]
    return diffs


def submit(approved, *, transport, account, endpoint_host, permission_scope, quote_fresh, signal_fresh,
           proposal_unexpired, expected_margin_ok, human_confirmed_signal, provider_evidence_displayed,
           operator_approval_completed, disable_path=None, order_sending_enabled=None, now_ms=0,
           audit=None):
    """One controlled submission attempt. Firewall-gated; idempotent; timeout -> reconcile (no retry)."""
    order_sending_enabled = (CFG.ORDER_SENDING_ENABLED if order_sending_enabled is None
                             else order_sending_enabled)

    # idempotency FIRST: reconcile existing orders by deterministic clientOrderId
    existing = transport.find_order_by_client_id(approved.client_order_id)
    fw = SFW.submission_firewall(
        approved=approved, account=account, endpoint_host=endpoint_host, permission_scope=permission_scope,
        quote_fresh=quote_fresh, signal_fresh=signal_fresh, proposal_unexpired=proposal_unexpired,
        expected_margin_ok=expected_margin_ok, human_confirmed_signal=human_confirmed_signal,
        provider_evidence_displayed=provider_evidence_displayed,
        existing_order_for_id=existing is not None, operator_approval_completed=operator_approval_completed,
        disable_path=disable_path, order_sending_enabled=order_sending_enabled)

    length_issues = validate_field_lengths(approved)
    if not fw.all_passed or length_issues:
        reason = "FIREWALL_BLOCKED" if not fw.all_passed else "FIELD_LENGTH_INVALID"
        final = "NO_ORDER_SENT" if not order_sending_enabled else reason
        if audit is not None:
            audit.record("ORDER_REJECTED", approved.proposal_id,
                         {"pre_send": True, "reason": reason, "length_issues": length_issues})
        return {"sent": False, "endpoint_called": False, "reason": reason, "final_state": final,
                "firewall": fw.as_dict(), "length_issues": length_issues,
                "order_sending_enabled": order_sending_enabled}

    # firewall passed -> only reachable with order_sending_enabled=True (tests, fake transport)
    fields = build_new_order_fields(approved)
    if audit is not None:
        audit.record("ORDER_REQUESTED", approved.proposal_id, {"client_order_id": approved.client_order_id})
    res = transport.new_order(fields)                    # FAKE transport in tests; no real send
    status = (res or {}).get("status")

    if status == "TIMEOUT":
        # DO NOT RETRY — reconcile first
        if audit is not None:
            audit.record("ORDER_RECONCILIATION_REQUIRED", approved.proposal_id, {})
        rec = transport.reconcile(approved.client_order_id)
        if rec is not None and audit is not None:
            audit.record("ORDER_RECONCILED", approved.proposal_id, {"broker_order_id": rec.get("broker_order_id")})
        return {"sent": "UNKNOWN", "endpoint_called": True, "final_state": "ORDER_RECONCILIATION_REQUIRED",
                "reconciled": rec, "no_retry": True}

    if status == "REJECTED":
        if audit is not None:
            audit.record("ORDER_REJECTED", approved.proposal_id,
                         {"error_code": res.get("error_code"), "error_description": res.get("error_description")})
        return {"sent": True, "accepted": False, "endpoint_called": True, "final_state": "ORDER_REJECTED",
                "error_code": res.get("error_code"), "error_description": res.get("error_description"),
                "replacement_allowed": True}

    if status == "ACCEPTED":
        if audit is not None:
            audit.record("ORDER_ACCEPTED", approved.proposal_id, {"broker_order_id": res.get("broker_order_id")})
        diffs = compare_broker_state(approved, res.get("returned") or {})
        if diffs:
            if audit is not None:
                audit.record("BROKER_STATE_MISMATCH", approved.proposal_id, {"fields": diffs})
            return {"sent": True, "accepted": True, "endpoint_called": True,
                    "final_state": "BROKER_STATE_MISMATCH", "mismatch_fields": diffs,
                    "manual_review_required": True}
        if res.get("position_id") and audit is not None:
            audit.record("POSITION_OPENED", approved.proposal_id, {"position_id": res.get("position_id")})
        return {"sent": True, "accepted": True, "endpoint_called": True, "final_state": "ORDER_ACCEPTED",
                "broker_order_id": res.get("broker_order_id"), "position_id": res.get("position_id")}

    return {"sent": True, "endpoint_called": True, "final_state": "UNKNOWN_RESPONSE", "raw": res}
