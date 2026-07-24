"""
Deterministic campaign reducer.

Replays the immutable, append-ordered ACCEPTED event stream to produce campaign state.
Events are NEVER mutated; state is a pure fold over the stream. Replaying the same stream
always yields the same state and the same state hash.

Invariants enforced here (the reducer-level frozen regressions):
  * A leg's terminal outcome (STOPPED / TP / CLOSED) is permanent — later events cannot
    reopen, flip, or erase it. A later winning RE_ENTER is a SEPARATE child leg.
  * Earlier losses are never netted away or removed by later gains — every leg persists.
  * COMMENTARY / screenshots never create a leg and never realise profit; only an explicit
    CLOSE/STOP/TP event changes a leg's status.
  * Percentages are never invented: PARTIAL_CLOSE moves the remaining fraction only when
    the validator supplied a deterministic value; otherwise the fraction is left as-is.
  * Impossible stop geometry is FLAGGED, never repaired (prices left untouched).
  * PROVIDER / SHADOW / DEMO tracks are reduced into separate, independent states.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Optional

from schema import EventType

TERMINAL = {"STOPPED", "TP", "CLOSED"}
LEG_STATUS_FOR = {
    EventType.STOP_HIT.value: "STOPPED",
    EventType.TP_HIT.value: "TP",
    EventType.CLOSE.value: "CLOSED",
}


@dataclass
class Leg:
    leg_id: str
    track: str
    direction: Optional[str] = None
    entry: Optional[object] = None
    stop: Optional[object] = None
    parent_leg_id: Optional[str] = None
    status: str = "OPEN"
    remaining_fraction: Optional[float] = 1.0
    partial_tp_count: int = 0                 # how many partial take-profits banked (non-terminal)
    flags: list = field(default_factory=list)
    opened_seq: Optional[int] = None
    closed_seq: Optional[int] = None
    opened_by_hash: Optional[str] = None
    closed_by_hash: Optional[str] = None
    realized_r: Optional[float] = None        # stays None unless deterministically known


@dataclass
class CampaignState:
    tracks: dict = field(default_factory=dict)   # track -> {leg_id -> Leg}
    anomalies: list = field(default_factory=list)

    def legs(self, track: str):
        return self.tracks.get(track, {})

    def all_legs(self):
        for t, legs in self.tracks.items():
            for leg in legs.values():
                yield leg

    def count(self, track: str, status: str) -> int:
        return sum(1 for leg in self.legs(track).values() if leg.status == status)

    def state_hash(self) -> str:
        payload = {
            t: [
                {k: v for k, v in sorted(asdict(leg).items())}
                for leg in [legs[lid] for lid in sorted(legs)]
            ]
            for t, legs in sorted(self.tracks.items())
        }
        return hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()


def _impossible_geometry(direction, entry, stop) -> bool:
    try:
        e, s = float(entry), float(stop)
    except (TypeError, ValueError):
        return False
    d = (direction or "").lower()
    if d in ("buy", "long"):
        return s >= e          # long stop must be BELOW entry
    if d in ("sell", "short"):
        return s <= e          # short stop must be ABOVE entry
    return False


def _fv(ev, name):
    f = ev.fields.get(name)
    if f is None or f.rejected:
        return None
    return f.value


def reduce(events) -> CampaignState:
    state = CampaignState()
    counters = {}

    for seq, ev in enumerate(events):
        track = ev.track or "SHADOW"
        legs = state.tracks.setdefault(track, {})
        et = ev.event_type

        if et in (EventType.ENTRY.value, EventType.RE_ENTER.value):
            counters[track] = counters.get(track, 0) + 1
            leg_id = ev.leg_ref or f"{track}-leg-{counters[track]}"
            if leg_id in legs:
                state.anomalies.append({"seq": seq, "issue": "duplicate leg id", "leg_id": leg_id})
                continue
            entry = _fv(ev, "entry")
            if entry is None:
                entry = _fv(ev, "entry_low")
            leg = Leg(
                leg_id=leg_id, track=track, direction=_fv(ev, "direction"),
                entry=entry, stop=_fv(ev, "stop"),
                parent_leg_id=ev.parent_ref if et == EventType.RE_ENTER.value else None,
                status="OPEN", opened_seq=seq, opened_by_hash=ev.accepted_hash(),
            )
            if _impossible_geometry(leg.direction, leg.entry, leg.stop):
                leg.flags.append("IMPOSSIBLE_STOP_GEOMETRY")   # flagged, NOT repaired
                state.anomalies.append({"seq": seq, "issue": "impossible stop geometry",
                                        "leg_id": leg_id, "entry": leg.entry, "stop": leg.stop})
            legs[leg_id] = leg

        elif et in LEG_STATUS_FOR:                              # STOP_HIT / TP_HIT / CLOSE
            leg = legs.get(ev.leg_ref)
            if leg is None:
                state.anomalies.append({"seq": seq, "issue": "event targets unknown leg",
                                        "leg_ref": ev.leg_ref, "event_type": et})
                continue
            if leg.status in TERMINAL:
                # terminal outcome is permanent — cannot be reopened, flipped, or erased
                state.anomalies.append({"seq": seq, "issue": "ignored mutation of terminal leg",
                                        "leg_id": leg.leg_id, "was": leg.status, "attempted": et})
                continue
            leg.status = LEG_STATUS_FOR[et]
            leg.closed_seq = seq
            leg.closed_by_hash = ev.accepted_hash()

        elif et in (EventType.PARTIAL_CLOSE.value, EventType.PARTIAL_TP.value):
            # Both are NON-terminal: the leg stays open after banking part of the move.
            # A partial take-profit ("tp 1") must NEVER end the leg.
            leg = legs.get(ev.leg_ref)
            if leg is None or leg.status in TERMINAL:
                continue
            rf = _fv(ev, "remaining_fraction")
            if rf is not None:                                  # never invent a percentage
                leg.remaining_fraction = rf
            if et == EventType.PARTIAL_TP.value:
                leg.partial_tp_count += 1
            leg.status = "PARTIAL"

        elif et == EventType.MOVE_STOP.value:
            leg = legs.get(ev.leg_ref)
            if leg is None or leg.status in TERMINAL:
                continue
            new_stop = _fv(ev, "stop")
            if new_stop is not None:
                leg.stop = new_stop
                if _impossible_geometry(leg.direction, leg.entry, leg.stop):
                    if "IMPOSSIBLE_STOP_GEOMETRY" not in leg.flags:
                        leg.flags.append("IMPOSSIBLE_STOP_GEOMETRY")

        elif et == EventType.ADD.value:
            leg = legs.get(ev.leg_ref)
            if leg is None or leg.status in TERMINAL:
                continue
            # size accounting deferred; status unchanged (still open)

        # COMMENTARY / CONDITIONAL: never create a leg, never realise profit -> no-op

    return state
