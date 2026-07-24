"""
Refinement 3 — deterministic leg-association pass.

A SEPARATE layer between validation and reduction. The LLM does NOT reason out which leg
an event targets; this pass associates a leg-targeting event (stop/close/partial/move/add)
to a leg ONLY when it is deterministically unambiguous, and otherwise LEAVES it
NEEDS_REVIEW. It never edits the frozen prompt or any locked truth.

Association rules (applied per campaign, over the ordered event stream):
  1. exactly ONE open leg at that point  -> associate to it
  2. the message names a literal price matching exactly ONE open leg's level -> associate

Hard carve-outs that ALWAYS stay NEEDS_REVIEW (never auto-associated), even with one leg:
  * ranking / sub-fill language: worst / best / highest / lowest entry, first/second entry,
    "on everything", "every trade" (the June 26 precedent). These pick a specific leg/fill
    the text does not pin down deterministically.
  * zero open legs, or 2+ open legs with no disambiguating literal price.

A wrong association is worse than NEEDS_REVIEW. This pass is intentionally conservative:
when in doubt, it does nothing and the event stays NEEDS_REVIEW for human resolution.
"""
from __future__ import annotations
import re

from schema import Status, EventType
from validator import _numbers_in, _normalize_num

LEG_TARGETING = {EventType.STOP_HIT.value, EventType.TP_HIT.value, EventType.CLOSE.value,
                 EventType.PARTIAL_CLOSE.value, EventType.PARTIAL_TP.value,
                 EventType.MOVE_STOP.value, EventType.ADD.value}
# terminal events close a leg (so it stops being "open" for later events)
TERMINAL = {EventType.STOP_HIT.value, EventType.TP_HIT.value, EventType.CLOSE.value}
LEG_OPENING = {EventType.ENTRY.value, EventType.RE_ENTER.value}

# ranking / multi-target language -> never deterministic
_RANKING_RE = re.compile(
    r"\b(worst|best|highest|lowest)\b|first entry|second entry|fist entry|on everything|every trade",
    re.I)

LEVEL_FIELDS = ("entry_low", "entry_high", "entry", "stop", "tp1", "tp2", "tp3")


def _fv(ev, name):
    f = ev.fields.get(name)
    if f is None or f.rejected:
        return None
    return f.value


def _leg_levels(ev):
    levels = set()
    for n in LEVEL_FIELDS:
        v = _fv(ev, n)
        if v is not None:
            levels.add(_normalize_num(str(v)))
    return levels


def _price_match(msg_text, open_legs):
    """Return the single leg id whose level exactly matches a number named in the message,
    or None if zero / more-than-one legs match (ambiguous -> NEEDS_REVIEW)."""
    named = _numbers_in(msg_text or "")
    if not named:
        return None
    hits = [lid for lid, lv in open_legs.items() if named & lv]
    return hits[0] if len(hits) == 1 else None


def resolve(events, archive):
    """events: ordered list[ValidatedEvent] for ONE campaign. Mutates leg_ref/status in
    place for deterministically-resolvable leg-targeting events. Returns a report list.

    The LLM does NOT decide legs: any leg_ref the extractor proposed on a leg-targeting
    event is IGNORED and re-derived here. Only ids this pass assigns to ENTRY/RE_ENTER
    legs are valid. Unresolved leg-targeting events are forced to NEEDS_REVIEW."""
    open_legs = {}            # leg_id -> set(level strings)
    counter = 0
    report = []

    def text_of(ev):
        return archive.get_text(ev.source_message_keys[0]) if ev.source_message_keys else ""

    # messages that themselves open a leg: their literal prices belong to the NEW leg's
    # declaration, so they must NOT be borrowed to disambiguate a stop/close (msg-360 trap).
    opening_msgs = {ev.source_message_keys[0] for ev in events
                    if ev.event_type in LEG_OPENING and ev.source_message_keys}

    for ev in events:
        et = ev.event_type

        if et in LEG_OPENING:
            counter += 1
            # the system assigns leg ids; the LLM does not name legs
            lid = ev.leg_ref if (ev.leg_ref and ev.leg_ref.startswith("leg-")) else f"leg-{counter}"
            ev.leg_ref = lid
            open_legs[lid] = _leg_levels(ev)
            continue

        if et not in LEG_TARGETING:
            continue

        # IGNORE whatever the LLM proposed; re-derive deterministically. Default: NEEDS_REVIEW.
        ev.leg_ref = None
        ev.status = Status.NEEDS_REVIEW.value
        msg = text_of(ev) or ""
        mid = ev.source_message_keys[0] if ev.source_message_keys else "?"

        # CARVE-OUT: ranking / sub-fill / multi-target language -> never auto-associate
        if _RANKING_RE.search(msg):
            report.append({"msg": mid, "event": et, "outcome": "NEEDS_REVIEW",
                           "reason": "ranking/sub-fill/multi-target language"})
            continue

        target = method = None
        if len(open_legs) == 1:
            target, method = next(iter(open_legs)), "single_open_leg"
        elif len(open_legs) >= 2 and mid not in opening_msgs:
            pm = _price_match(msg, open_legs)
            if pm:
                target, method = pm, "price_match"

        if target:
            ev.leg_ref = target
            ev.status = Status.ACCEPTED.value
            report.append({"msg": mid, "event": et, "outcome": "RESOLVED",
                           "leg": target, "method": method})
            if et in TERMINAL:
                open_legs.pop(target, None)
        else:
            reason = ("same message opens a leg; its prices belong to the new leg"
                      if (len(open_legs) >= 2 and mid in opening_msgs)
                      else f"{len(open_legs)} open legs, no disambiguating price")
            report.append({"msg": mid, "event": et, "outcome": "NEEDS_REVIEW", "reason": reason})

    return report
