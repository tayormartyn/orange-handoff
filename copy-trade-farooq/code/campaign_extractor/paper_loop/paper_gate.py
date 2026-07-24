"""
Thin deterministic PAPER decision gate — a wrapper AROUND the existing Q4A kernel (imported
unchanged). Validates the UnifiedSignal, then maps Q4A's dual-anchor result to a PAPER status.
Preserves all Q4A rules (BUY->ASK, SELL->BID, Decimal, inclusive range, no interpolation, no
crossing sessions, both anchors retained). NO_COVERAGE stays PAPER_UNKNOWN, never REJECT.
"""
from __future__ import annotations
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_Q4 = os.path.join(os.path.dirname(_HERE), "q4_align")
for p in (_Q4, _HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import kernel as q4a                                   # existing Q4A kernel, UNCHANGED
import unified_signal as us
from paper_const import PAPER_UNKNOWN_REASONS, NEEDS_REVIEW_REASONS


def _to_q4a(sig):
    ref = sig.get("source_evidence_references")
    return {"source_telegram_message_id": sig.get("source_message_id"),
            "source_evidence_ref": ref[0] if isinstance(ref, (list, tuple)) and ref else ref,
            "asset": sig.get("instrument"), "direction": sig.get("direction"),
            "entry_low": sig.get("entry_low"), "entry_high": sig.get("entry_high"),
            "telegram_posted_at": sig.get("source_message_timestamp"),
            "listener_received_at": sig.get("listener_received_at"),
            "parsed_at": sig.get("parsed_at"), "human_confirmed": sig.get("human_confirmed")}


def _map_anchor(anchor):
    """Map one Q4A anchor result to a paper status contribution."""
    res = anchor.get("result")
    if res == "INSIDE_ZONE":
        return "PAPER_READY", None
    if res == "OUTSIDE_ZONE":
        return "PAPER_OUTSIDE_ZONE", None
    reason = anchor.get("reason")
    if reason in NEEDS_REVIEW_REASONS:
        return "NEEDS_REVIEW", reason
    return "PAPER_UNKNOWN", reason                     # incl. NO_COVERAGE (never REJECT)


def decide(sig, quotes, config=None):
    """Return the paper decision. Signal problems -> NEEDS_REVIEW (before Q4A). Otherwise run Q4A
    and derive the status from the ACTIONABLE-system anchor; both anchors are retained."""
    status, unified, errors = us.validate(sig)
    if status == "NEEDS_REVIEW":
        return {"status": "NEEDS_REVIEW", "reason": errors[0] if errors else "NEEDS_REVIEW",
                "validation_errors": errors, "delivery": None, "actionable": None,
                "unified": unified, "q4a_config_version": None}

    r = q4a.align(_to_q4a(unified), quotes, config)
    delivery, actionable = r["delivery"], r["actionable"]
    paper_status, reason = _map_anchor(actionable)     # actionable-system anchor drives the status
    return {"status": paper_status, "reason": reason,
            "delivery": delivery, "actionable": actionable,
            "timing": r.get("timing"), "unified": unified,
            "q4a_config_version": r.get("config_version"), "labels": r.get("labels"),
            "validation_errors": []}
