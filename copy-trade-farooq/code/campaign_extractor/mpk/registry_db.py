"""
MPK registry database (mpk_registry_v1.db) — the immutable provider/instrument registry.

Append-only, isolated, empty of business data after Step 1 initialisation. Holds the
designed structures for providers, provider aliases, provider channels, channel-permission
events, canonical instruments, instrument aliases, and administrative events.

Identity rule: provider_id is an opaque, stable primary key — display names / usernames /
channel titles are attributes only and are NEVER identity. No business data is inserted by
this module during Step 1; the appenders exist for later steps and for offline tests that
operate on temporary/in-memory copies.
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

SCHEMA_NAME = "mpk_registry"
SCHEMA_VERSION = "mpk-2a.0"   # 2a: source_candidates + sender assignments + status events

# ----- business / history tables (append-only) -----
_SCHEMA = {
    "providers": """
        CREATE TABLE IF NOT EXISTS providers (
            provider_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            added_at_utc TEXT,
            notes TEXT,
            registry_hash TEXT NOT NULL)""",
    "provider_aliases": """
        CREATE TABLE IF NOT EXISTS provider_aliases (
            alias_id TEXT PRIMARY KEY,
            provider_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            sender_identifier TEXT NOT NULL,
            effective_from_utc TEXT,
            effective_to_utc TEXT,
            verification_status TEXT NOT NULL,
            created_at_utc TEXT,
            alias_hash TEXT NOT NULL,
            FOREIGN KEY (provider_id) REFERENCES providers (provider_id))""",
    "provider_channels": """
        CREATE TABLE IF NOT EXISTS provider_channels (
            channel_assignment_id TEXT PRIMARY KEY,
            provider_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            immutable_channel_id TEXT NOT NULL,
            channel_title_for_display_only TEXT,
            effective_from_utc TEXT,
            effective_to_utc TEXT,
            created_at_utc TEXT,
            assignment_hash TEXT NOT NULL,
            FOREIGN KEY (provider_id) REFERENCES providers (provider_id))""",
    "channel_permission_events": """
        CREATE TABLE IF NOT EXISTS channel_permission_events (
            permission_event_id TEXT PRIMARY KEY,
            provider_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            immutable_channel_id TEXT NOT NULL,
            capture_status TEXT NOT NULL,
            tracking_status TEXT NOT NULL,
            effective_from_utc TEXT,
            reason TEXT,
            created_at_utc TEXT,
            event_hash TEXT NOT NULL,
            FOREIGN KEY (provider_id) REFERENCES providers (provider_id))""",
    "canonical_instruments": """
        CREATE TABLE IF NOT EXISTS canonical_instruments (
            canonical_instrument_id TEXT PRIMARY KEY,
            normalized_underlying TEXT NOT NULL,
            instrument_kind TEXT,
            display_label TEXT,
            notes TEXT)""",
    "instrument_aliases": """
        CREATE TABLE IF NOT EXISTS instrument_aliases (
            mapping_id TEXT PRIMARY KEY,
            raw_symbol TEXT NOT NULL,
            provider_id TEXT,
            normalized_underlying TEXT,
            canonical_instrument_id TEXT,
            instrument_mapping_status TEXT NOT NULL,
            mapping_evidence TEXT,
            mapping_version TEXT,
            created_at_utc TEXT,
            mapping_hash TEXT NOT NULL)""",
    "administrative_events": """
        CREATE TABLE IF NOT EXISTS administrative_events (
            admin_event_id TEXT PRIMARY KEY,
            admin_event_type TEXT NOT NULL,
            subject_provider_id TEXT,
            payload TEXT,
            effective_from_utc TEXT,
            actor TEXT,
            created_at_utc TEXT,
            admin_event_hash TEXT NOT NULL,
            prev_event_hash TEXT)""",
    # ---- MPK-2A additions (append-only; existing tables/data untouched) ----
    "source_candidates": """
        CREATE TABLE IF NOT EXISTS source_candidates (
            rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_uid TEXT NOT NULL,
            platform TEXT NOT NULL,
            immutable_sender_id TEXT,
            immutable_channel_id TEXT,
            observed_display_name TEXT,
            observed_username TEXT,
            observed_channel_title TEXT,
            first_observed_at TEXT,
            last_observed_at TEXT,
            evidence_reference TEXT,
            proposed_provider_id TEXT,
            identity_status TEXT NOT NULL,
            review_status TEXT NOT NULL,
            supersedes_rowseq INTEGER,
            created_at TEXT,
            schema_version TEXT,
            candidate_hash TEXT NOT NULL,
            CHECK (identity_status IN
                ('UNVERIFIED','CANDIDATE_MATCH','VERIFIED','REJECTED','NEEDS_REVIEW')),
            CHECK (review_status IN
                ('UNVERIFIED','CANDIDATE_MATCH','VERIFIED','REJECTED','NEEDS_REVIEW')))""",
    "provider_sender_assignments": """
        CREATE TABLE IF NOT EXISTS provider_sender_assignments (
            assignment_id TEXT PRIMARY KEY,
            provider_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            immutable_sender_id TEXT NOT NULL,
            effective_from TEXT NOT NULL,
            effective_to TEXT,
            created_at TEXT,
            assignment_hash TEXT NOT NULL,
            FOREIGN KEY (provider_id) REFERENCES providers (provider_id))""",
    "provider_status_events": """
        CREATE TABLE IF NOT EXISTS provider_status_events (
            status_event_id TEXT PRIMARY KEY,
            provider_id TEXT NOT NULL,
            status TEXT NOT NULL,
            effective_from TEXT NOT NULL,
            reason TEXT,
            created_at TEXT,
            event_hash TEXT NOT NULL,
            FOREIGN KEY (provider_id) REFERENCES providers (provider_id),
            CHECK (status IN ('ACTIVE','PAUSED','RETIRED')))""",
}
BUSINESS_TABLES = tuple(_SCHEMA.keys())

# extra uniqueness (duplicate immutable identity rejection beyond the PKs)
_INDEXES = [
    # an alias claim is unique per (platform, sender_identifier) at a given effective_from
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_alias_identity "
    "ON provider_aliases (platform, sender_identifier, effective_from_utc)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_channel_assignment "
    "ON provider_channels (platform, immutable_channel_id, provider_id, effective_from_utc)",
    # MPK-2A fail-closed conflict backstops:
    # only ONE open-ended (active) assignment per immutable channel/sender across ALL providers
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_channel_active_single "
    "ON provider_channels (platform, immutable_channel_id) WHERE effective_to_utc IS NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_sender_active_single "
    "ON provider_sender_assignments (platform, immutable_sender_id) WHERE effective_to IS NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_sender_assignment_identity "
    "ON provider_sender_assignments (platform, immutable_sender_id, provider_id, effective_from)",
]

# ----- schema-control table (NOT append-only; managed separately from business rows) -----
_SCHEMA_META_DDL = """
    CREATE TABLE IF NOT EXISTS mpk_schema_meta (
        meta_id INTEGER PRIMARY KEY AUTOINCREMENT,
        schema_name TEXT NOT NULL,
        schema_version TEXT NOT NULL,
        applied_at_utc TEXT)"""

# the six canonical business-record-count tables the Step 1 report names
COUNT_TABLES = ("providers", "provider_aliases", "provider_channels",
                "administrative_events")


class RegistryDB:
    def __init__(self, db_path, applied_at_utc=None):
        self.db_path = db_path
        if db_path != ":memory:":
            d = os.path.dirname(db_path)
            if d:
                os.makedirs(d, exist_ok=True)
        self.con = sqlite3.connect(db_path)
        self.con.execute("PRAGMA foreign_keys = ON")
        self._create(applied_at_utc)

    # -- deterministic schema initialisation ----------------------------------
    def _create(self, applied_at_utc):
        cur = self.con.cursor()
        for ddl in _SCHEMA.values():
            cur.execute(ddl)
        for idx in _INDEXES:
            cur.execute(idx)
        for t in BUSINESS_TABLES:
            for trig in append_only_trigger_ddl(t):
                cur.execute(trig)
        cur.execute(_SCHEMA_META_DDL)
        # record the migration exactly once (schema-control, not business data)
        already = cur.execute(
            "SELECT COUNT(*) FROM mpk_schema_meta WHERE schema_name=? AND schema_version=?",
            (SCHEMA_NAME, SCHEMA_VERSION)).fetchone()[0]
        if not already:
            cur.execute(
                "INSERT INTO mpk_schema_meta (schema_name, schema_version, applied_at_utc) "
                "VALUES (?,?,?)", (SCHEMA_NAME, SCHEMA_VERSION, applied_at_utc))
        self.con.commit()

    # -- insert-only writer (the ONLY mutation path; constructs INSERT only) ---
    def _append(self, table, record: dict, commit=True):
        if table not in BUSINESS_TABLES:
            raise AppendOnlyViolation(f"unknown business table {table!r}")
        cols = list(record.keys())
        sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})"
        reject_mutation(sql)                       # app-level guard (INSERT passes)
        self.con.execute(sql, [record[c] for c in cols])
        if commit:
            self.con.commit()
        return record

    def begin(self):
        self.con.execute("BEGIN")

    def commit(self):
        self.con.commit()

    def rollback(self):
        self.con.rollback()

    # -- appenders (unused in Step 1; for later steps / temp-DB tests only) ----
    def append_provider(self, *, provider_id, display_name, added_at_utc=None, notes=None,
                        commit=True):
        rec = {"provider_id": provider_id, "display_name": display_name,
               "added_at_utc": added_at_utc, "notes": notes}
        rec["registry_hash"] = canonical_hash(rec)
        return self._append("providers", rec, commit=commit)

    def append_provider_alias(self, *, alias_id, provider_id, platform, sender_identifier,
                              verification_status, effective_from_utc=None,
                              effective_to_utc=None, created_at_utc=None, commit=True):
        rec = {"alias_id": alias_id, "provider_id": provider_id, "platform": platform,
               "sender_identifier": sender_identifier, "effective_from_utc": effective_from_utc,
               "effective_to_utc": effective_to_utc, "verification_status": verification_status,
               "created_at_utc": created_at_utc}
        rec["alias_hash"] = canonical_hash(rec)
        return self._append("provider_aliases", rec, commit=commit)

    def append_provider_channel(self, *, channel_assignment_id, provider_id, platform,
                                immutable_channel_id, channel_title_for_display_only=None,
                                effective_from_utc=None, effective_to_utc=None,
                                created_at_utc=None, commit=True):
        rec = {"channel_assignment_id": channel_assignment_id, "provider_id": provider_id,
               "platform": platform, "immutable_channel_id": immutable_channel_id,
               "channel_title_for_display_only": channel_title_for_display_only,
               "effective_from_utc": effective_from_utc, "effective_to_utc": effective_to_utc,
               "created_at_utc": created_at_utc}
        rec["assignment_hash"] = canonical_hash(rec)
        return self._append("provider_channels", rec, commit=commit)

    def append_channel_permission_event(self, *, permission_event_id, provider_id, platform,
                                        immutable_channel_id, capture_status, tracking_status,
                                        effective_from_utc=None, reason=None, created_at_utc=None,
                                        commit=True):
        rec = {"permission_event_id": permission_event_id, "provider_id": provider_id,
               "platform": platform, "immutable_channel_id": immutable_channel_id,
               "capture_status": capture_status, "tracking_status": tracking_status,
               "effective_from_utc": effective_from_utc, "reason": reason,
               "created_at_utc": created_at_utc}
        rec["event_hash"] = canonical_hash(rec)
        return self._append("channel_permission_events", rec, commit=commit)

    def append_administrative_event(self, *, admin_event_id, admin_event_type,
                                    subject_provider_id=None, payload=None,
                                    effective_from_utc=None, actor=None, created_at_utc=None,
                                    prev_event_hash=None, commit=True):
        rec = {"admin_event_id": admin_event_id, "admin_event_type": admin_event_type,
               "subject_provider_id": subject_provider_id, "payload": payload,
               "effective_from_utc": effective_from_utc, "actor": actor,
               "created_at_utc": created_at_utc}
        rec["admin_event_hash"] = canonical_hash(rec)
        rec["prev_event_hash"] = prev_event_hash
        return self._append("administrative_events", rec, commit=commit)

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
