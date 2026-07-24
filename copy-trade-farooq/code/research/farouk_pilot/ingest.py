"""
Deterministic local ingestion tool for the Farouk evidence pilot. It hashes a MANUALLY supplied file,
mints an immutable asset id, captures metadata, and appends to the asset manifest — refusing if the
linked rights record is not APPROVED for machine processing, and refusing to overwrite an existing
asset. It NEVER uploads anything and NEVER touches Discord/TradingView. Dry-run supported.

    python ingest.py --file <path> --kind <kind> --rights-record-id <id> [--dry-run]
                     [--source-captured-at <iso>] [--notes <text>]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import mimetypes
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from rights_gate import rights_permit, normalize_rights_row
from schemas.pilot_schemas import ASSET_KINDS

RIGHTS_CSV = os.path.join(_HERE, "rights_register.csv")
MANIFEST_CSV = os.path.join(_HERE, "asset_manifest.csv")
MANIFEST_FIELDS = ["asset_id", "sha256", "kind", "original_filename", "mime_type", "byte_size",
                   "ingested_at_utc", "source_captured_at_utc", "rights_record_id", "notes"]
# ingestion requires machine-processing permission specifically
INGEST_PERMISSION = "permitted_machine_processing"


class IngestError(Exception):
    def __init__(self, code, detail=None):
        self.code, self.detail = code, detail
        super().__init__(f"{code}" + (f": {detail}" if detail else ""))


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def asset_id_for(sha):
    return "sa-" + sha[:16]                              # immutable, hash-derived


def load_rights(rights_csv=RIGHTS_CSV):
    out = {}
    if os.path.exists(rights_csv):
        with open(rights_csv, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("rights_record_id"):
                    out[row["rights_record_id"]] = normalize_rights_row(row)
    return out


def load_manifest(manifest_csv=MANIFEST_CSV):
    rows = []
    if os.path.exists(manifest_csv):
        with open(manifest_csv, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    return rows


def ingest(*, file_path, kind, rights_record_id, rights_csv=RIGHTS_CSV, manifest_csv=MANIFEST_CSV,
           dry_run=False, source_captured_at=None, notes="", now_iso=None):
    """Ingest one file. Returns a result dict. Raises IngestError on refusal. Never uploads."""
    if kind not in ASSET_KINDS:
        raise IngestError("INVALID_KIND", f"{kind} not in {ASSET_KINDS}")
    if not os.path.isfile(file_path):
        raise IngestError("FILE_NOT_FOUND", file_path)
    if not rights_record_id:
        raise IngestError("RIGHTS_RECORD_REQUIRED")

    rights = load_rights(rights_csv).get(rights_record_id)
    permitted, reason = rights_permit(rights, INGEST_PERMISSION)
    if not permitted:
        raise IngestError("RIGHTS_REFUSED", reason)      # fail closed on false/unknown/missing/unapproved

    sha = sha256_file(file_path)
    asset_id = asset_id_for(sha)
    manifest = load_manifest(manifest_csv)

    # duplicate detection by hash (and by asset_id) — never overwrite an existing asset
    for row in manifest:
        if row.get("sha256") == sha:
            return {"status": "DUPLICATE", "asset_id": row.get("asset_id"), "sha256": sha,
                    "existing": True, "written": False, "uploaded": False}

    now = now_iso or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    mime = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    record = {
        "asset_id": asset_id, "sha256": sha, "kind": kind,
        "original_filename": os.path.basename(file_path), "mime_type": mime,
        "byte_size": str(os.path.getsize(file_path)), "ingested_at_utc": now,
        "source_captured_at_utc": source_captured_at or "", "rights_record_id": rights_record_id,
        "notes": notes or "",
    }
    if dry_run:
        return {"status": "DRY_RUN", "asset_id": asset_id, "sha256": sha, "record": record,
                "written": False, "uploaded": False}

    # append-only; create header if new
    new_file = not os.path.exists(manifest_csv)
    with open(manifest_csv, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        if new_file:
            w.writeheader()
        w.writerow(record)
    return {"status": "INGESTED", "asset_id": asset_id, "sha256": sha, "record": record,
            "written": True, "uploaded": False}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Farouk pilot — deterministic local asset ingestion (no upload).")
    ap.add_argument("--file", required=True)
    ap.add_argument("--kind", required=True, choices=list(ASSET_KINDS))
    ap.add_argument("--rights-record-id", required=True)
    ap.add_argument("--source-captured-at", default=None)
    ap.add_argument("--notes", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    try:
        res = ingest(file_path=args.file, kind=args.kind, rights_record_id=args.rights_record_id,
                     dry_run=args.dry_run, source_captured_at=args.source_captured_at, notes=args.notes)
    except IngestError as e:
        print(f"REFUSED: {e}")
        return 2
    print(f"{res['status']}: asset_id={res['asset_id']} sha256={res['sha256'][:16]}… uploaded={res['uploaded']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
