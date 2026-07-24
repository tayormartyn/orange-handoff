"""Ingestion tool: deterministic hashing, duplicate detection, append behaviour, fail-closed rights
refusal, dry-run, no-upload. Uses temp registers — never touches the real workspace files."""
from __future__ import annotations
import csv
import hashlib
import os
import sys
import tempfile

_PILOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PILOT)
import ingest as ING
from schemas.pilot_schemas import PERMISSION_FIELDS

_FIX = os.path.join(_PILOT, "tests", "fixtures", "sample_message.txt")
_FIX2 = os.path.join(_PILOT, "tests", "fixtures", "sample_message_2.txt")


def _rights_csv(tmp, *, rid="RR-001", status="APPROVED", machine=True):
    path = os.path.join(tmp, "rights.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rights_record_id", "applies_to_asset_ids", "rights_status", "source_owner",
                    "access_basis", *PERMISSION_FIELDS, "retention_notes"])
        perms = ["true" if machine else "false"] * len(PERMISSION_FIELDS)
        w.writerow([rid, "", status, "Farouk", "manual copy Martyn holds", *perms, "pilot"])
    return path


def _env():
    tmp = tempfile.mkdtemp()
    return tmp, _rights_csv(tmp), os.path.join(tmp, "manifest.csv")


def test_deterministic_hashing():
    expected = hashlib.sha256(open(_FIX, "rb").read()).hexdigest()
    assert ING.sha256_file(_FIX) == expected
    assert ING.asset_id_for(expected) == "sa-" + expected[:16]


def test_ingest_and_manifest_append():
    tmp, rights, manifest = _env()
    r1 = ING.ingest(file_path=_FIX, kind="message", rights_record_id="RR-001", rights_csv=rights,
                    manifest_csv=manifest, now_iso="2026-07-04T10:00:00Z")
    assert r1["status"] == "INGESTED" and r1["written"] and r1["uploaded"] is False
    r2 = ING.ingest(file_path=_FIX2, kind="message", rights_record_id="RR-001", rights_csv=rights,
                    manifest_csv=manifest, now_iso="2026-07-04T10:01:00Z")
    assert r2["status"] == "INGESTED" and r2["asset_id"] != r1["asset_id"]
    rows = ING.load_manifest(manifest)
    assert len(rows) == 2                                # append-only, both present


def test_duplicate_detection_no_overwrite():
    tmp, rights, manifest = _env()
    ING.ingest(file_path=_FIX, kind="message", rights_record_id="RR-001", rights_csv=rights,
               manifest_csv=manifest, now_iso="2026-07-04T10:00:00Z")
    dup = ING.ingest(file_path=_FIX, kind="message", rights_record_id="RR-001", rights_csv=rights,
                     manifest_csv=manifest, now_iso="2026-07-04T10:05:00Z")
    assert dup["status"] == "DUPLICATE" and dup["written"] is False
    assert len(ING.load_manifest(manifest)) == 1        # not overwritten / not duplicated


def test_refuse_when_rights_unapproved():
    tmp = tempfile.mkdtemp()
    rights = _rights_csv(tmp, status="PENDING")
    manifest = os.path.join(tmp, "m.csv")
    try:
        ING.ingest(file_path=_FIX, kind="message", rights_record_id="RR-001", rights_csv=rights, manifest_csv=manifest)
        assert False
    except ING.IngestError as e:
        assert e.code == "RIGHTS_REFUSED" and "NOT_APPROVED" in str(e.detail)
    assert not os.path.exists(manifest)                 # nothing written on refusal


def test_refuse_when_machine_processing_false():
    tmp = tempfile.mkdtemp()
    rights = _rights_csv(tmp, machine=False)
    try:
        ING.ingest(file_path=_FIX, kind="message", rights_record_id="RR-001", rights_csv=rights,
                   manifest_csv=os.path.join(tmp, "m.csv"))
        assert False
    except ING.IngestError as e:
        assert e.code == "RIGHTS_REFUSED" and "PERMISSION_FALSE_OR_UNKNOWN" in str(e.detail)


def test_refuse_when_rights_record_missing():
    tmp, rights, manifest = _env()
    try:
        ING.ingest(file_path=_FIX, kind="message", rights_record_id="RR-DOES-NOT-EXIST",
                   rights_csv=rights, manifest_csv=manifest)
        assert False
    except ING.IngestError as e:
        assert e.code == "RIGHTS_REFUSED" and "RIGHTS_RECORD_MISSING" in str(e.detail)


def test_dry_run_writes_nothing():
    tmp, rights, manifest = _env()
    r = ING.ingest(file_path=_FIX, kind="message", rights_record_id="RR-001", rights_csv=rights,
                   manifest_csv=manifest, dry_run=True)
    assert r["status"] == "DRY_RUN" and r["written"] is False and r["uploaded"] is False
    assert not os.path.exists(manifest)


def test_result_never_uploads():
    tmp, rights, manifest = _env()
    r = ING.ingest(file_path=_FIX, kind="message", rights_record_id="RR-001", rights_csv=rights,
                   manifest_csv=manifest, now_iso="2026-07-04T10:00:00Z")
    assert r["uploaded"] is False
