"""
Layered idempotency / deduplication for fresh signals. Nothing is deleted — duplicate evidence is
preserved append-only and LINKED to the canonical signal.

Layer 1 — exact source duplication (message id, chat id, attachment hash, normalized raw-text hash)
Layer 2 — semantic signal fingerprint (provider, instrument, direction, intent, entry bounds, stop,
          targets, provider-timestamp bucket)
Layer 3 — execution identity (proposal id, deterministic clientOrderId, account id)
Layer 4 — broker reconciliation (existing pending orders / open positions / uncertain prior submit)
"""
from __future__ import annotations
import hashlib
import re

import config as CFG


def _norm_text(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def raw_text_hash(text):
    return hashlib.sha256(_norm_text(text).encode()).hexdigest()[:16]


def source_fingerprint(*, message_id=None, chat_id=None, attachment_sha256=None, raw_text=None):
    parts = [str(message_id), str(chat_id), str(attachment_sha256), raw_text_hash(raw_text) if raw_text else None]
    return {"message_id": message_id, "chat_id": chat_id, "attachment_sha256": attachment_sha256,
            "raw_text_hash": raw_text_hash(raw_text) if raw_text else None,
            "source_key": hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:16]}


def semantic_fingerprint(*, provider, instrument, direction, order_intent, entry_low, entry_high,
                         stop, targets=None, provider_ts_ms=None, bucket_seconds=None):
    bucket_seconds = CFG.DUPLICATE_SIGNAL_WINDOW_SECONDS if bucket_seconds is None else bucket_seconds
    tb = (provider_ts_ms // (bucket_seconds * 1000)) if provider_ts_ms is not None else None
    lo, hi = (min(entry_low, entry_high), max(entry_low, entry_high)) if (entry_low is not None and entry_high is not None) else (entry_low, entry_high)
    key = "|".join(str(x) for x in [(provider or "").lower(), (instrument or "").upper(),
                                     (direction or "").upper(), (order_intent or "").upper(),
                                     lo, hi, stop, tuple(sorted(targets or [])), tb])
    return {"provider": provider, "instrument": instrument, "direction": direction,
            "order_intent": order_intent, "entry_low": lo, "entry_high": hi, "stop": stop,
            "targets": list(targets or []), "provider_ts_bucket": tb,
            "semantic_key": hashlib.sha256(key.encode()).hexdigest()[:16]}


def execution_identity(*, proposal_id=None, client_order_id=None, account_id=None):
    return {"proposal_id": proposal_id, "client_order_id": client_order_id, "account_id": account_id}


ACTIVE_STATES = ("ACTIVE", "PROPOSED", "PENDING", "SUBMITTED", "ACCEPTED", "OPEN")


def check_duplicate(new, existing, *, now_ms, window_seconds=None):
    """new/existing carry source_fingerprint + semantic_fingerprint + fields + state + provider_ts_ms.
    Returns a decision dict. Exact-source or same-semantic within the window on an ACTIVE signal ->
    DUPLICATE_IGNORED (evidence preserved, linked). instrument+direction match but zone/stop/type/
    targets differ -> POSSIBLE_REISSUE_OR_AMENDMENT / HUMAN_REVIEW_REQUIRED."""
    window = CFG.DUPLICATE_SIGNAL_WINDOW_SECONDS if window_seconds is None else window_seconds
    for e in existing:
        if str(e.get("state", "")).upper() not in ACTIVE_STATES:
            continue
        # Layer 1 — exact source
        if new["source_fingerprint"]["source_key"] == e["source_fingerprint"]["source_key"]:
            return _dup(e, "EXACT_SOURCE_DUPLICATE")
        # Layer 3 — same execution identity
        nid, eid = new.get("execution_identity", {}), e.get("execution_identity", {})
        if nid.get("client_order_id") and nid["client_order_id"] == eid.get("client_order_id"):
            return _dup(e, "SAME_CLIENT_ORDER_ID")
        # Layer 2 — semantic, within window
        within = (new.get("provider_ts_ms") is None or e.get("provider_ts_ms") is None
                  or abs(new["provider_ts_ms"] - e["provider_ts_ms"]) <= window * 1000)
        if new["semantic_fingerprint"]["semantic_key"] == e["semantic_fingerprint"]["semantic_key"] and within:
            return _dup(e, "SEMANTIC_DUPLICATE_WITHIN_WINDOW")
        # instrument+direction match but material fields differ -> reissue/amendment
        nf, ef = new["semantic_fingerprint"], e["semantic_fingerprint"]
        if nf["instrument"] == ef["instrument"] and nf["direction"] == ef["direction"] and within:
            if (nf["entry_low"], nf["entry_high"], nf["stop"], nf["order_intent"], tuple(nf["targets"])) != \
               (ef["entry_low"], ef["entry_high"], ef["stop"], ef["order_intent"], tuple(ef["targets"])):
                return {"effective_state": "POSSIBLE_REISSUE_OR_AMENDMENT", "execution_eligible": False,
                        "blocking_reason": "HUMAN_REVIEW_REQUIRED", "canonical_signal": e.get("signal_id"),
                        "evidence_preserved": True}
    return {"effective_state": "UNIQUE", "execution_eligible": True, "blocking_reason": None}


def _dup(canonical, layer):
    return {"effective_state": "DUPLICATE_IGNORED", "execution_eligible": False,
            "blocking_reason": "DUPLICATE_IGNORED", "duplicate_layer": layer,
            "canonical_signal": canonical.get("signal_id"), "evidence_preserved": True,
            "no_order_proposal": True, "no_broker_action": True}
