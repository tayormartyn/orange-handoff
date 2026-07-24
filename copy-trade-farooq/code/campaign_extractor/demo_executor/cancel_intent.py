"""
Cancellation intent detection + deterministic intent precedence. CANCEL_PENDING outranks generic
TRADE_UPDATE and NEW_SIGNAL, but TRADE_RESULT (a completed result card) outranks CANCEL_PENDING.
Isolated words (cancel/delete/remove/ignore) are NOT sufficient without clear instruction context.
Parsing NEVER calls broker transport — it only proposes an intent for human adjudication.
"""
from __future__ import annotations
import re

# explicit imperative cancellation phrases (instruction context, not bare words)
CANCEL_PHRASES = (
    "cancel gold", "cancel xauusd", "cancel previous order", "cancel the order", "cancel that order",
    "delete pending", "remove pending order", "remove the pending", "ignore that signal",
    "disregard previous gold entry", "disregard that gold", "scrap that setup", "scrap the setup",
    "cancel pending", "delete the pending order",
)
# bare words that must NOT alone trigger a cancellation
_ISOLATED = ("cancel", "delete", "remove", "ignore", "scrap", "disregard")
_CONTEXT = ("gold", "xauusd", "xau", "order", "pending", "signal", "entry", "setup", "previous", "that")

# deterministic precedence (highest first)
PRECEDENCE = ("TRADE_RESULT", "CANCEL_PENDING", "TRADE_UPDATE", "NEW_SIGNAL", "UNKNOWN")


def _compact(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def detect_cancel(text):
    """Returns (True, matched_phrase) for an explicit cancellation instruction, else (False, reason)."""
    t = (text or "").lower()
    tc = _compact(t)
    for p in CANCEL_PHRASES:
        if p in t or _compact(p) in tc:
            return True, p
    # a bare cancel word alone is NOT enough — require instruction context nearby
    if any(re.search(r"\b" + w + r"\b", t) for w in _ISOLATED):
        if not any(c in t for c in _CONTEXT):
            return False, "AMBIGUOUS_ISOLATED_WORD_NO_CONTEXT"
        return False, "ISOLATED_WORD_WITH_WEAK_CONTEXT_NEEDS_REVIEW"
    return False, "NO_CANCELLATION_INTENT"


def classify_intent(text, *, is_result_card=False, is_trade_update=False, is_new_signal=False):
    """Deterministic precedence: TRADE_RESULT > CANCEL_PENDING > TRADE_UPDATE > NEW_SIGNAL > UNKNOWN.
    A completed result card is NEVER reinterpreted as a cancellation or new signal."""
    if is_result_card:
        return "TRADE_RESULT"
    ok, _ = detect_cancel(text)
    if ok:
        return "CANCEL_PENDING"
    if is_trade_update:
        return "TRADE_UPDATE"
    if is_new_signal:
        return "NEW_SIGNAL"
    return "UNKNOWN"
