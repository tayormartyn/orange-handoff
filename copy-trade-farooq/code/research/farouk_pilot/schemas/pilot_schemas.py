"""
Versioned schemas for the Farouk evidence-pilot workspace. Pure stdlib, methodology-agnostic record
shapes. Every DERIVED record must link back to one or more source asset ids (`source_asset_ids`). This
module defines shapes + a strict validator + the rights-gate constants; it performs NO ingestion, NO
network access, and NO trading logic.

Separation of concerns: a statement made in a video is an EducationalClaim with support_status
SOURCE_CLAIM until trade evidence supports/contradicts it (see README workflow).
"""
from __future__ import annotations

PILOT_SCHEMA_VERSION = "1.0.0"

# rights gate — fail closed. An asset is processable ONLY when its rights record is APPROVED and the
# specific permission needed for the step is explicitly True. false/unknown/missing => refuse.
RIGHTS_STATUS_APPROVED = "APPROVED"
RIGHTS_STATUSES = ("APPROVED", "REJECTED", "PENDING", "UNKNOWN")
PERMISSION_FIELDS = (
    "permitted_internal_analysis", "permitted_transcription", "permitted_machine_processing",
    "permitted_sharing_external", "permitted_derivative_implementation",
)

# outcome / support / status vocabularies
CAMPAIGN_OUTCOMES = ("WIN", "LOSS", "STOPPED", "REJECTED", "CANCELLED", "OPEN", "UNKNOWN")
SUPPORT_STATUSES = ("SOURCE_CLAIM", "SUPPORTED", "CONTRADICTED", "UNRESOLVED")
ASSET_KINDS = ("message", "image", "video", "market_data", "indicator_observation", "document", "audio")


def _f(required=True, type=None, note=""):
    return {"required": required, "type": type, "note": note}


# each schema: field -> spec. Derived schemas carry source_asset_ids (non-empty) for lineage.
SCHEMAS = {
    "SourceAsset": {
        "schema_version": _f(type=str), "asset_id": _f(type=str, note="immutable, hash-derived"),
        "sha256": _f(type=str), "kind": _f(type=str, note="one of ASSET_KINDS"),
        "original_filename": _f(type=str), "mime_type": _f(type=str),
        "byte_size": _f(type=int), "ingested_at_utc": _f(type=str),
        "source_captured_at_utc": _f(required=False, type=str), "original_timestamps": _f(required=False, type=dict),
        "rights_record_id": _f(type=str, note="MUST link a RightsRecord"), "notes": _f(required=False, type=str),
    },
    "RightsRecord": {
        "schema_version": _f(type=str), "rights_record_id": _f(type=str),
        "applies_to_asset_ids": _f(required=False, type=list),
        "rights_status": _f(type=str, note="one of RIGHTS_STATUSES"),
        "source_owner": _f(type=str), "access_basis": _f(type=str),
        "permitted_internal_analysis": _f(type=bool), "permitted_transcription": _f(type=bool),
        "permitted_machine_processing": _f(type=bool), "permitted_sharing_external": _f(type=bool),
        "permitted_derivative_implementation": _f(type=bool), "retention_notes": _f(type=str),
    },
    "TradeCampaign": {
        "schema_version": _f(type=str), "campaign_id": _f(type=str), "symbol": _f(type=str),
        "direction": _f(type=str), "setup_family": _f(type=str),
        "outcome": _f(type=str, note="one of CAMPAIGN_OUTCOMES"),
        "market_event_start_utc": _f(required=False, type=str), "market_event_end_utc": _f(required=False, type=str),
        "source_posting_ts_utc": _f(required=False, type=str),
        "source_asset_ids": _f(type=list, note="lineage — non-empty"), "notes": _f(required=False, type=str),
    },
    "TradeEvent": {
        "schema_version": _f(type=str), "event_id": _f(type=str), "campaign_id": _f(type=str),
        "event_type": _f(type=str, note="SIGNAL/ENTRY/MANAGEMENT/EXIT/VETO/CANCEL"),
        "ts_utc": _f(required=False, type=str), "ts_uncertainty_seconds": _f(required=False, type=(int, float)),
        "price_decimal_string": _f(required=False, type=str),
        "exact_supporting_text": _f(required=False, type=str),
        "source_asset_ids": _f(type=list, note="lineage — non-empty"),
    },
    "TranscriptSegment": {
        "schema_version": _f(type=str), "segment_id": _f(type=str), "source_asset_id": _f(type=str),
        "start_ms": _f(type=int), "end_ms": _f(type=int), "text": _f(type=str),
        "speaker": _f(required=False, type=str), "confidence": _f(required=False, type=(int, float)),
        "source_asset_ids": _f(type=list, note="lineage — non-empty"),
    },
    "ChartObservation": {
        "schema_version": _f(type=str), "observation_id": _f(type=str), "symbol": _f(type=str),
        "feature": _f(type=str, note="session_high/session_low/level/zone"),
        "value_decimal_string": _f(required=False, type=str),
        "observed_at_utc": _f(required=False, type=str),
        "point_in_time_ts_utc": _f(type=str, note="the T this feature is valid as-of"),
        "method": _f(required=False, type=str), "source_asset_ids": _f(type=list, note="lineage — non-empty"),
    },
    "IndicatorObservation": {
        "schema_version": _f(type=str), "observation_id": _f(type=str), "indicator_name": _f(type=str),
        "state": _f(required=False, type=str), "value_decimal_string": _f(required=False, type=str),
        "observed_at_utc": _f(required=False, type=str), "point_in_time_ts_utc": _f(type=str),
        "source_asset_ids": _f(type=list, note="lineage — non-empty"),
    },
    "EducationalClaim": {
        "schema_version": _f(type=str), "claim_id": _f(type=str),
        "claim_type": _f(type=str, note="ORB/SESSION_LIQUIDITY/MOMENTUM_REVERSAL/OTHER"),
        "claim_text": _f(type=str), "ts_in_video_ms": _f(required=False, type=int),
        "support_status": _f(type=str, note="SOURCE_CLAIM until supported/contradicted"),
        "linked_campaign_ids": _f(required=False, type=list),
        "source_asset_ids": _f(type=list, note="lineage — non-empty"),
    },
    "AlignmentRecord": {
        "schema_version": _f(type=str), "alignment_id": _f(type=str),
        "subject_kind": _f(type=str, note="claim/campaign/event"), "subject_id": _f(type=str),
        "aligned_market_data_ref": _f(required=False, type=str),
        "alignment_method": _f(type=str), "timestamp_alignment_confidence": _f(required=False, type=(int, float)),
        "notes": _f(required=False, type=str), "source_asset_ids": _f(type=list, note="lineage — non-empty"),
    },
    "CandidateRule": {
        "schema_version": _f(type=str), "rule_id": _f(type=str), "rule_text": _f(type=str),
        "preconditions": _f(required=False, type=list), "actions": _f(required=False, type=list),
        "confidence": _f(required=False, type=(int, float)),
        "status": _f(type=str, note="CANDIDATE/ADJUDICATED"), "adjudicator": _f(required=False, type=str),
        "derived_from_campaign_ids": _f(required=False, type=list),
        "derived_from_claim_ids": _f(required=False, type=list),
        "source_asset_ids": _f(type=list, note="lineage — non-empty"),
    },
    "TradeDossier": {
        "schema_version": _f(type=str), "campaign_id": _f(type=str), "symbol": _f(type=str),
        "direction": _f(type=str), "setup_family": _f(type=str),
        "market_event_start_utc": _f(required=False, type=str), "market_event_end_utc": _f(required=False, type=str),
        "source_posting_ts_utc": _f(required=False, type=str),
        "timestamp_uncertainty_seconds": _f(required=False, type=(int, float)),
        "session_context": _f(required=False, type=str),
        "point_in_time_session_high": _f(required=False, type=str),
        "point_in_time_session_low": _f(required=False, type=str),
        "previous_completed_day_levels": _f(required=False, type=dict),
        "visible_indicator_states": _f(required=False, type=list),
        "explicit_farouk_statements": _f(required=False, type=list),
        "observed_actions": _f(required=False, type=list),
        "entry_zone": _f(required=False, type=dict), "structural_invalidation": _f(required=False, type=str),
        "targets": _f(required=False, type=list), "management_events": _f(required=False, type=list),
        "veto_cancellation_evidence": _f(required=False, type=list),
        "mfe_decimal_string": _f(required=False, type=str), "mae_decimal_string": _f(required=False, type=str),
        "explicit_facts": _f(required=False, type=list), "strong_inferences": _f(required=False, type=list),
        "weak_inferences": _f(required=False, type=list), "contradictions": _f(required=False, type=list),
        "unresolved_questions": _f(required=False, type=list),
        "candidate_rules": _f(required=False, type=list), "confidence_by_field": _f(required=False, type=dict),
        # video-evidence sections (additive, optional, backward-compatible)
        "video_metadata": _f(required=False, type=dict),
        "video_transcript_status": _f(required=False, type=str),
        "directly_visible_chart_observations": _f(required=False, type=list),
        "explicit_spoken_statements": _f(required=False, type=list),
        "candidate_hypotheses": _f(required=False, type=list),
        "video_alignment": _f(required=False, type=dict),
        # multi-leg + external-review sections (additive, optional, backward-compatible)
        "legs": _f(required=False, type=list),
        "net_campaign_outcome": _f(required=False, type=str),
        "external_review": _f(required=False, type=dict),
        "math_observations": _f(required=False, type=dict),
        "multi_entry_analysis": _f(required=False, type=dict),
        "explicit_discord_statements": _f(required=False, type=list),
        "prior_market_context": _f(required=False, type=dict),
        "confluence_analysis": _f(required=False, type=dict),
        "contingency_analysis": _f(required=False, type=dict),
        "setup_structures": _f(required=False, type=dict),
        "source_asset_ids": _f(type=list, note="lineage — non-empty"),
    },
}

DERIVED_TYPES = ("TradeCampaign", "TradeEvent", "TranscriptSegment", "ChartObservation",
                 "IndicatorObservation", "EducationalClaim", "AlignmentRecord", "CandidateRule",
                 "TradeDossier")


class SchemaError(ValueError):
    def __init__(self, code, field=None, detail=None):
        self.code, self.field, self.detail = code, field, detail
        super().__init__(f"{code}" + (f" [{field}]" if field else "") + (f": {detail}" if detail else ""))


def validate(record_type, record, *, allow_unknown=False):
    """Validate a record against its schema. Strict on unknown fields unless allow_unknown. Enforces
    required fields, declared types, and non-empty source_asset_ids for derived records. Pure."""
    if record_type not in SCHEMAS:
        raise SchemaError("UNKNOWN_RECORD_TYPE", detail=record_type)
    if not isinstance(record, dict):
        raise SchemaError("NOT_AN_OBJECT", detail=record_type)
    spec = SCHEMAS[record_type]
    if not allow_unknown:
        unknown = set(record) - set(spec)
        if unknown:
            raise SchemaError("UNKNOWN_FIELD", ",".join(sorted(unknown)))
    for field, s in spec.items():
        if field not in record or record[field] is None:
            if s["required"]:
                raise SchemaError("MISSING_FIELD", field)
            continue
        if s["type"] is not None and not isinstance(record[field], s["type"]):
            raise SchemaError("WRONG_TYPE", field, type(record[field]).__name__)
    if record.get("schema_version") and record["schema_version"] != PILOT_SCHEMA_VERSION:
        raise SchemaError("UNSUPPORTED_SCHEMA_VERSION", "schema_version", record["schema_version"])
    if record_type in DERIVED_TYPES:
        ids = record.get("source_asset_ids")
        if not isinstance(ids, list) or not ids:
            raise SchemaError("MISSING_LINEAGE", "source_asset_ids", "derived record must cite >=1 source asset")
    if record_type == "RightsRecord" and record.get("rights_status") not in RIGHTS_STATUSES:
        raise SchemaError("INVALID_RIGHTS_STATUS", "rights_status", record.get("rights_status"))
    return record
