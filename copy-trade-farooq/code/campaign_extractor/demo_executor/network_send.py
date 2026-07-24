"""
The single network-send gate. The actual transmission method requires EVERY condition below; one
failure terminates BEFORE any network transmission (and before the protobuf is even constructed).
Because ORDER_SENDING_ENABLED=False, every attempt this phase terminates at the gate. There is no
live-endpoint fallback. Amend/close/cancel are not present.
"""
from __future__ import annotations

import config as CFG
import submission_firewall as SFW
import one_shot_permit as OSP
import order_request_adapter as ADAPTER
from models import Check, FirewallResult


def network_gate(*, approved, account, endpoint_host, endpoint_port, permission_scope, permit,
                 permit_store, quote_fresh, signal_fresh, proposal_unexpired, replay_status,
                 human_approval_completed, existing_order, expected_margin_ok=True,
                 provider_evidence_displayed=True, disable_path=None, order_sending_enabled=None,
                 now_ms=0):
    fw = SFW.submission_firewall(
        approved=approved, account=account, endpoint_host=endpoint_host, permission_scope=permission_scope,
        quote_fresh=quote_fresh, signal_fresh=signal_fresh, proposal_unexpired=proposal_unexpired,
        expected_margin_ok=expected_margin_ok, human_confirmed_signal=True,
        provider_evidence_displayed=provider_evidence_displayed, existing_order_for_id=existing_order,
        operator_approval_completed=human_approval_completed, disable_path=disable_path,
        order_sending_enabled=order_sending_enabled)

    permit_ok, permit_reason = (False, "NO_PERMIT")
    if permit is not None:
        permit_ok, permit_reason = OSP.validate_permit(
            permit, account_id=approved.account_id, signal_id=approved.signal_id,
            proposal_id=approved.proposal_id, client_order_id=approved.client_order_id, now_ms=now_ms,
            store=permit_store, disable_path=disable_path, fresh_signal=signal_fresh)

    extra = [
        Check("endpoint_demo_host", endpoint_host == CFG.DEMO_ENDPOINT_HOST, str(endpoint_host)),
        Check("endpoint_demo_port", endpoint_port == CFG.DEMO_ENDPOINT_PORT, str(endpoint_port)),
        Check("no_replay_status", replay_status != "REPLAY_VALIDATION_ONLY", str(replay_status)),
        Check("valid_unconsumed_permit", permit_ok, permit_reason),
    ]
    checks = list(fw.checks) + extra
    return FirewallResult(checks, all(c.passed for c in checks))


def send_new_order(*, approved, transport, account, endpoint_host, endpoint_port, permission_scope,
                   permit, permit_store, quote_fresh, signal_fresh, proposal_unexpired, replay_status,
                   human_approval_completed, expected_margin_ok=True, provider_evidence_displayed=True,
                   disable_path=None, order_sending_enabled=None, now_ms=0, audit=None):
    """One controlled transmission attempt. Terminates BEFORE constructing/sending unless the full
    gate passes. With ORDER_SENDING_ENABLED=False the gate can never pass -> no protobuf, no send."""
    ose = CFG.ORDER_SENDING_ENABLED if order_sending_enabled is None else order_sending_enabled

    existing = transport.find_order_by_client_id(approved.client_order_id) if transport else None
    gate = network_gate(
        approved=approved, account=account, endpoint_host=endpoint_host, endpoint_port=endpoint_port,
        permission_scope=permission_scope, permit=permit, permit_store=permit_store,
        quote_fresh=quote_fresh, signal_fresh=signal_fresh, proposal_unexpired=proposal_unexpired,
        replay_status=replay_status, human_approval_completed=human_approval_completed,
        existing_order=existing is not None, expected_margin_ok=expected_margin_ok,
        provider_evidence_displayed=provider_evidence_displayed, disable_path=disable_path,
        order_sending_enabled=ose, now_ms=now_ms)

    if not gate.all_passed:
        if audit is not None:
            audit.record("ORDER_REJECTED", approved.proposal_id,
                         {"pre_transmission": True, "reason": "NETWORK_GATE_BLOCKED"})
        return {"transmitted": False, "network_transmission_reached": False,
                "protobuf_constructed": False, "final_state": "NO_ORDER_SENT",
                "reason": "NETWORK_GATE_BLOCKED", "gate": gate.as_dict()}

    # ---- only reachable with ORDER_SENDING_ENABLED=True + valid permit (NOT this phase) ----
    if not permit_store.consume(permit.permit_id):            # atomic single-use
        return {"transmitted": False, "protobuf_constructed": False, "final_state": "NO_ORDER_SENT",
                "reason": "PERMIT_CONSUME_FAILED"}
    req = ADAPTER.build_new_order_request(approved)           # REAL protobuf (only on a passed gate)
    if audit is not None:
        audit.record("ORDER_REQUESTED", approved.proposal_id, {"client_order_id": approved.client_order_id})
    res = transport.send(req)                                 # real network transmission
    return {"transmitted": True, "protobuf_constructed": True, "final_state": "ORDER_REQUESTED",
            "broker_response": res}
