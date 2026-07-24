"""
Isolated cTrader demo trade-MANAGEMENT transport. Consumes an immutable ApprovedManagementPlan and
sends amend/close/cancel ONLY. Blocked by the management firewall (which includes the SEPARATE
ORDER_MANAGEMENT_ENABLED lock); with that False the transport can never send and no management
protobuf is constructed. All accept/reject/timeout/reconcile tests use a FAKE transport. Composite
plans execute sequentially and STOP on the first failure (never claiming atomic execution). Timeout
reconciles before any retry. No market-entry route here.
"""
from __future__ import annotations

import config as CFG
import management_firewall as MFW
import management_adapter as ADAPTER

_SERIALIZE = {"MOVE_SL_BREAKEVEN": ADAPTER.serialize_amend_sltp,
              "PARTIAL_CLOSE": ADAPTER.serialize_close,
              "CANCEL_PENDING": ADAPTER.serialize_cancel}


def _gate(approved, kw):
    return MFW.management_firewall(
        approved=approved, account=kw["account"], endpoint_host=kw["endpoint_host"],
        endpoint_port=kw["endpoint_port"], permission_scope=kw["permission_scope"],
        position_match=kw["position_match"], quote_fresh=kw["quote_fresh"],
        update_fresh=kw["update_fresh"], plan_unexpired=kw["plan_unexpired"],
        replay_status=kw["replay_status"], operator_approval_completed=kw["operator_approval_completed"],
        permit_valid=kw["permit_valid"], lease_valid=kw["lease_valid"],
        disable_path=kw.get("disable_path"), order_management_enabled=kw["order_management_enabled"])


def _send_one(approved, transport, audit):
    """Send a single non-composite action via the FAKE transport (serialized dict, no protobuf)."""
    fields = _SERIALIZE[approved.action](approved)          # offline serialization; no protobuf here
    if audit is not None:
        audit.record("MGMT_REQUESTED", approved.plan_id, {"action": approved.action})
    res = transport.send_management(fields) or {}
    status = res.get("status")
    if status == "TIMEOUT":
        if audit is not None:
            audit.record("MGMT_RECONCILIATION_REQUIRED", approved.plan_id, {})
        rec = transport.reconcile(approved)                 # reconcile, DO NOT retry
        return {"final_state": "MGMT_RECONCILIATION_REQUIRED", "no_retry": True, "reconciled": rec}
    if status == "REJECTED":
        if audit is not None:
            audit.record("MGMT_REJECTED", approved.plan_id, {"error_code": res.get("error_code")})
        return {"final_state": "MGMT_REJECTED", "error_code": res.get("error_code")}
    if status == "ACCEPTED":
        if audit is not None:
            audit.record("MGMT_ACCEPTED", approved.plan_id, {"broker_ref": res.get("broker_ref")})
        # reconcile + compare requested vs returned
        diffs = transport.reconcile_compare(approved, res.get("returned") or {})
        if diffs:
            if audit is not None:
                audit.record("MGMT_STATE_MISMATCH", approved.plan_id, {"fields": diffs})
            return {"final_state": "MGMT_STATE_MISMATCH", "mismatch_fields": diffs,
                    "manual_review_required": True}
        return {"final_state": "MGMT_ACCEPTED", "action": approved.action}
    return {"final_state": "UNKNOWN_RESPONSE", "raw": res}


def send_management(approved, *, transport, account, endpoint_host, endpoint_port, permission_scope,
                    position_match, quote_fresh, update_fresh, plan_unexpired, replay_status,
                    operator_approval_completed, permit_valid, lease_valid, disable_path=None,
                    order_management_enabled=None, now_ms=0, audit=None):
    """One controlled management attempt. Firewall-gated; with ORDER_MANAGEMENT_ENABLED=False it
    terminates BEFORE constructing/serialising any management request."""
    ome = CFG.ORDER_MANAGEMENT_ENABLED if order_management_enabled is None else order_management_enabled
    kw = dict(account=account, endpoint_host=endpoint_host, endpoint_port=endpoint_port,
              permission_scope=permission_scope, position_match=position_match, quote_fresh=quote_fresh,
              update_fresh=update_fresh, plan_unexpired=plan_unexpired, replay_status=replay_status,
              operator_approval_completed=operator_approval_completed, permit_valid=permit_valid,
              lease_valid=lease_valid, disable_path=disable_path, order_management_enabled=ome)

    fw = _gate(approved, kw)
    if not fw.all_passed:
        if audit is not None:
            audit.record("MGMT_REJECTED", approved.plan_id, {"pre_send": True, "reason": "FIREWALL_BLOCKED"})
        return {"sent": False, "endpoint_called": False, "protobuf_constructed": False,
                "final_state": "NO_BROKER_ACTION_SENT", "reason": "FIREWALL_BLOCKED",
                "firewall": fw.as_dict(), "order_management_enabled": ome}

    # ---- only reachable with ORDER_MANAGEMENT_ENABLED=True (tests, fake transport) ----
    if approved.action != "COMPOSITE":
        r = _send_one(approved, transport, audit)
        return {"sent": True, "endpoint_called": True, **r}

    # COMPOSITE: sequential; STOP on first failure; never atomic
    completed = []
    for i, step in enumerate(approved.steps):
        sub_fw = _gate(step, {**kw, "position_match": position_match})
        if not sub_fw.all_passed:
            return {"sent": True, "final_state": "MANAGEMENT_PLAN_PARTIAL_SUCCESS", "completed_steps": completed,
                    "failed_step": i, "reason": "STEP_FIREWALL_BLOCKED", "new_approval_required": True,
                    "atomic": False}
        r = _send_one(step, transport, audit)
        completed.append({"step": i, "action": step.action, "final_state": r["final_state"]})
        if r["final_state"] != "MGMT_ACCEPTED":
            return {"sent": True, "final_state": "MANAGEMENT_PLAN_PARTIAL_SUCCESS", "completed_steps": completed,
                    "failed_step": i, "reason": r["final_state"], "new_approval_required": True,
                    "atomic": False}
    return {"sent": True, "final_state": "MGMT_ACCEPTED", "completed_steps": completed, "atomic": False}
