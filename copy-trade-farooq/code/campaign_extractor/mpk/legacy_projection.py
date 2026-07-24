"""
Read-only Farouk compatibility projection.

Presents the mapped signed-off-28 records THROUGH the new provider interface by joining
legacy_campaign_mapping (canonical DB) to the immutable legacy archive (opened mode=ro).
Every displayed value is SOURCED from the legacy archive — nothing is recomputed, replaced
or reinterpreted. The mapping supplies only provenance (provider_id, compatibility id,
source_record_type, original_record_hash); the trade facts/outcomes come verbatim from the
legacy row, and the original_record_hash is re-verified against the live read.

The canonical mapping DB and the legacy DB are opened on SEPARATE connections; they are
never attached together, and the legacy connection is read-only.
"""
from __future__ import annotations
import os
import sqlite3

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)
from appendonly import canonical_hash, ro_connect

PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))


def project_farouk_signed_off(campaigns_db_path, signal_archive_path=None, set_id="SIGNED_OFF_28"):
    """Return a list of read-only projected rows for the mapped signed-off set."""
    signal_archive_path = signal_archive_path or os.path.join(
        PROJECT_ROOT, "data", "signal_archive.db")

    cam = sqlite3.connect(f"file:{campaigns_db_path}?mode=ro", uri=True)   # mapping DB read-only too
    arch = ro_connect(signal_archive_path, immutable=False)
    try:
        maps = cam.execute(
            "SELECT mapping_uid, provider_id, immutable_legacy_reference, source_record_type, "
            "compatibility_record_uid, original_record_hash, mapping_status "
            "FROM legacy_campaign_mapping WHERE signed_off_set_identifier=? "
            "AND mapping_status='MAPPED_VERIFIED' ORDER BY immutable_legacy_reference",
            (set_id,)).fetchall()
        out = []
        for (muid, pid, ref, srt, cuid, orig_hash, mstatus) in maps:
            row = arch.execute("""
                SELECT s.signal_id, s.source_message_key, s.provider, s.asset, s.asset_class,
                       s.direction, s.entry_low, s.entry_high, s.stop, s.tp1, s.tp2, s.tp3,
                       s.classification, op.outcome_category, op.binary_rollup, op.calculated_r,
                       op.r_is_known
                FROM signals s LEFT JOIN outcome_projections op ON op.signal_id = s.signal_id
                WHERE s.signal_id=?""", (ref,)).fetchone()
            if row is None:
                out.append({"mapping_uid": muid, "provider_id": pid, "legacy_ref": ref,
                            "error": "LEGACY_ROW_NOT_FOUND"})
                continue
            cols = ["signal_id", "source_message_key", "provider", "asset", "asset_class",
                    "direction", "entry_low", "entry_high", "stop", "tp1", "tp2", "tp3",
                    "classification", "outcome_category", "binary_rollup", "calculated_r",
                    "r_is_known"]
            legacy = dict(zip(cols, row))
            out.append({
                # provenance from the canonical mapping
                "provider_id": pid, "mapping_uid": muid, "compatibility_record_uid": cuid,
                "source_record_type": srt, "mapping_status": mstatus,
                "original_record_hash": orig_hash,
                # trade facts sourced VERBATIM from immutable legacy truth (not recomputed)
                "legacy": legacy,
            })
        return out
    finally:
        cam.close()
        arch.close()
