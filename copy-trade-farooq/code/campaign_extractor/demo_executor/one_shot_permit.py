"""
One-shot activation permit — DESIGN + validation only (no permit is issued this phase). A permit
authorises exactly ONE approved fresh proposal. It is bound to account+signal+proposal+clientOrderId,
has a short expiry, is atomically consumed, cannot be reused, cannot approve a different proposal, and
is INSUFFICIENT on its own (ORDER_SENDING_ENABLED + the full firewall are still required). The
emergency-disable file overrides everything.
"""
from __future__ import annotations
import hashlib
from dataclasses import dataclass

import config as CFG
import disable_guard

PERMIT_TTL_MS = 60_000          # short expiry (60s)


@dataclass(frozen=True)
class OneShotPermit:
    permit_id: str
    account_id: int
    signal_id: str
    proposal_id: str
    client_order_id: str
    issued_at_ms: int
    expires_at_ms: int


def make_permit(*, account_id, signal_id, proposal_id, client_order_id, now_ms, ttl_ms=PERMIT_TTL_MS):
    raw = f"{account_id}|{signal_id}|{proposal_id}|{client_order_id}|{now_ms}"
    pid = "permit-" + hashlib.sha256(raw.encode()).hexdigest()[:20]
    return OneShotPermit(pid, account_id, signal_id, proposal_id, client_order_id, now_ms, now_ms + ttl_ms)


class PermitStore:
    """Atomic single-use ledger; a permit id can be consumed exactly once."""
    def __init__(self):
        self._consumed = set()

    def is_consumed(self, permit_id):
        return permit_id in self._consumed

    def consume(self, permit_id):
        if permit_id in self._consumed:
            return False                    # already consumed -> refuse
        self._consumed.add(permit_id)
        return True


def validate_permit(permit, *, account_id, signal_id, proposal_id, client_order_id, now_ms, store,
                    disable_path=None, fresh_signal=True):
    if disable_guard.is_disabled(disable_path):
        return False, "EMERGENCY_DISABLE_FILE_OVERRIDES_EVERYTHING"
    if not fresh_signal:
        return False, "STALE_OR_REPLAY_SIGNAL_INELIGIBLE"
    if now_ms > permit.expires_at_ms:
        return False, "PERMIT_EXPIRED"
    if store.is_consumed(permit.permit_id):
        return False, "PERMIT_ALREADY_CONSUMED"
    if permit.account_id != account_id:
        return False, "ACCOUNT_MISMATCH"
    if permit.signal_id != signal_id:
        return False, "SIGNAL_MISMATCH"
    if permit.proposal_id != proposal_id:
        return False, "PROPOSAL_MISMATCH"       # cannot approve a different proposal
    if permit.client_order_id != client_order_id:
        return False, "CLIENT_ORDER_ID_MISMATCH"
    return True, "OK"


def try_consume(permit, *, account_id, signal_id, proposal_id, client_order_id, now_ms, store,
                disable_path=None, fresh_signal=True, order_sending_enabled=None):
    """Validate then atomically consume. A permit is INSUFFICIENT alone — the caller must ALSO pass the
    full submission firewall and ORDER_SENDING_ENABLED=True. This phase never enables sending."""
    ose = CFG.ORDER_SENDING_ENABLED if order_sending_enabled is None else order_sending_enabled
    ok, reason = validate_permit(permit, account_id=account_id, signal_id=signal_id,
                                 proposal_id=proposal_id, client_order_id=client_order_id, now_ms=now_ms,
                                 store=store, disable_path=disable_path, fresh_signal=fresh_signal)
    if not ok:
        return {"consumed": False, "reason": reason, "order_sending_enabled": ose,
                "global_enable_sufficient": False}
    if not store.consume(permit.permit_id):
        return {"consumed": False, "reason": "PERMIT_ALREADY_CONSUMED"}
    return {"consumed": True, "reason": "OK", "order_sending_enabled": ose,
            "still_requires_full_firewall": True, "global_enable_sufficient": False}
