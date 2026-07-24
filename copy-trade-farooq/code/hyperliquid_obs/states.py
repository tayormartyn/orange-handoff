"""
H1 — WebSocket observation connection state machine.

No state may be silently skipped. Every transition records prior/next/reason/timestamp/
version. Invalid transitions fail closed (raise, no mutation). The clock is injectable so
deterministic replay yields identical logical hashes (the logical hash EXCLUDES wall-clock).

Reconnect is first-class: after a drop/stall/error the machine must re-walk from CONNECTING;
it can never jump straight back to STREAMING.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone

from . import OBSERVER_VERSION

STATES = [
    "DISCONNECTED", "CONNECTING", "CONNECTED", "META_LOADED", "SYMBOL_VERIFIED",
    "SUBSCRIBED", "STREAMING", "STALLED", "CLOSING", "CLOSED", "ERROR",
]
_LINEAR = STATES[:7]   # DISCONNECTED .. STREAMING (happy path, in order)

ALLOWED = {}
for _i, _s in enumerate(_LINEAR):
    nxt = set()
    if _i + 1 < len(_LINEAR):
        nxt.add(_LINEAR[_i + 1])          # exactly the next step — no skipping
    nxt.update({"STALLED", "ERROR", "CLOSING"})
    ALLOWED[_s] = nxt
# stall during streaming, then resume or reconnect
ALLOWED["STREAMING"].update({"STALLED", "ERROR", "CLOSING"})
ALLOWED["STALLED"] = {"STREAMING", "CONNECTING", "ERROR", "CLOSING"}
# error/reconnect must re-walk from CONNECTING (cannot leap back into STREAMING)
ALLOWED["ERROR"] = {"CONNECTING", "CLOSING", "DISCONNECTED"}
ALLOWED["CLOSING"] = {"CLOSED"}
ALLOWED["CLOSED"] = {"CONNECTING", "DISCONNECTED"}
ALLOWED["DISCONNECTED"] = {"CONNECTING"}


class InvalidTransition(Exception):
    pass


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


class WSConnectionStateMachine:
    def __init__(self, clock=None, version: str = OBSERVER_VERSION, initial: str = "DISCONNECTED"):
        if initial not in STATES:
            raise InvalidTransition(f"unknown initial state {initial}")
        self.version = version
        self._clock = clock or _utc_now_iso
        self.state = initial
        self.history = []
        self.reconnects = 0

    def transition(self, to: str, reason: str):
        if to not in STATES:
            raise InvalidTransition(f"unknown state {to}")
        if to not in ALLOWED.get(self.state, set()):
            raise InvalidTransition(f"illegal transition {self.state} -> {to}")
        if to == "CONNECTING" and self.state in ("STALLED", "ERROR", "CLOSED"):
            self.reconnects += 1
        rec = {"prior": self.state, "next": to, "reason": reason,
               "timestamp": self._clock(), "version": self.version}
        self.history.append(rec)
        self.state = to
        return rec

    def get_state(self) -> str:
        return self.state

    def logical_hash(self) -> str:
        seq = [(r["prior"], r["next"], r["reason"], r["version"]) for r in self.history]
        return hashlib.sha256(json.dumps(seq, sort_keys=True).encode("utf-8")).hexdigest()
