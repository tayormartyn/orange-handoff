"""
One-attempt activation lease. The one-shot permit is necessary but NOT sufficient: an ephemeral
lease authorises AT MOST ONE network-send attempt and the send gate then AUTOMATICALLY RELOCKS in
every terminal path (including exceptions) via a finally-equivalent fail-safe. The persistent
ORDER_SENDING_ENABLED is never left True. No lease is created here.
"""
from __future__ import annotations
import hashlib
from dataclasses import dataclass

import disable_guard

LEASE_TTL_MS = 30_000          # short
TERMINAL_STATES = ("ORDER_ACCEPTED", "ORDER_REJECTED", "ORDER_RECONCILIATION_REQUIRED",
                   "BROKER_STATE_MISMATCH", "NETWORK_EXCEPTION", "AUTHENTICATION_FAILURE")


@dataclass(frozen=True)
class OneAttemptActivationLease:
    lease_id: str
    account_id: int
    signal_id: str
    proposal_id: str
    client_order_id: str
    permit_id: str
    issued_at_ms: int
    expires_at_ms: int


def make_lease(*, account_id, signal_id, proposal_id, client_order_id, permit_id, now_ms,
               ttl_ms=LEASE_TTL_MS):
    raw = f"{account_id}|{signal_id}|{proposal_id}|{client_order_id}|{permit_id}|{now_ms}"
    lid = "lease-" + hashlib.sha256(raw.encode()).hexdigest()[:20]
    return OneAttemptActivationLease(lid, account_id, signal_id, proposal_id, client_order_id,
                                     permit_id, now_ms, now_ms + ttl_ms)


class LeaseState:
    """Runtime ledger: a lease can be consumed once and is always closed after the attempt."""
    def __init__(self):
        self._consumed, self._closed = set(), set()

    def is_consumed(self, lease_id):
        return lease_id in self._consumed

    def is_closed(self, lease_id):
        return lease_id in self._closed

    def consume(self, lease_id):
        if lease_id in self._consumed:
            return False
        self._consumed.add(lease_id)
        return True

    def close(self, lease_id):
        self._closed.add(lease_id)          # idempotent relock


def validate_lease(lease, *, account_id, signal_id, proposal_id, client_order_id, permit_id, now_ms,
                   state, disable_path=None, fresh_signal=True):
    if disable_guard.is_disabled(disable_path):
        return False, "EMERGENCY_DISABLE_FILE_OVERRIDES_EVERYTHING"
    if not fresh_signal:
        return False, "STALE_OR_REPLAY_SIGNAL_INELIGIBLE"
    if now_ms > lease.expires_at_ms:
        return False, "LEASE_EXPIRED"
    if state.is_consumed(lease.lease_id):
        return False, "LEASE_ALREADY_CONSUMED"
    if lease.account_id != account_id:
        return False, "ACCOUNT_MISMATCH"
    if lease.signal_id != signal_id:
        return False, "SIGNAL_MISMATCH"
    if lease.proposal_id != proposal_id:
        return False, "PROPOSAL_MISMATCH"       # cannot be transferred to another proposal
    if lease.client_order_id != client_order_id:
        return False, "CLIENT_ORDER_ID_MISMATCH"
    if lease.permit_id != permit_id:
        return False, "PERMIT_ID_MISMATCH"
    return True, "OK"


def execute_one_attempt(lease, *, send_fn, state, account_id, signal_id, proposal_id, client_order_id,
                        permit_id, now_ms, disable_path=None, fresh_signal=True):
    """Validate -> atomically consume -> ONE send attempt (transient authorization) -> ALWAYS relock.
    send_fn(order_sending_enabled=True) performs the single attempt. Whatever it returns or raises, the
    lease is closed and the send state returns to disabled."""
    ok, reason = validate_lease(lease, account_id=account_id, signal_id=signal_id,
                                proposal_id=proposal_id, client_order_id=client_order_id,
                                permit_id=permit_id, now_ms=now_ms, state=state,
                                disable_path=disable_path, fresh_signal=fresh_signal)
    if not ok:
        return {"attempted": False, "reason": reason, "activation_lease": "REJECTED",
                "order_sending_enabled_after": False, "send_gate": "DISABLED"}
    if not state.consume(lease.lease_id):
        return {"attempted": False, "reason": "LEASE_ALREADY_CONSUMED",
                "activation_lease": "CONSUMED_OR_CLOSED", "order_sending_enabled_after": False,
                "send_gate": "DISABLED"}
    result = {"final_state": "UNKNOWN"}
    try:
        result = send_fn(order_sending_enabled=True)        # the single transient attempt
    except Exception as e:                                  # noqa: BLE001
        result = {"final_state": "NETWORK_EXCEPTION", "error": type(e).__name__}
    finally:
        state.close(lease.lease_id)                         # fail-safe relock — ALWAYS runs
    return {"attempted": True, "final_state": result.get("final_state"),
            "activation_lease": "CONSUMED_OR_CLOSED", "order_sending_enabled_after": False,
            "send_gate": "DISABLED", "result": result}
