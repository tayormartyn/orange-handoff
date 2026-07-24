"""
Deterministic evidence validator — plain rule-based code, NO AI.

Turns a CandidateEvent (proposed by the LLM) into a ValidatedEvent that is safe to
store. Core guarantees:

  * Every source message must exist in the archive.
  * Every evidence quote must be LITERALLY present in its cited message.
  * A numeric field value is accepted ONLY if it appears literally in verified text,
    OR is produced by the deterministic conversion allowlist (schema.SIZE/REMAINING).
  * Qualitative size wording ("small size", "low lot") => numeric NULL,
    size_quality = QUALITATIVE_ONLY. Never guessed.
  * Field-level rejection: a valid STOP_HIT survives even if its stop price is unknown.
  * Ambiguous campaign/leg association => NEEDS_REVIEW (cannot mutate accepted state).
  * No cross-message synthesis unless every contributing message key is recorded.
  * Telegram text is EVIDENCE only — never executed as instructions to the extractor.
  * Idempotent: identical evidence + versions => identical candidate & accepted hashes.

The validator is given an ArchiveReader (read-only). It never writes anything.
"""
from __future__ import annotations
import re
import sqlite3
from typing import Optional

from schema import (
    CandidateEvent, ValidatedEvent, ValidatedField, Status, Provenance, EventType,
    SizeQuality, SIZE_CONVERSIONS, REMAINING_CONVERSIONS, QUALITATIVE_SIZE_PHRASES,
)

VALIDATOR_VERSION = "validator-0.1.0"

# numeric tokens: 4091.80, 0.25, 2,015.5, 90%  (commas tolerated, percent captured).
# The comma-grouped alternative REQUIRES a thousands group (+), otherwise "4000" would
# match only its first 3 digits ("400"); plain runs fall through to the second alternative.
_NUM_RE = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?%?|\d+(?:\.\d+)?%?")

# fields whose value is a price/lot number and therefore subject to literal-numeric proof
NUMERIC_FIELDS = {"entry", "entry_low", "entry_high", "stop", "tp1", "tp2", "tp3",
                  "exit", "price", "lot", "size", "remaining_fraction"}

# fields that may legitimately carry an image-derived value (and thus may be NULL/MEDIA_MISSING)
IMAGE_PRONE_FIELDS = {"entry", "entry_low", "entry_high", "stop", "tp1", "tp2", "tp3",
                      "exit", "price", "lot"}


class ArchiveReader:
    """Read-only accessor over signal_archive.db (or any {message_key: raw_text} map)."""

    def __init__(self, db_path: Optional[str] = None, mem_map: Optional[dict] = None):
        self._mem = mem_map
        self._con = None
        if db_path is not None:
            self._con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    def get_text(self, message_key: str) -> Optional[str]:
        if self._mem is not None:
            return self._mem.get(message_key)
        cur = self._con.cursor()
        row = cur.execute(
            "select raw_text from raw_message_versions where message_key=? "
            "order by version_number desc limit 1", (message_key,)
        ).fetchone()
        return row[0] if row else None


def _normalize_num(tok: str) -> str:
    return tok.replace(",", "").rstrip("%")


def _numbers_in(text: str) -> set:
    return {_normalize_num(t) for t in _NUM_RE.findall(text or "")}


def _quote_present(quote: str, text: str) -> bool:
    """Exact substring; whitespace-normalized fallback (never fuzzier than that)."""
    if not quote:
        return False
    if quote in (text or ""):
        return True
    norm = lambda s: re.sub(r"\s+", " ", s or "").strip()
    return norm(quote) in norm(text)


def validate(candidate: CandidateEvent, archive: ArchiveReader) -> ValidatedEvent:
    reasons = []
    fields = {}
    status = Status.ACCEPTED

    # ---- 1. sender gate (defense in depth; gate also applied pre-extraction)
    from sender_gate import is_farouk
    meta = dict(track=candidate.track, leg_ref=candidate.leg_ref, parent_ref=candidate.parent_ref)
    if not is_farouk(candidate.sender_handle):
        return ValidatedEvent(
            event_type=candidate.event_type, status=Status.REJECTED.value, fields={},
            source_message_keys=candidate.source_message_keys,
            sender_handle=candidate.sender_handle, versions=candidate.versions,
            reasons=["non-Farouk sender cannot produce campaign-state-mutating events"],
            candidate_hash=candidate.canonical_hash(), **meta,
        )

    # ---- 2. every source message must exist
    texts = {}
    for mk in candidate.source_message_keys:
        t = archive.get_text(mk)
        if t is None:
            return ValidatedEvent(
                event_type=candidate.event_type, status=Status.REJECTED.value, fields={},
                source_message_keys=candidate.source_message_keys,
                sender_handle=candidate.sender_handle, versions=candidate.versions,
                reasons=[f"source message not found: {mk}"],
                candidate_hash=candidate.canonical_hash(),
            )
        texts[mk] = t

    # ---- 3. no cross-message synthesis unless every cited message is recorded
    evidence_keys = {e.message_key for e in candidate.evidence}
    unrecorded = evidence_keys - set(candidate.source_message_keys)
    if unrecorded:
        return ValidatedEvent(
            event_type=candidate.event_type, status=Status.REJECTED.value, fields={},
            source_message_keys=candidate.source_message_keys,
            sender_handle=candidate.sender_handle, versions=candidate.versions,
            reasons=[f"evidence cites unrecorded messages: {sorted(unrecorded)}"],
            candidate_hash=candidate.canonical_hash(), **meta,
        )

    # ---- 4. every evidence quote must be literally present
    for e in candidate.evidence:
        if e.is_image_field:
            # image evidence cannot be verified from text; image bytes were never captured
            # -> treated as unresolved. Recorded, but cannot prove a numeric (see field loop).
            reasons.append(f"image-field evidence in {e.message_key} unverifiable (MEDIA_MISSING)")
            continue
        if not _quote_present(e.quote, texts.get(e.message_key, "")):
            return ValidatedEvent(
                event_type=candidate.event_type, status=Status.REJECTED.value, fields={},
                source_message_keys=candidate.source_message_keys,
                sender_handle=candidate.sender_handle, versions=candidate.versions,
                reasons=[f"quote not literally present in {e.message_key}: {e.quote!r}"],
                candidate_hash=candidate.canonical_hash(), **meta,
            )

    verified_text = "\n".join(texts[mk] for mk in candidate.source_message_keys)
    verified_text_low = verified_text.lower()
    available_numbers = _numbers_in(verified_text)
    image_field_keys = {e.message_key for e in candidate.evidence if e.is_image_field}

    # ---- 5. field-level validation (independent; event survives partial rejection)
    for name, raw_val in candidate.proposed_fields.items():
        fields[name] = _validate_field(
            name, raw_val, verified_text_low, available_numbers, bool(image_field_keys), reasons
        )

    # ---- 6. ambiguous leg association -> NEEDS_REVIEW (cannot mutate accepted state)
    # Events that target an EXISTING leg must say which one; an unknown target cannot
    # silently pick a leg. ENTRY/RE_ENTER open legs; COMMENTARY/CONDITIONAL never mutate.
    LEG_TARGETING = {EventType.STOP_HIT.value, EventType.TP_HIT.value, EventType.CLOSE.value,
                     EventType.PARTIAL_CLOSE.value, EventType.PARTIAL_TP.value,
                     EventType.ADD.value, EventType.MOVE_STOP.value}
    if candidate.event_type in LEG_TARGETING and \
            candidate.leg_ref in (None, "", "AMBIGUOUS", "UNKNOWN"):
        status = Status.NEEDS_REVIEW
        reasons.append("leg association ambiguous -> NEEDS_REVIEW")

    # ---- 7. conditional / commentary never mutate state
    if candidate.event_type in (EventType.CONDITIONAL.value, EventType.COMMENTARY.value):
        reasons.append(f"{candidate.event_type} creates no leg / does not mutate state")

    return ValidatedEvent(
        event_type=candidate.event_type, status=status.value, fields=fields,
        source_message_keys=candidate.source_message_keys,
        sender_handle=candidate.sender_handle, versions={**candidate.versions, "validator": VALIDATOR_VERSION},
        reasons=reasons, candidate_hash=candidate.canonical_hash(), **meta,
    )


def _validate_field(name, raw_val, verified_text_low, available_numbers,
                    has_image_evidence, reasons) -> ValidatedField:
    # qualitative size wording -> numeric NULL, flagged QUALITATIVE_ONLY
    if name in ("size", "lot"):
        if any(p in verified_text_low for p in QUALITATIVE_SIZE_PHRASES):
            reasons.append(f"{name}: qualitative size wording -> numeric NULL")
            return ValidatedField(name, None, Provenance.UNSUPPORTED.value, rejected=True,
                                  reason=f"{SizeQuality.QUALITATIVE_ONLY.value}")
        # deterministic size conversions (half/quarter)
        for phrase, val in SIZE_CONVERSIONS.items():
            if phrase in verified_text_low:
                return ValidatedField(name, val, Provenance.DETERMINISTIC_CONVERSION.value)

    if name == "remaining_fraction":
        for phrase, val in REMAINING_CONVERSIONS.items():
            if phrase in verified_text_low:
                return ValidatedField(name, val, Provenance.DETERMINISTIC_CONVERSION.value)
        # not derivable from an allowlisted phrase -> NULL
        reasons.append("remaining_fraction: no allowlisted phrase -> NULL")
        return ValidatedField(name, None, Provenance.UNSUPPORTED.value, rejected=True,
                              reason="no deterministic conversion phrase present")

    if name in NUMERIC_FIELDS:
        norm = _normalize_num(str(raw_val)) if raw_val is not None else None
        if norm is not None and norm in available_numbers:
            return ValidatedField(name, raw_val, Provenance.LITERAL_TEXT.value)
        # numeric not literally present in verified text
        if name in IMAGE_PRONE_FIELDS and has_image_evidence:
            reasons.append(f"{name}: only image-derived & image MEDIA_MISSING -> NULL")
            return ValidatedField(name, None, Provenance.UNSUPPORTED.value, rejected=True,
                                  reason="image-only value, media missing")
        reasons.append(f"{name}: value {raw_val!r} not literally present -> rejected")
        return ValidatedField(name, None, Provenance.UNSUPPORTED.value, rejected=True,
                              reason="numeric not literally present in verified text")

    # non-numeric descriptive field: accept if its literal text appears, else reject
    if raw_val is not None and str(raw_val).lower() in verified_text_low:
        return ValidatedField(name, raw_val, Provenance.LITERAL_TEXT.value)
    # direction/asset may be stated; keep when present, else reject as unsupported
    return ValidatedField(name, raw_val, Provenance.LITERAL_TEXT.value) \
        if name in ("direction", "asset") and raw_val else \
        ValidatedField(name, None, Provenance.UNSUPPORTED.value, rejected=True,
                       reason="descriptive value not present in verified text")
