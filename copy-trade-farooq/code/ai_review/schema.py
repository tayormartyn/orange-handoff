"""
AI Evidence Reviewer — schemas + fail-closed validation (provider-neutral, observation-only).

The AI lane may EXTRACT / REVIEW / EXPLAIN / COMPARE / FLAG CONTRADICTIONS in evidence packs.
It has NO execution surface: any reviewer output containing a forbidden execution/broker field is
REJECTED, and every accepted output is stamped review-only. Deterministic validators (this module)
are the authority — AI output is advisory input to humans, never a signal.

No AI API is called here. No secrets. NOT_INTEGRATION_READY unchanged.
"""
from __future__ import annotations

# ---- reviewer verdicts (review-only; no trade-ready verdict exists) ----
VERDICTS = ("EXTRACTED", "UNCLEAR", "CONTRADICTORY", "NEEDS_HUMAN_REVIEW")

# ---- forbidden execution surface: any key containing one of these substrings is rejected ----
FORBIDDEN_KEY_SUBSTRINGS = (
    "order", "order_type", "lot_size", "lot", "risk", "account_id", "account",
    "broker", "ctrader", "qst", "permit", "lease", "execute", "execution",
    "trade_now", "route", "position_size", "qty",
)

# ---- input schema: one evidence pack ----
EVIDENCE_PACK_REQUIRED = ("pack_id", "instrument", "source_channel", "messages")
EVIDENCE_MESSAGE_REQUIRED = ("message_id", "timestamp_utc", "raw_text")
EVIDENCE_PACK_OPTIONAL = ("media", "ohlc_summary", "tv_alert_context", "notes")
# media items: {"message_id", "sha256", "path"}

# ---- output schema: reviewer result ----
OUTPUT_REQUIRED = (
    "pack_id", "extracted_instrument", "direction", "entry_zone", "sl", "tp_levels",
    "result_claim", "evidence_used", "confidence", "contradictions", "missing_evidence",
    "ohlc_required", "verdict",
)
# stamped on every accepted output (hard-wired, not provider-supplied):
SAFETY_STAMP = {
    "review_only": True,
    "executable": False,
    "trade_ready": False,
    "observation_only": True,
}


class ReviewerOutputRejected(ValueError):
    """Raised when a reviewer output violates the safety contract or schema."""


def _walk_keys(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield f"{path}.{k}" if path else str(k)
            yield from _walk_keys(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_keys(v, f"{path}[{i}]")


def validate_evidence_pack(pack: dict) -> dict:
    """Validate one evidence pack (input side). Returns the pack. Raises ValueError on problems."""
    if not isinstance(pack, dict):
        raise ValueError("evidence pack must be a dict")
    for f in EVIDENCE_PACK_REQUIRED:
        if f not in pack:
            raise ValueError(f"evidence pack missing required field: {f}")
    if not isinstance(pack["messages"], list) or not pack["messages"]:
        raise ValueError("evidence pack needs a non-empty messages list")
    for i, m in enumerate(pack["messages"]):
        for f in EVIDENCE_MESSAGE_REQUIRED:
            if f not in m:
                raise ValueError(f"messages[{i}] missing required field: {f}")
    for item in pack.get("media") or []:
        for f in ("message_id", "sha256", "path"):
            if f not in item:
                raise ValueError(f"media item missing required field: {f}")
    return pack


def validate_reviewer_output(out: dict) -> dict:
    """FAIL-CLOSED validation of a reviewer (AI or human or stub) output.

    1. rejects any forbidden execution/broker key anywhere in the structure;
    2. enforces the output schema + verdict enum;
    3. stamps the review-only safety fields (overwriting anything the provider sent).
    Returns a NEW dict (validated + stamped). Raises ReviewerOutputRejected on violation.
    """
    if not isinstance(out, dict):
        raise ReviewerOutputRejected("reviewer output must be a dict")

    # (1) forbidden execution surface — checked over EVERY nested key
    for keypath in _walk_keys(out):
        leaf = keypath.split(".")[-1].split("[")[0].lower()
        for bad in FORBIDDEN_KEY_SUBSTRINGS:
            if bad in leaf:
                raise ReviewerOutputRejected(
                    f"forbidden execution-surface field in reviewer output: '{keypath}'")

    # (2) schema
    for f in OUTPUT_REQUIRED:
        if f not in out:
            raise ReviewerOutputRejected(f"reviewer output missing required field: {f}")
    if out["verdict"] not in VERDICTS:
        raise ReviewerOutputRejected(f"invalid verdict '{out['verdict']}' (allowed: {VERDICTS})")
    if not isinstance(out["tp_levels"], list):
        raise ReviewerOutputRejected("tp_levels must be a list")
    conf = out["confidence"]
    if not (isinstance(conf, (int, float)) and 0.0 <= float(conf) <= 1.0):
        raise ReviewerOutputRejected("confidence must be a number in [0,1]")
    if not isinstance(out["ohlc_required"], bool):
        raise ReviewerOutputRejected("ohlc_required must be a bool")

    # (3) stamp review-only safety fields (authority: this validator, not the provider)
    clean = dict(out)
    clean.update(SAFETY_STAMP)
    return clean
