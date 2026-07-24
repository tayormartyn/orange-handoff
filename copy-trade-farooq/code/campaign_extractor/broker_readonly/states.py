"""
Brick 3 — authentication / connection state machine.

No state may be silently skipped. Every transition records prior, next, reason,
timestamp and adapter version. Invalid transitions fail closed (raise, no mutation).
The clock is injectable so deterministic replay produces identical logical hashes
(the logical hash deliberately EXCLUDES wall-clock timestamps).
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone

from .config import ADAPTER_VERSION

STATES = [
    "APP_NOT_APPROVED", "CREDENTIALS_MISSING", "AUTHORISATION_REQUIRED",
    "AUTHORISATION_CODE_RECEIVED", "TOKEN_EXCHANGE_REQUIRED", "TOKEN_AVAILABLE",
    "APPLICATION_AUTHENTICATED", "ACCOUNTS_DISCOVERED", "DEMO_ACCOUNT_SELECTED",
    "ACCOUNT_AUTHENTICATED", "READ_ONLY_READY", "AUTH_FAILED", "DISCONNECTED",
]
_LINEAR = STATES[:11]   # the happy path, in order

ALLOWED = {}
for _i, _s in enumerate(_LINEAR):
    nxt = set()
    if _i + 1 < len(_LINEAR):
        nxt.add(_LINEAR[_i + 1])          # exactly the next step — no skipping
    nxt.update({"AUTH_FAILED", "DISCONNECTED"})
    ALLOWED[_s] = nxt
ALLOWED["AUTH_FAILED"] = {"DISCONNECTED", "CREDENTIALS_MISSING"}
# reconnect paths after a loss (no skipping: must re-walk from a valid point)
ALLOWED["DISCONNECTED"] = {"CREDENTIALS_MISSING", "AUTHORISATION_REQUIRED",
                           "TOKEN_AVAILABLE", "APPLICATION_AUTHENTICATED"}


class InvalidTransition(Exception):
    pass


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


class ConnectionStateMachine:
    def __init__(self, clock=None, version: str = ADAPTER_VERSION,
                 initial: str = "APP_NOT_APPROVED"):
        if initial not in STATES:
            raise InvalidTransition(f"unknown initial state {initial}")
        self.version = version
        self._clock = clock or _utc_now_iso
        self.state = initial
        self.history = []

    def transition(self, to: str, reason: str):
        if to not in STATES:
            raise InvalidTransition(f"unknown state {to}")
        if to not in ALLOWED.get(self.state, set()):
            # fail closed: refuse, do NOT mutate state
            raise InvalidTransition(f"illegal transition {self.state} -> {to}")
        rec = {"prior": self.state, "next": to, "reason": reason,
               "timestamp": self._clock(), "version": self.version}
        self.history.append(rec)
        self.state = to
        return rec

    def get_connection_state(self) -> str:
        return self.state

    def logical_hash(self) -> str:
        seq = [(r["prior"], r["next"], r["reason"], r["version"]) for r in self.history]
        return hashlib.sha256(json.dumps(seq, sort_keys=True).encode("utf-8")).hexdigest()
