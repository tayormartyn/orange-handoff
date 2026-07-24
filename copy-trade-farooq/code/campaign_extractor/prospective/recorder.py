"""
Brick 5 — prospective recorder pipeline.

Raw Telegram evidence -> candidate extraction -> deterministic validation -> deterministic
leg association -> append-only record. Observe-don't-infer: NO fill, entry, exit, R,
or win/loss is ever produced. The raw message evidence is stored FIRST and ALWAYS — a
parser/validator failure can never destroy it. Broker quote context is always NULL with
BROKER_NOT_CONNECTED in this phase (no broker connected, so no quotes exist).

This module does NOT connect to Telegram and does NOT activate any live handler. It records
provided/offline messages only. Live activation is a separate, separately-approved step.
"""
from __future__ import annotations
import hashlib
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

from schema import CandidateEvent, EvidenceQuote, Status, EventType
from validator import validate, ArchiveReader, VALIDATOR_VERSION
from leg_resolver import resolve as resolve_legs, LEG_TARGETING
from extractor import EXTRACTOR_VERSION

CONTEXT_BROKER_NOT_CONNECTED = "BROKER_NOT_CONNECTED"


def _sha(s):
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def _to_candidate(proposal: dict, message_key: str, sender_handle: str):
    quotes = []
    if proposal.get("evidence_quote"):
        quotes.append(proposal["evidence_quote"])
    return CandidateEvent(
        event_type=proposal.get("event_type", ""),
        proposed_fields=proposal.get("proposed_fields", {}) or {},
        source_message_keys=[message_key],
        evidence=[EvidenceQuote(message_key, q) for q in quotes],
        sender_handle=sender_handle,
        confidence=float(proposal.get("confidence", 0.5)),
        versions={"extractor": EXTRACTOR_VERSION, "validator": VALIDATOR_VERSION},
        track=proposal.get("track", "PROVIDER"),
        leg_ref=proposal.get("leg_ref"), parent_ref=proposal.get("parent_ref"),
    )


class ProspectiveRecorder:
    def __init__(self, db):
        self.db = db

    # ---- raw evidence is stored FIRST and ALWAYS (perishable; parser failure never loses it)
    # NOTE: raw message content is written to the evidence DB ONLY — never to application logs
    # or exception output. Telegram DELETION capture is NOT implemented by the listener (see
    # module docstring); the schema supports append-only revisions so deletions/edits can later
    # be appended as lifecycle events WITHOUT overwriting the preserved original.
    def record_message(self, msg: dict):
        posted, received = msg.get("posted_at_utc"), msg.get("received_at_utc")
        started, completed = msg.get("parser_started_at_utc"), msg.get("parser_completed_at_utc")
        return self.db.append_message_evidence(
            telegram_channel_id=msg.get("channel_id"),
            telegram_message_id=str(msg.get("message_id")),
            telegram_posted_at_utc=posted, listener_received_at_utc=received,
            raw_text=msg.get("raw_text"),             # exact content; None for media-only (NULL)
            media_reference_or_hash=msg.get("media_reference"),
            parser_started_at_utc=started, parser_completed_at_utc=completed,
            listener_latency_ms=msg.get("listener_latency_ms"),
            parser_latency_ms=msg.get("parser_latency_ms"),
            extractor_version=EXTRACTOR_VERSION,
            message_event_type=msg.get("message_event_type", "CREATED"),
            message_revision_number=msg.get("message_revision_number", 1),
            supersedes_evidence_id=msg.get("supersedes_evidence_id"),
            telegram_edited_at_utc=msg.get("telegram_edited_at_utc"),
            listener_observed_at_utc=msg.get("listener_observed_at_utc"),
            telegram_sender_id=msg.get("sender_id"),
            telegram_sender_username=msg.get("sender_username"),
            telegram_sender_display=msg.get("sender_display"),
            telegram_is_forwarded=msg.get("is_forwarded"),
            telegram_fwd_origin=msg.get("fwd_origin"))

    def record_quote_context(self, message_id, *, broker_symbol_id=None,
                             quote_before_message_id=None, first_quote_after_message_id=None):
        # broker not connected -> NULL prices, BROKER_NOT_CONNECTED. Never fabricated.
        return self.db.append_quote_context(
            telegram_message_id=str(message_id), context_status=CONTEXT_BROKER_NOT_CONNECTED,
            broker_symbol_id=broker_symbol_id, quote_before_message_id=quote_before_message_id,
            first_quote_after_message_id=first_quote_after_message_id,
            quote_status=CONTEXT_BROKER_NOT_CONNECTED)

    # ---- full batch pipeline (a campaign window or single message)
    def run_batch(self, messages: list, archive: ArchiveReader):
        # 1. store raw evidence for EVERY message first, unconditionally
        for msg in messages:
            self.record_message(msg)

        # 2. build + validate candidates (failures recorded, never destroy evidence)
        validated_by_msg = {}
        ordered = []
        for msg in messages:
            mk = msg["message_key"]
            vs = []
            for proposal in msg.get("candidates", []):
                try:
                    cand = _to_candidate(proposal, mk, msg.get("sender_handle", "seascalperfarouk"))
                    v = validate(cand, archive)
                except Exception:
                    # parser/extraction failure for this candidate -> record a rejected marker,
                    # but the raw evidence row (step 1) is already safely stored.
                    self.db.append_candidate_event(
                        telegram_message_id=str(msg["message_id"]),
                        proposed_event_type=proposal.get("event_type", "UNPARSEABLE"),
                        association_status="UNKNOWN", validator_status=Status.REJECTED.value,
                        rejection_reason="parse_failure", extractor_version=EXTRACTOR_VERSION,
                        validator_version=VALIDATOR_VERSION)
                    continue
                vs.append(v)
                ordered.append(v)
            validated_by_msg[mk] = vs

        # 3. deterministic leg association over the ordered batch (NEEDS_REVIEW where ambiguous)
        resolve_legs(ordered, archive)

        # 4. record candidate events + quote context (NULL/BROKER_NOT_CONNECTED) per message
        mk_to_msg = {m["message_key"]: m for m in messages}
        for mk, vs in validated_by_msg.items():
            msg = mk_to_msg[mk]
            for v in vs:
                assoc = ("RESOLVED" if v.leg_ref and v.status == Status.ACCEPTED.value
                         and v.event_type in LEG_TARGETING else
                         ("NEEDS_REVIEW" if v.status == Status.NEEDS_REVIEW.value else "N/A"))
                support = msg.get("candidates", [])
                # exact supporting text = the literal quote the candidate cited
                ev_text = None
                for p in support:
                    if p.get("event_type") == v.event_type:
                        ev_text = p.get("evidence_quote")
                        break
                self.db.append_candidate_event(
                    telegram_message_id=str(msg["message_id"]),
                    proposed_event_type=v.event_type,
                    asset=(v.fields["asset"].value if "asset" in v.fields and not v.fields["asset"].rejected else None),
                    direction=(v.fields["direction"].value if "direction" in v.fields and not v.fields["direction"].rejected else None),
                    proposed_campaign_id=msg.get("campaign_id"),
                    proposed_leg_id=v.leg_ref,
                    association_status=assoc,
                    exact_supporting_text=ev_text,
                    supporting_media_fact_id=msg.get("media_fact_id"),
                    extraction_confidence=None,
                    validator_status=v.status,
                    rejection_reason=(v.reasons[0] if v.status != Status.ACCEPTED.value and v.reasons else None),
                    extractor_version=EXTRACTOR_VERSION, validator_version=VALIDATOR_VERSION)
            self.record_quote_context(msg["message_id"])

    # ---- NEEDS_REVIEW-rate metrics (diagnostic only; never relaxes validation)
    def metrics(self, window=None):
        rows = self.db.con.execute(
            "SELECT proposed_event_type, validator_status, association_status, rejection_reason, "
            "supporting_media_fact_id FROM prospective_candidate_events ORDER BY rowseq").fetchall()
        if window:
            rows = rows[-window:]
        total = len(rows)
        accepted = sum(1 for r in rows if r[1] == Status.ACCEPTED.value)
        rejected = sum(1 for r in rows if r[1] == Status.REJECTED.value)
        needs_review = sum(1 for r in rows if r[1] == Status.NEEDS_REVIEW.value)
        unknown = sum(1 for r in rows if r[2] == "UNKNOWN")
        by_type = {}
        for r in rows:
            d = by_type.setdefault(r[0], {"total": 0, "needs_review": 0})
            d["total"] += 1
            if r[1] == Status.NEEDS_REVIEW.value:
                d["needs_review"] += 1
        media = sum(1 for r in rows if r[4])
        text_only = total - media
        reasons = {}
        for r in rows:
            if r[3]:
                reasons[r[3]] = reasons.get(r[3], 0) + 1
        return {
            "total": total, "accepted": accepted, "rejected": rejected,
            "needs_review": needs_review, "unknown": unknown,
            "needs_review_rate": (needs_review / total) if total else 0.0,
            "by_event_type": by_type,
            "text_only": text_only, "media_supported": media,
            "top_ambiguity_reasons": sorted(reasons.items(), key=lambda kv: -kv[1]),
            "note": "diagnostic only — does NOT relax validation",
        }
