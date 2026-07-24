"""
Stub/mock AI Evidence Reviewer — returns valid structured output WITHOUT calling any AI API.

Provider-neutral seam: a "reviewer" is any callable `review(pack: dict) -> dict` whose output must
pass schema.validate_reviewer_output(). Real providers (Fable 5 / Claude / Gemini / manual human
review) plug in behind the same seam later; the validator — not the provider — is the authority.

No network. No secrets. Observation-only.
"""
from __future__ import annotations
import re

import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import schema


# registry of available reviewer backends (extend later; stub is the only one implemented)
REVIEWERS = {}


def register(name):
    def deco(fn):
        REVIEWERS[name] = fn
        return fn
    return deco


@register("stub")
def stub_review(pack: dict) -> dict:
    """Deterministic, rule-based mock 'AI' extraction over the pack text. Good enough to exercise
    the schema/validator end-to-end; NOT a real model."""
    schema.validate_evidence_pack(pack)
    text = "\n".join(m.get("raw_text") or "" for m in pack["messages"])
    tl = text.lower()

    direction = None
    if re.search(r"\bsell\b|\bshort\b", tl):
        direction = "SHORT"
    if re.search(r"\bbuy\b|\blong\b", tl) and direction is None:
        direction = "LONG"

    m_entry = re.search(r"entry[^0-9]{0,12}([\d,\.]+)\s*[-–—?]{1,3}\s*([\d,\.]+)", text, re.I)
    entry_zone = f"{m_entry.group(1)}-{m_entry.group(2)}" if m_entry else None
    m_sl = re.search(r"\bsl\b[^0-9]{0,6}([\d,\.]+)|stop loss[^0-9]{0,6}([\d,\.]+)", text, re.I)
    sl = (m_sl.group(1) or m_sl.group(2)) if m_sl else None
    tp_levels = re.findall(r"tp\s*\d?\s*[:=]?\s*([\d,\.]{3,10})", text, re.I)
    claims = re.findall(r"(\d+\s*\+?\s*pips|full (?:tp|target) hit)", text, re.I)
    result_claim = "; ".join(claims) if claims else None

    contradictions = []
    if re.search(r"\bsell\b|\bshort\b", tl) and re.search(r"\bbuy\b|\blong\b", tl):
        contradictions.append("both long and short language present in pack text")

    missing = []
    if not entry_zone:
        missing.append("entry zone not found in text")
    if not sl:
        missing.append("SL not found in text")
    if not pack.get("ohlc_summary"):
        missing.append("no OHLC summary supplied — result claims are unverified")

    extracted = bool(direction and (entry_zone or sl))
    verdict = ("CONTRADICTORY" if contradictions else
               "EXTRACTED" if extracted else
               "UNCLEAR" if direction else "NEEDS_HUMAN_REVIEW")

    return {
        "pack_id": pack["pack_id"],
        "extracted_instrument": pack.get("instrument"),
        "direction": direction,
        "entry_zone": entry_zone,
        "sl": sl,
        "tp_levels": tp_levels,
        "result_claim": result_claim,
        "evidence_used": [m["message_id"] for m in pack["messages"]],
        "confidence": 0.6 if extracted else 0.3,
        "contradictions": contradictions,
        "missing_evidence": missing,
        "ohlc_required": bool(result_claim),   # a result claim always needs independent OHLC
        "verdict": verdict,
    }


def review(pack: dict, provider: str = "stub") -> dict:
    """Run a reviewer backend and pass its output through the fail-closed validator.
    The returned dict is validated + review-only-stamped. NEVER an executable signal."""
    fn = REVIEWERS.get(provider)
    if fn is None:
        raise ValueError(f"unknown reviewer provider '{provider}' (available: {sorted(REVIEWERS)})")
    raw = fn(pack)
    return schema.validate_reviewer_output(raw)
