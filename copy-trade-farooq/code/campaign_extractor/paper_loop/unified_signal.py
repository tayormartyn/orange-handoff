"""
Versioned UnifiedSignal + validation. Human confirmation creates ONLY a UnifiedSignal (never a
fill/order/outcome/R/PL). Missing or ambiguous mandatory fields -> NEEDS_REVIEW with explicit
reasons. Providers are isolated; instrument must be Gold for the broker-observation loop.
"""
from __future__ import annotations
import hashlib
import json

from paper_const import (SCHEMA_VERSION, PROVIDERS, SOURCE_TYPES, DIRECTIONS)

GOLD = ("XAUUSD", "GOLD", "XAU")
FIELDS = ("schema_version", "provider_id", "source_channel_id", "source_message_id",
          "source_message_timestamp", "listener_received_at", "parsed_at", "source_type",
          "instrument", "direction", "entry_low", "entry_high", "stop_price", "target_prices",
          "source_evidence_references", "human_confirmed", "reviewer_reference",
          "confirmation_timestamp", "candidate_status", "validation_errors")


def _num(v):
    try:
        from decimal import Decimal
        return Decimal(str(v))
    except Exception:
        return None


def build_unified(**kw):
    sig = {f: kw.get(f) for f in FIELDS}
    sig["schema_version"] = SCHEMA_VERSION
    return sig


def validate(sig):
    """Return (candidate_status, unified, errors). candidate_status in
    VALID_FOR_OBSERVATION | NEEDS_REVIEW. Fail closed with explicit reasons."""
    e = []
    if sig.get("provider_id") not in PROVIDERS:
        e.append("UNCERTAIN_PROVIDER")
    if str(sig.get("instrument", "")).upper() not in GOLD:
        e.append("UNSUPPORTED_ASSET")
    if str(sig.get("direction", "")).upper() not in DIRECTIONS:
        e.append("AMBIGUOUS_DIRECTION")
    lo, hi = sig.get("entry_low"), sig.get("entry_high")
    if lo is None or hi is None or str(lo).strip() == "" or str(hi).strip() == "":
        e.append("ENTRY_RANGE_MISSING")
    else:
        dlo, dhi = _num(lo), _num(hi)
        if dlo is None or dhi is None or dlo <= 0 or dhi <= 0:
            e.append("ENTRY_RANGE_INVALID")
    sp = sig.get("stop_price")
    if sp is not None and str(sp).strip() != "":
        dsp = _num(sp)
        dlo, dhi = _num(sig.get("entry_low")), _num(sig.get("entry_high"))
        if dsp is None or dsp <= 0:
            e.append("INVALID_STOP_GEOMETRY")
        elif dlo is not None and dhi is not None:               # BUY stop below, SELL stop above
            d = str(sig.get("direction", "")).upper()
            if d == "BUY" and dsp >= min(dlo, dhi):
                e.append("INVALID_STOP_GEOMETRY")
            if d == "SELL" and dsp <= max(dlo, dhi):
                e.append("INVALID_STOP_GEOMETRY")
    if not sig.get("source_evidence_references"):
        e.append("MISSING_EVIDENCE")
    if not sig.get("listener_received_at"):
        e.append("MISSING_LISTENER_RECEIVED_AT")
    if not sig.get("parsed_at"):
        e.append("MISSING_PARSED_AT")
    if sig.get("human_confirmed") is not True:
        e.append("NOT_HUMAN_CONFIRMED")
    if sig.get("source_type") not in SOURCE_TYPES:
        e.append("UNKNOWN_SOURCE_TYPE")

    out = dict(sig)
    out["validation_errors"] = e
    out["candidate_status"] = "VALID_FOR_OBSERVATION" if not e else "NEEDS_REVIEW"
    return out["candidate_status"], out, e


def snapshot_hash(sig):
    keys = [f for f in FIELDS if f != "validation_errors"]
    return hashlib.sha256(json.dumps({k: str(sig.get(k)) for k in keys}, sort_keys=True)
                          .encode()).hexdigest()
