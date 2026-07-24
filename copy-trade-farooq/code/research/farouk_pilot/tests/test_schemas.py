"""Schema validation: required fields, unknown-field rejection, derived-record lineage, rights status,
and the rights gate (fail closed)."""
from __future__ import annotations
import os
import sys

_PILOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PILOT)
from schemas import pilot_schemas as PS
import rights_gate as RG

V = PS.PILOT_SCHEMA_VERSION


def _source_asset(**o):
    r = {"schema_version": V, "asset_id": "sa-abc", "sha256": "a" * 64, "kind": "message",
         "original_filename": "m.txt", "mime_type": "text/plain", "byte_size": 10,
         "ingested_at_utc": "2026-07-04T10:00:00Z", "rights_record_id": "RR-001"}
    r.update(o); return r


def _rights(**o):
    r = {"schema_version": V, "rights_record_id": "RR-001", "rights_status": "APPROVED",
         "source_owner": "Farouk", "access_basis": "manual", "permitted_internal_analysis": True,
         "permitted_transcription": True, "permitted_machine_processing": True,
         "permitted_sharing_external": False, "permitted_derivative_implementation": True,
         "retention_notes": "pilot"}
    r.update(o); return r


def test_valid_source_asset():
    assert PS.validate("SourceAsset", _source_asset()) is not None


def test_missing_required_field_rejected():
    a = _source_asset(); del a["sha256"]
    try:
        PS.validate("SourceAsset", a); assert False
    except PS.SchemaError as e:
        assert e.code == "MISSING_FIELD" and e.field == "sha256"


def test_unknown_field_rejected():
    try:
        PS.validate("SourceAsset", _source_asset(surprise=1)); assert False
    except PS.SchemaError as e:
        assert e.code == "UNKNOWN_FIELD"


def test_wrong_type_rejected():
    try:
        PS.validate("SourceAsset", _source_asset(byte_size="ten")); assert False
    except PS.SchemaError as e:
        assert e.code == "WRONG_TYPE" and e.field == "byte_size"


def test_derived_record_requires_lineage():
    campaign = {"schema_version": V, "campaign_id": "C1", "symbol": "XAUUSD", "direction": "LONG",
                "setup_family": "ORB", "outcome": "WIN", "source_asset_ids": []}
    try:
        PS.validate("TradeCampaign", campaign); assert False
    except PS.SchemaError as e:
        assert e.code == "MISSING_LINEAGE"
    campaign["source_asset_ids"] = ["sa-abc"]
    assert PS.validate("TradeCampaign", campaign) is not None


def test_educational_claim_lineage_and_support_status():
    claim = {"schema_version": V, "claim_id": "CL1", "claim_type": "ORB",
             "claim_text": "buy the ORB break", "support_status": "SOURCE_CLAIM",
             "source_asset_ids": ["sa-vid"]}
    assert PS.validate("EducationalClaim", claim)["support_status"] == "SOURCE_CLAIM"


def test_rights_status_validated():
    try:
        PS.validate("RightsRecord", _rights(rights_status="MAYBE")); assert False
    except PS.SchemaError as e:
        assert e.code == "INVALID_RIGHTS_STATUS"


def test_unsupported_schema_version_rejected():
    try:
        PS.validate("SourceAsset", _source_asset(schema_version="9.9.9")); assert False
    except PS.SchemaError as e:
        assert e.code == "UNSUPPORTED_SCHEMA_VERSION"


# --- rights gate fail-closed ---
def test_rights_gate_permits_approved():
    ok, reason = RG.rights_permit(_rights(), "permitted_machine_processing")
    assert ok and reason is None


def test_rights_gate_fails_closed():
    assert RG.rights_permit(None, "permitted_machine_processing")[0] is False
    assert RG.rights_permit(_rights(rights_status="PENDING"), "permitted_machine_processing")[0] is False
    assert RG.rights_permit(_rights(permitted_sharing_external=False), "permitted_sharing_external")[0] is False
    assert RG.rights_permit(_rights(), "not_a_permission")[0] is False
