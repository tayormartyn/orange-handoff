"""
MPK-1 Step 2 — Farouk registration + non-destructive signed-off-28 mapping.

Registers Farouk as provider_farouk_001 (idempotent) and maps EXACTLY the locked
signed-off 28 legacy SIGNAL records into legacy_campaign_mapping as compatibility records.
NO canonical campaigns are created; NO legs/events/chronology are invented; the legacy
archive is read STRICTLY read-only (mode=ro). Idempotent and transactional: the complete
verified mapping set commits or none does.

This module is NOT imported by any live path. It loads no credentials and opens no socket.
"""
from __future__ import annotations
import hashlib
import os

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)
from appendonly import canonical_hash, ro_connect
from registry_db import RegistryDB
from campaigns_db import CampaignsDB, SCHEMA_VERSION as CAMPAIGNS_SCHEMA_VERSION

# ---- stable, deterministic constants ----
PROVIDER_ID = "provider_farouk_001"               # stable external identity (NOT a rowid)
FAROUK_DISPLAY = "Farouk"                          # mutable display metadata (not identity)
FAROUK_PLATFORM = "TELEGRAM"
FAROUK_ALIAS = "seascalperfarouk"                  # verified sender identity (evidence-backed)
SET_ID = "SIGNED_OFF_28"
SOURCE_RECORD_TYPE = "LEGACY_SIGNED_OFF_SIGNAL"
LEGACY_DB_REL = "data/signal_archive.db"
LEGACY_TABLE = "signals"
STEP2_AUTHORED_AT = "2026-06-30"                   # fixed -> deterministic, idempotent hashes
PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))

# the 28 locked baseline source_message_keys (N values), as immutable selection criteria
BASELINE_N = (16, 29, 47, 57, 65, 73, 92, 95, 99, 103, 127, 137, 143, 155, 182, 208, 212,
              224, 237, 242, 256, 270, 278, 290, 313, 327, 344, 376)
BASELINE_KEYS = tuple(f"telegram:baseline:{n}" for n in BASELINE_N)


class Step2Block(Exception):
    """Raised to abort Step 2 without committing any Farouk mapping rows."""


def _det_id(prefix, *parts):
    return prefix + hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:16]


def load_signed_off_28(signal_archive_path):
    """Read the 28 locked baseline SIGNAL records (mode=ro). Returns (records, diagnostics)."""
    con = ro_connect(signal_archive_path, immutable=False)   # possibly-live WAL DB -> no immutable
    try:
        cur = con.cursor()
        qmarks = ",".join("?" * len(BASELINE_KEYS))
        rows = cur.execute(f"""
            SELECT s.signal_id, s.source_message_key, s.source_signal_index, s.provider,
                   s.asset, s.asset_class, s.direction, s.entry_low, s.entry_high, s.stop,
                   s.tp1, s.tp2, s.tp3, s.classification,
                   op.outcome_category, op.binary_rollup, op.calculated_r, op.r_is_known
            FROM signals s LEFT JOIN outcome_projections op ON op.signal_id = s.signal_id
            WHERE s.source_message_key IN ({qmarks})
            ORDER BY s.signal_id
        """, BASELINE_KEYS).fetchall()
        cols = ["signal_id", "source_message_key", "source_signal_index", "provider", "asset",
                "asset_class", "direction", "entry_low", "entry_high", "stop", "tp1", "tp2",
                "tp3", "classification", "outcome_category", "binary_rollup", "calculated_r",
                "r_is_known"]
        records = [dict(zip(cols, r)) for r in rows]
        return records, {"rows_found": len(records)}
    finally:
        con.close()


def _eligible(rec):
    """A record is eligible iff it is in the locked signed-off set AND attributed to Farouk."""
    return (rec.get("source_message_key") in BASELINE_KEYS
            and rec.get("provider") == FAROUK_ALIAS
            and rec.get("source_signal_index") == 0)


def _build_mapping_record(rec):
    """Deterministic compatibility mapping for one signed-off legacy SIGNAL record."""
    original_record_hash = canonical_hash(rec)     # tamper sentinel over the legacy row
    signal_id = rec["signal_id"]
    return CampaignsDB.make_legacy_mapping_record(
        mapping_uid=_det_id("map_", SET_ID, signal_id),
        provider_id=PROVIDER_ID,
        legacy_source_database=LEGACY_DB_REL,
        legacy_source_table=LEGACY_TABLE,
        immutable_legacy_reference=signal_id,                 # the UUID PK = immutable ref
        source_record_type=SOURCE_RECORD_TYPE,                # preserves original semantic type
        new_campaign_uid=None,                                # NO campaign boundary asserted
        compatibility_record_uid=_det_id("cmp_", PROVIDER_ID, signal_id),
        original_record_hash=original_record_hash,
        signed_off_set_identifier=SET_ID,
        mapping_status="MAPPED_VERIFIED",
        mapping_created_at=STEP2_AUTHORED_AT,
        mapping_reason=("signed-off 28 legacy signal record attributed to Farouk "
                        f"(provider={FAROUK_ALIAS}); read-only compatibility mapping, "
                        "no campaign boundary asserted"),
        schema_version=CAMPAIGNS_SCHEMA_VERSION)


# ----------------------------------------------------------------- provider registration
def register_farouk(reg: RegistryDB):
    existing = reg.con.execute(
        "SELECT display_name FROM providers WHERE provider_id=?", (PROVIDER_ID,)).fetchone()
    alias_present = reg.con.execute(
        "SELECT COUNT(*) FROM provider_aliases WHERE provider_id=? AND platform=? "
        "AND sender_identifier=?", (PROVIDER_ID, FAROUK_PLATFORM, FAROUK_ALIAS)).fetchone()[0]

    if existing is not None:
        if existing[0] != FAROUK_DISPLAY:
            raise Step2Block(
                f"provider {PROVIDER_ID} exists with conflicting display_name {existing[0]!r}")
        if not alias_present:
            raise Step2Block(
                f"provider {PROVIDER_ID} present but verified alias missing — inconsistent "
                "partial state; review required (no auto-repair)")
        return "ALREADY_PRESENT_VERIFIED"

    # fresh registration — atomic (provider + alias + 2 admin events)
    reg.begin()
    try:
        reg.append_provider(provider_id=PROVIDER_ID, display_name=FAROUK_DISPLAY,
                            added_at_utc=STEP2_AUTHORED_AT,
                            notes="first canonical provider; identity = provider_id (stable)",
                            commit=False)
        reg.append_provider_alias(
            alias_id=_det_id("ali_", PROVIDER_ID, FAROUK_PLATFORM, FAROUK_ALIAS),
            provider_id=PROVIDER_ID, platform=FAROUK_PLATFORM, sender_identifier=FAROUK_ALIAS,
            verification_status="VERIFIED", effective_from_utc=STEP2_AUTHORED_AT, commit=False)
        reg.append_administrative_event(
            admin_event_id=_det_id("adm_", "PROVIDER_REGISTERED", PROVIDER_ID),
            admin_event_type="PROVIDER_REGISTERED", subject_provider_id=PROVIDER_ID,
            payload=f"display_name={FAROUK_DISPLAY}", effective_from_utc=STEP2_AUTHORED_AT,
            actor="martyn", created_at_utc=STEP2_AUTHORED_AT, commit=False)
        reg.append_administrative_event(
            admin_event_id=_det_id("adm_", "PROVIDER_ALIAS_ADDED", PROVIDER_ID, FAROUK_ALIAS),
            admin_event_type="PROVIDER_ALIAS_ADDED", subject_provider_id=PROVIDER_ID,
            payload=f"platform={FAROUK_PLATFORM} sender={FAROUK_ALIAS} verification=VERIFIED",
            effective_from_utc=STEP2_AUTHORED_AT, actor="martyn",
            created_at_utc=STEP2_AUTHORED_AT, commit=False)
        reg.commit()
    except Exception:
        reg.rollback()
        raise
    return "REGISTERED"


# ----------------------------------------------------------------- mapping (transactional)
def map_signed_off_28(cam: CampaignsDB, records):
    eligible = [r for r in records if _eligible(r)]
    if len(eligible) != 28:
        raise Step2Block(
            f"expected 28 eligible signed-off records, found {len(eligible)} — refusing to "
            "invent/alter mappings; transaction not started")
    ids = [r["signal_id"] for r in eligible]
    if len(set(ids)) != 28:
        raise Step2Block("duplicate signal_id among eligible records — cannot uniquely map")

    built = [_build_mapping_record(r) for r in eligible]
    by_ref = {b["immutable_legacy_reference"]: b for b in built}

    existing = cam.con.execute(
        "SELECT immutable_legacy_reference, mapping_hash FROM legacy_campaign_mapping "
        "WHERE signed_off_set_identifier=?", (SET_ID,)).fetchall()

    if len(existing) == 0:
        cam.append_legacy_mappings_atomic(built)
        return "MAPPED", 28
    if len(existing) == 28:
        for ref, h in existing:
            if by_ref.get(ref) is None or by_ref[ref]["mapping_hash"] != h:
                raise Step2Block(
                    f"existing mapping for {ref} differs from deterministic recompute — "
                    "conflicting rerun; refusing to modify (append-only)")
        return "ALREADY_MAPPED_VERIFIED", 28
    raise Step2Block(
        f"partial/conflicting mapping set: {len(existing)} rows present (expected 0 or 28)")


# ----------------------------------------------------------------- top-level
def run(registry_path, campaigns_path, signal_archive_path=None):
    signal_archive_path = signal_archive_path or os.path.join(PROJECT_ROOT, LEGACY_DB_REL)
    reg = RegistryDB(registry_path)
    cam = CampaignsDB(campaigns_path)
    try:
        prov_action = register_farouk(reg)
        records, diag = load_signed_off_28(signal_archive_path)
        map_action, n = map_signed_off_28(cam, records)
        report = {
            "provider_action": prov_action,
            "mapping_action": map_action,
            "canonical_provider_count": reg.count("providers"),
            "provider_farouk_001_count": reg.con.execute(
                "SELECT COUNT(*) FROM providers WHERE provider_id=?", (PROVIDER_ID,)).fetchone()[0],
            "provider_alias_count": reg.count("provider_aliases"),
            "provider_channel_count": reg.count("provider_channels"),
            "administrative_event_count": reg.count("administrative_events"),
            "campaigns_count": cam.count("campaigns"),
            "legacy_mapping_total": cam.count("legacy_campaign_mapping"),
            "mapped_verified_count": cam.con.execute(
                "SELECT COUNT(*) FROM legacy_campaign_mapping WHERE mapping_status='MAPPED_VERIFIED'"
            ).fetchone()[0],
            "needs_review_count": cam.con.execute(
                "SELECT COUNT(*) FROM legacy_campaign_mapping WHERE mapping_status='NEEDS_REVIEW'"
            ).fetchone()[0],
            "rejected_duplicate_count": cam.con.execute(
                "SELECT COUNT(*) FROM legacy_campaign_mapping WHERE mapping_status='REJECTED_DUPLICATE'"
            ).fetchone()[0],
            "legacy_rows_found": diag["rows_found"],
        }
        return report
    finally:
        reg.close()
        cam.close()


if __name__ == "__main__":
    import json
    import init_db
    rep = run(init_db.REGISTRY_DB_PATH, init_db.CAMPAIGNS_DB_PATH)
    print(json.dumps(rep, indent=2, sort_keys=True))
