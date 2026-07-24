"""
One-shot MANAGEMENT permit + one-attempt MANAGEMENT lease. Mirror of the entry-order permit/lease but
bound to a management plan. Both are necessary; the lease authorises AT MOST ONE amend/close/cancel
attempt and the management gate then AUTOMATICALLY RELOCKS in every terminal path (accepted, rejected,
timeout, mismatch, authentication failure, exception) via a finally-equivalent fail-safe. They
independently require ORDER_MANAGEMENT_ENABLED=True; the emergency-disable file overrides everything.
Neither is issued during this build.
"""
from __future__ import annotations
import hashlib
from dataclasses import dataclass

import config as CFG
import disable_guard

PERMIT_TTL_MS = 60_000
LEASE_TTL_MS = 30_000
TERMINAL_STATES = ("MGMT_ACCEPTED", "MGMT_REJECTED", "MGMT_RECONCILIATION_REQUIRED",
                   "MGMT_STATE_MISMATCH", "MGMT_NETWORK_EXCEPTION", "MGMT_AUTHENTICATION_FAILURE")


def _bind(account_id, signal_id, update_intake_id, plan_id, broker_ref):
    return f"{account_id}|{signal_id}|{update_intake_id}|{plan_id}|{broker_ref}"


@dataclass(frozen=True)
class OneShotManagementPermit:
    permit_id: str
    account_id: int
    parent_signal_id: str
    update_intake_id: str
    management_plan_id: str
    broker_ref: str                 # broker order or position id
    issued_at_ms: int
    expires_at_ms: int


@dataclass(frozen=True)
class OneAttemptManagementLease:
    lease_id: str
    account_id: int
    parent_signal_id: str
    update_intake_id: str
    management_plan_id: str
    broker_ref: str
    permit_id: str
    issued_at_ms: int
    expires_at_ms: int


def make_permit(*, account_id, parent_signal_id, update_intake_id, management_plan_id, broker_ref,
                now_ms, ttl_ms=PERMIT_TTL_MS):
    raw = _bind(account_id, parent_signal_id, update_intake_id, management_plan_id, broker_ref) + f"|{now_ms}"
    pid = "mpermit-" + hashlib.sha256(raw.encode()).hexdigest()[:20]
    return OneShotManagementPermit(pid, account_id, parent_signal_id, update_intake_id,
                                   management_plan_id, broker_ref, now_ms, now_ms + ttl_ms)


def make_lease(*, permit, now_ms, ttl_ms=LEASE_TTL_MS):
    raw = _bind(permit.account_id, permit.parent_signal_id, permit.update_intake_id,
                permit.management_plan_id, permit.broker_ref) + f"|{permit.permit_id}|{now_ms}"
    lid = "mlease-" + hashlib.sha256(raw.encode()).hexdigest()[:20]
    return OneAttemptManagementLease(lid, permit.account_id, permit.parent_signal_id,
                                     permit.update_intake_id, permit.management_plan_id,
                                     permit.broker_ref, permit.permit_id, now_ms, now_ms + ttl_ms)


class UseLedger:
    def __init__(self):
        self._used, self._closed = set(), set()

    def is_used(self, i):
        return i in self._used

    def is_closed(self, i):
        return i in self._closed

    def use(self, i):
        if i in self._used:
            return False
        self._used.add(i)
        return True

    def close(self, i):
        self._closed.add(i)


def validate_permit(permit, *, account_id, parent_signal_id, update_intake_id, management_plan_id,
                    broker_ref, now_ms, ledger, disable_path=None, fresh_update=True):
    if disable_guard.is_disabled(disable_path):
        return False, "EMERGENCY_DISABLE_FILE_OVERRIDES_EVERYTHING"
    if not fresh_update:
        return False, "STALE_OR_REPLAY_UPDATE_INELIGIBLE"
    if now_ms > permit.expires_at_ms:
        return False, "PERMIT_EXPIRED"
    if ledger.is_used(permit.permit_id):
        return False, "PERMIT_ALREADY_CONSUMED"
    if permit.account_id != account_id:
        return False, "ACCOUNT_MISMATCH"
    if permit.parent_signal_id != parent_signal_id:
        return False, "SIGNAL_MISMATCH"
    if permit.update_intake_id != update_intake_id:
        return False, "UPDATE_MISMATCH"
    if permit.management_plan_id != management_plan_id:
        return False, "PLAN_MISMATCH"                    # cannot transfer to another trade/plan
    if permit.broker_ref != broker_ref:
        return False, "BROKER_REF_MISMATCH"
    return True, "OK"


def validate_lease(lease, *, now_ms, ledger, disable_path=None, fresh_update=True):
    if disable_guard.is_disabled(disable_path):
        return False, "EMERGENCY_DISABLE_FILE_OVERRIDES_EVERYTHING"
    if not fresh_update:
        return False, "STALE_OR_REPLAY_UPDATE_INELIGIBLE"
    if now_ms > lease.expires_at_ms:
        return False, "LEASE_EXPIRED"
    if ledger.is_used(lease.lease_id):
        return False, "LEASE_ALREADY_CONSUMED"
    return True, "OK"


def execute_one_attempt(lease, *, send_fn, ledger, now_ms, disable_path=None, fresh_update=True):
    """Validate -> atomically consume the lease -> ONE attempt -> ALWAYS relock. Whatever send_fn
    returns or raises, the lease is closed and the management gate returns to disabled."""
    ok, reason = validate_lease(lease, now_ms=now_ms, ledger=ledger, disable_path=disable_path,
                                fresh_update=fresh_update)
    if not ok:
        return {"attempted": False, "reason": reason, "management_lease": "REJECTED",
                "order_management_enabled_after": False, "management_gate": "DISABLED"}
    if not ledger.use(lease.lease_id):
        return {"attempted": False, "reason": "LEASE_ALREADY_CONSUMED",
                "management_lease": "CONSUMED_OR_CLOSED", "order_management_enabled_after": False,
                "management_gate": "DISABLED"}
    result = {"final_state": "UNKNOWN"}
    try:
        result = send_fn(order_management_enabled=True)  # single transient attempt
    except Exception as e:                               # noqa: BLE001
        result = {"final_state": "MGMT_NETWORK_EXCEPTION", "error": type(e).__name__}
    finally:
        ledger.close(lease.lease_id)                     # fail-safe relock — ALWAYS runs
    return {"attempted": True, "final_state": result.get("final_state"),
            "management_lease": "CONSUMED_OR_CLOSED", "order_management_enabled_after": False,
            "management_gate": "DISABLED", "result": result}
