"""
Campaign extractor — core schema, provenance, and the deterministic conversion allowlist.

Pure data + pure functions. No AI, no I/O. Everything here is what the LLM may PROPOSE
and what the deterministic validator reasons over. The LLM never constructs accepted
state; it only emits CandidateEvent objects that the validator then judges.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------- enums / tags
class Provenance(str, Enum):
    LITERAL_TEXT = "LITERAL_TEXT"
    LITERAL_IMAGE = "LITERAL_IMAGE"
    DETERMINISTIC_CONVERSION = "DETERMINISTIC_CONVERSION"
    UNSUPPORTED = "UNSUPPORTED"          # can NEVER affect campaign state or R


class EventType(str, Enum):
    ENTRY = "ENTRY"                      # opens a leg
    RE_ENTER = "RE_ENTER"                # opens a child leg
    ADD = "ADD"                          # adds to an existing leg
    STOP_HIT = "STOP_HIT"                # leg stopped out (TERMINAL)
    TP_HIT = "TP_HIT"                    # full take-profit / final TP close (TERMINAL)
    PARTIAL_TP = "PARTIAL_TP"            # partial take-profit (e.g. "tp 1") — NON-terminal,
                                         # leg stays open after banking part of the move
    PARTIAL_CLOSE = "PARTIAL_CLOSE"      # closes part of a leg (NON-terminal)
    CLOSE = "CLOSE"                      # closes a leg (TERMINAL)
    MOVE_STOP = "MOVE_STOP"
    COMMENTARY = "COMMENTARY"            # never mutates state (analysis / context)
    CONDITIONAL = "CONDITIONAL"          # "if X I'll..." — creates NO leg


class Status(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class SizeQuality(str, Enum):
    NUMERIC = "NUMERIC"
    QUALITATIVE_ONLY = "QUALITATIVE_ONLY"   # "small size", "low lot" -> numeric stays NULL


# The ONLY sender whose posts may produce campaign-state-mutating events.
FAROUK_HANDLE = "seascalperfarouk"


# ----------------------------------------------- deterministic conversion allowlist
# Each entry: a literal phrase (lowercased, regex-free substring) -> (field, value).
# Provenance for any value produced here is DETERMINISTIC_CONVERSION. Nothing outside
# this table may turn words into numbers; everything else must be literally present.
SIZE_CONVERSIONS = {
    "half size": 0.50,
    "quarter size": 0.25,
}
# "remaining fraction" conversions: phrase -> fraction of position still open afterwards.
REMAINING_CONVERSIONS = {
    "leave 10%": 0.10,
    "take 90% off": 0.10,
    "leave 25%": 0.25,
    "take 75% off": 0.25,
    "leave 50%": 0.50,
    "take 50% off": 0.50,
}
# Qualitative size wording: recognised, but numeric MUST remain NULL.
QUALITATIVE_SIZE_PHRASES = ("small size", "low lot", "small lot", "low size", "tiny size")


# ---------------------------------------------------------------- dataclasses
@dataclass(frozen=True)
class EvidenceQuote:
    """An exact quotation the candidate claims is present in a specific message."""
    message_key: str
    quote: str
    is_image_field: bool = False          # True => evidence is an image-derived field ref
    image_ref: Optional[str] = None       # image hash / bbox ref when is_image_field


@dataclass
class CandidateEvent:
    """What the LLM PROPOSES. Never written to accepted state directly."""
    event_type: str                        # EventType value
    proposed_fields: dict                  # field_name -> raw proposed value (may be wrong)
    source_message_keys: list              # every contributing message key
    evidence: list                         # list[EvidenceQuote]
    sender_handle: Optional[str]           # derived sender (evidence); None if unknown
    confidence: float
    versions: dict                         # extractor/model/prompt/validator versions
    # ---- routing metadata (NOT facts extracted from text): which outcome track this
    # belongs to, and which leg it targets / parents. Carried through validation as-is.
    track: str = "SHADOW"                  # PROVIDER | SHADOW | DEMO — kept separate
    leg_ref: Optional[str] = None          # target leg id (mutating events) or new leg id
    parent_ref: Optional[str] = None       # parent leg id for RE_ENTER child legs

    def canonical_hash(self) -> str:
        return _canonical_hash({
            "event_type": self.event_type,
            "proposed_fields": self.proposed_fields,
            "source_message_keys": sorted(self.source_message_keys),
            "evidence": sorted(
                [(e.message_key, e.quote, e.is_image_field, e.image_ref) for e in self.evidence]
            ),
            "sender_handle": self.sender_handle,
            "versions": self.versions,
            "track": self.track,
            "leg_ref": self.leg_ref,
            "parent_ref": self.parent_ref,
        })


@dataclass
class ValidatedField:
    name: str
    value: object                          # validated value, or None if unsupported
    provenance: str                        # Provenance value
    rejected: bool = False
    reason: Optional[str] = None


@dataclass
class ValidatedEvent:
    """Output of the deterministic validator. This is what may enter the event store."""
    event_type: str
    status: str                            # Status value
    fields: dict                           # name -> ValidatedField
    source_message_keys: list
    sender_handle: Optional[str]
    versions: dict
    reasons: list                          # human-readable validator notes
    candidate_hash: str
    track: str = "SHADOW"
    leg_ref: Optional[str] = None
    parent_ref: Optional[str] = None

    def accepted_hash(self) -> str:
        """Idempotent: identical evidence + versions => identical accepted-event hash."""
        return _canonical_hash({
            "event_type": self.event_type,
            "status": self.status,
            "fields": {
                n: {"value": f.value, "provenance": f.provenance, "rejected": f.rejected}
                for n, f in sorted(self.fields.items())
            },
            "source_message_keys": sorted(self.source_message_keys),
            "sender_handle": self.sender_handle,
            "versions": self.versions,
            "track": self.track,
            "leg_ref": self.leg_ref,
            "parent_ref": self.parent_ref,
        })


def _canonical_hash(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, ensure_ascii=False, sort_keys=True, default=_default).encode("utf-8")
    ).hexdigest()


def _default(o):
    if isinstance(o, Enum):
        return o.value
    if hasattr(o, "__dict__"):
        return asdict(o) if hasattr(o, "__dataclass_fields__") else o.__dict__
    return str(o)
