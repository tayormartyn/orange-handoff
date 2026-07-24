"""
MPK campaigns database (mpk_campaigns_v1.db) — campaign identity, events and the
non-destructive legacy bridge.

Append-only, isolated, empty of business data after Step 1 initialisation. Holds the
designed structures for campaigns, campaign events and legacy_campaign_mapping.

campaign_uid is the opaque primary identity. There is DELIBERATELY no unique constraint on
(provider_id, canonical_instrument_id[, direction]) — that absence is what lets one provider
hold multiple open campaigns on an instrument and lets opposing campaigns coexist. Step 1
inserts NO business data and creates NO legacy mapping rows.
"""
from __future__ import annotations
import os
import sqlite3

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)
from appendonly import (AppendOnlyViolation, append_only_trigger_ddl, canonical_hash,
                        reject_mutation)

SCHEMA_NAME = "mpk_campaigns"
SCHEMA_VERSION = "mpk-1.step2.0"   # step2: legacy_campaign_mapping reshaped (Section 3 fields)

_SCHEMA = {
    "campaigns": """
        CREATE TABLE IF NOT EXISTS campaigns (
            campaign_uid TEXT PRIMARY KEY,
            provider_id TEXT NOT NULL,
            source_platform TEXT,
            origin_channel_id TEXT,
            canonical_instrument_id TEXT,
            provider_campaign_reference TEXT,
            campaign_sequence INTEGER,
            direction TEXT,
            campaign_creation_status TEXT NOT NULL,
            created_at_utc TEXT,
            campaign_hash TEXT NOT NULL)""",
    "campaign_events": """
        CREATE TABLE IF NOT EXISTS campaign_events (
            event_uid TEXT PRIMARY KEY,
            provider_id TEXT NOT NULL,
            campaign_uid TEXT NOT NULL,
            event_source_channel_id TEXT,
            evidence_reference TEXT,
            association_status TEXT NOT NULL,
            association_method TEXT,
            candidate_campaign_uids TEXT,
            created_at_utc TEXT,
            event_hash TEXT NOT NULL,
            FOREIGN KEY (campaign_uid) REFERENCES campaigns (campaign_uid))""",
    # Step 2 shape (Section 3 fields). new_campaign_uid is NULLABLE: a signed-off legacy
    # SIGNAL record maps via compatibility_record_uid and asserts NO campaign boundary.
    "legacy_campaign_mapping": """
        CREATE TABLE IF NOT EXISTS legacy_campaign_mapping (
            mapping_uid TEXT PRIMARY KEY,
            provider_id TEXT NOT NULL,
            legacy_source_database TEXT NOT NULL,
            legacy_source_table TEXT NOT NULL,
            immutable_legacy_reference TEXT NOT NULL,
            source_record_type TEXT NOT NULL,
            new_campaign_uid TEXT,
            compatibility_record_uid TEXT,
            original_record_hash TEXT NOT NULL,
            signed_off_set_identifier TEXT,
            mapping_status TEXT NOT NULL,
            mapping_created_at TEXT,
            mapping_reason TEXT,
            schema_version TEXT,
            mapping_hash TEXT NOT NULL,
            FOREIGN KEY (new_campaign_uid) REFERENCES campaigns (campaign_uid),
            CHECK (new_campaign_uid IS NOT NULL OR compatibility_record_uid IS NOT NULL),
            CHECK (mapping_status IN
                ('MAPPED_VERIFIED','NEEDS_REVIEW','REJECTED_AMBIGUOUS','REJECTED_DUPLICATE')))""",
}
BUSINESS_TABLES = tuple(_SCHEMA.keys())

# uniqueness (Section 4): a legacy record cannot map twice; ids are one-to-one.
_INDEXES = [
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_legacy_ref ON legacy_campaign_mapping "
    "(legacy_source_database, legacy_source_table, immutable_legacy_reference)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_compat_uid ON legacy_campaign_mapping "
    "(compatibility_record_uid) WHERE compatibility_record_uid IS NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_new_campaign_uid ON legacy_campaign_mapping "
    "(new_campaign_uid) WHERE new_campaign_uid IS NOT NULL",
]

_SCHEMA_META_DDL = """
    CREATE TABLE IF NOT EXISTS mpk_schema_meta (
        meta_id INTEGER PRIMARY KEY AUTOINCREMENT,
        schema_name TEXT NOT NULL,
        schema_version TEXT NOT NULL,
        applied_at_utc TEXT)"""

COUNT_TABLES = ("campaigns", "legacy_campaign_mapping")


class CampaignsDB:
    def __init__(self, db_path, applied_at_utc=None):
        self.db_path = db_path
        if db_path != ":memory:":
            d = os.path.dirname(db_path)
            if d:
                os.makedirs(d, exist_ok=True)
        self.con = sqlite3.connect(db_path)
        self.con.execute("PRAGMA foreign_keys = ON")
        self._create(applied_at_utc)

    def _create(self, applied_at_utc):
        cur = self.con.cursor()
        for ddl in _SCHEMA.values():
            cur.execute(ddl)
        self._migrate_legacy_mapping(cur)          # bring an old-shape empty table to step2
        for idx in _INDEXES:
            cur.execute(idx)
        for t in BUSINESS_TABLES:
            for trig in append_only_trigger_ddl(t):
                cur.execute(trig)
        cur.execute(_SCHEMA_META_DDL)
        already = cur.execute(
            "SELECT COUNT(*) FROM mpk_schema_meta WHERE schema_name=? AND schema_version=?",
            (SCHEMA_NAME, SCHEMA_VERSION)).fetchone()[0]
        if not already:
            cur.execute(
                "INSERT INTO mpk_schema_meta (schema_name, schema_version, applied_at_utc) "
                "VALUES (?,?,?)", (SCHEMA_NAME, SCHEMA_VERSION, applied_at_utc))
        self.con.commit()

    def _migrate_legacy_mapping(self, cur):
        """Forward-migrate an EMPTY old-shape legacy_campaign_mapping to the step2 shape.

        Schema control only (separate from business mutation). Blocks if the old-shape
        table already holds rows — never repairs data with UPDATE/DELETE.
        """
        cols = [r[1] for r in cur.execute(
            "PRAGMA table_info(legacy_campaign_mapping)").fetchall()]
        if "compatibility_record_uid" in cols:
            return                                  # already step2 shape
        n = cur.execute("SELECT COUNT(*) FROM legacy_campaign_mapping").fetchone()[0]
        if n != 0:
            raise RuntimeError(
                "BLOCK: legacy_campaign_mapping has rows in the pre-step2 shape; refusing "
                "to migrate (append-only — no destructive repair).")
        cur.execute("DROP TRIGGER IF EXISTS noupd_legacy_campaign_mapping")
        cur.execute("DROP TRIGGER IF EXISTS nodel_legacy_campaign_mapping")
        cur.execute("DROP TABLE legacy_campaign_mapping")
        cur.execute(_SCHEMA["legacy_campaign_mapping"])

    def _append(self, table, record: dict, commit=True):
        if table not in BUSINESS_TABLES:
            raise AppendOnlyViolation(f"unknown business table {table!r}")
        cols = list(record.keys())
        sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})"
        reject_mutation(sql)
        self.con.execute(sql, [record[c] for c in cols])
        if commit:
            self.con.commit()
        return record

    # -- appenders (unused in Step 1; for later steps / temp-DB tests only) ----
    def append_campaign(self, *, campaign_uid, provider_id, campaign_creation_status,
                        source_platform=None, origin_channel_id=None,
                        canonical_instrument_id=None, provider_campaign_reference=None,
                        campaign_sequence=None, direction=None, created_at_utc=None):
        rec = {"campaign_uid": campaign_uid, "provider_id": provider_id,
               "source_platform": source_platform, "origin_channel_id": origin_channel_id,
               "canonical_instrument_id": canonical_instrument_id,
               "provider_campaign_reference": provider_campaign_reference,
               "campaign_sequence": campaign_sequence, "direction": direction,
               "campaign_creation_status": campaign_creation_status,
               "created_at_utc": created_at_utc}
        rec["campaign_hash"] = canonical_hash(rec)
        return self._append("campaigns", rec)

    def append_campaign_event(self, *, event_uid, provider_id, campaign_uid, association_status,
                              event_source_channel_id=None, evidence_reference=None,
                              association_method=None, candidate_campaign_uids=None,
                              created_at_utc=None):
        rec = {"event_uid": event_uid, "provider_id": provider_id, "campaign_uid": campaign_uid,
               "event_source_channel_id": event_source_channel_id,
               "evidence_reference": evidence_reference, "association_status": association_status,
               "association_method": association_method,
               "candidate_campaign_uids": candidate_campaign_uids,
               "created_at_utc": created_at_utc}
        rec["event_hash"] = canonical_hash(rec)
        return self._append("campaign_events", rec)

    @staticmethod
    def make_legacy_mapping_record(*, mapping_uid, provider_id, legacy_source_database,
                                   legacy_source_table, immutable_legacy_reference,
                                   source_record_type, original_record_hash, mapping_status,
                                   new_campaign_uid=None, compatibility_record_uid=None,
                                   signed_off_set_identifier=None, mapping_created_at=None,
                                   mapping_reason=None, schema_version=None):
        rec = {"mapping_uid": mapping_uid, "provider_id": provider_id,
               "legacy_source_database": legacy_source_database,
               "legacy_source_table": legacy_source_table,
               "immutable_legacy_reference": immutable_legacy_reference,
               "source_record_type": source_record_type,
               "new_campaign_uid": new_campaign_uid,
               "compatibility_record_uid": compatibility_record_uid,
               "original_record_hash": original_record_hash,
               "signed_off_set_identifier": signed_off_set_identifier,
               "mapping_status": mapping_status, "mapping_created_at": mapping_created_at,
               "mapping_reason": mapping_reason, "schema_version": schema_version}
        rec["mapping_hash"] = canonical_hash(rec)
        return rec

    def append_legacy_mapping(self, **kwargs):
        return self._append("legacy_campaign_mapping", self.make_legacy_mapping_record(**kwargs))

    def append_legacy_mappings_atomic(self, records):
        """Insert a full set of pre-built mapping records in ONE transaction.

        All commit together or none do (Section 4). Append-only triggers are unaffected
        by ROLLBACK (they fire only on UPDATE/DELETE statements, not on transaction abort).
        """
        try:
            for rec in records:
                self._append("legacy_campaign_mapping", rec, commit=False)
            self.con.commit()
        except Exception:
            self.con.rollback()
            raise
        return len(records)

    # -- read helpers ---------------------------------------------------------
    def table_names(self):
        rows = self.con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return sorted(r[0] for r in rows if r[0] != "sqlite_sequence")

    def trigger_names(self):
        rows = self.con.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'").fetchall()
        return sorted(r[0] for r in rows)

    def count(self, table):
        return self.con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def business_counts(self):
        return {t: self.count(t) for t in COUNT_TABLES}

    def schema_meta_rows(self):
        cur = self.con.execute(
            "SELECT schema_name, schema_version, applied_at_utc FROM mpk_schema_meta "
            "ORDER BY meta_id")
        return [dict(zip(("schema_name", "schema_version", "applied_at_utc"), r))
                for r in cur.fetchall()]

    def schema_fingerprint(self):
        rows = self.con.execute(
            "SELECT type, name, sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name").fetchall()
        return canonical_hash({"objects": rows})

    def close(self):
        self.con.close()
