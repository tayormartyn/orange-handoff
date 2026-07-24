"""
ASSOC-1R deterministic candidate classifier. NO LLM / OCR / vision — pure keyword rules over
the preserved raw text. Ambiguity (instruction vs reported hit) is PRESERVED as metadata, not
silently resolved to the more favourable reading. Image-derived numbers are never produced.
"""
from __future__ import annotations
import os
import re

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_ASSOC = os.path.join(os.path.dirname(_HERE), "assoc")
for p in (_ASSOC,):
    if p not in _sys.path:
        _sys.path.insert(0, p)
from model import ManagementCandidate

FAROUK = "provider_farouk_001"
FAROUK_HANDLE = "seascalperfarouk"
CHANNEL = "-1001902136163"


def _body(text):
    # strip the "<handle> Posted in <topic>" header to inspect the actual message body
    return text.split("`Whale`", 1)[-1] if "`Whale`" in text else (
        text.split(" Posted in ", 1)[-1] if " Posted in " in text else text)


def classify(row):
    """Return (candidate_type, assoc_intent_or_None, metadata) deterministically."""
    text = row["raw_text"]
    low = _body(text).lower()
    meta = {}

    # follower / non-Farouk: no provider header at all
    if row["header_sender"] is None:
        return "FOLLOWER", None, {"reason": "no provider header (follower context)"}
    if row["header_sender"] != FAROUK_HANDLE:
        return "OTHER_PROVIDER", None, {"sender": row["header_sender"]}

    # original signal (campaign origin) — direction + explicit SL price
    if re.search(r"\b(sell|buy)\b", low) and re.search(r"\bsl\s*\d", low):
        return "ORIGINAL_SIGNAL", None, {"note": "campaign-origin signal, not a management msg"}

    # ---- management instructions ----
    if re.search(r"\bsl\s*(to|->)?\s*(entry|be)\b", low) or "stop to entry" in low:
        return "MANAGEMENT", "MOVE_STOP_TO_ENTRY", {}
    if "closing" in low and "lot" in low:
        amt = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*lot", low)
        dist = re.search(r"([0-9]+)\s*pips", low)
        return "MANAGEMENT", "PARTIAL_CLOSE_INSTRUCTION", {
            "provider_reported_amount": (amt.group(1) + " lot") if amt else None,
            "provider_claimed_distance": (dist.group(1) + " pips") if dist else None,
            "exact_fill": None, "broker_confirmed": False}
    if "take" in low and ("% off" in low or "%off" in low or re.search(r"take\s+\d+\s*%", low)):
        frac = re.search(r"(\d+)\s*%", low)
        return "MANAGEMENT", "PARTIAL_CLOSE_INSTRUCTION", {
            "provider_reported_fraction": (frac.group(1) + "%") if frac else None,
            "exact_fill": None, "broker_confirmed": False}
    if "tp now" in low:
        return "MANAGEMENT", "TP_HIT_REPORTED", {
            "target": "UNSPECIFIED", "close_fraction": None,
            "intent_ambiguity": "instruction_or_reported_hit_unresolved"}
    if re.search(r"\btp\s*1\b", low) or (re.search(r"\d+\s*pips\s*tp", low)):
        return "MANAGEMENT", "TP_HIT_REPORTED", {
            "intent_ambiguity": "instruction_or_reported_hit_unresolved"}

    # ---- non-management context ----
    if re.search(r"\b\d+\s*pips\b", low):                 # bare "100 pips !!!" milestone
        return "MILESTONE_CLAIM", None, {"note": "provider claim; no realised profit asserted"}
    if any(k in low for k in ("reason for the sell", "liquidity", "buy zone", "breakdown",
                              "entry zone", "order block", "fvg", "evolving")):
        return "ANALYSIS_ONLY", None, {"note": "rationale/analysis; no new campaign"}
    return "COMMENTARY", None, {"note": "general commentary"}


def build_candidate(row, intent, *, tracking_status, source_identity_approved, provider_id=FAROUK):
    return ManagementCandidate(
        source_message_uid=row["message_id"], provider_id=provider_id,
        management_intent=intent, source_message_timestamp=row["posted_at"],
        immutable_channel_id=CHANNEL, immutable_sender_id=row["header_sender"],
        source_platform="TELEGRAM",
        provider_tracking_status_at_message_time=tracking_status,
        source_identity_approved=source_identity_approved,
        raw_message_reference=row["message_id"],
        evidence_references=[row["raw_text_hash"]], provenance="LIVE_CAPTURED",
        parser_or_candidate_version="assoc-1r-classifier-0")
