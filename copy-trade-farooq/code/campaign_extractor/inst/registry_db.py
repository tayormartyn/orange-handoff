"""
INST-1 canonical instrument registry database (instrument_registry_v1.db).

Append-only, isolated. Six business/history tables + a separate schema-control table.
Underlying / instrument / contract / venue concepts are kept strictly distinct; a canonical
instrument record implies NOTHING about venue support, broker availability, or trading
eligibility (there is no venue field here — venue routing is out of scope for INST-1).
"""
from __future__ import annotations
import os
import sqlite3

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)
from _util import AppendOnlyViolation, append_only_trigger_ddl, canonical_hash, reject_mutation

SCHEMA_NAME = "instrument_registry"
SCHEMA_VERSION = "inst-1a.0"   # 1a: NULL-safe semantic-duplicate uniqueness on mapping_rules

ASSET_CLASSES = ("METAL", "CRYPTO", "ENERGY", "EQUITY", "INDEX", "FX", "COMMODITY", "UNKNOWN")
CONTRACT_TYPES = ("SPOT_REFERENCE", "CFD", "PERPETUAL", "FUTURE", "EQUITY_SHARE",
                  "INDEX_CFD", "UNKNOWN_CONTRACT")
MAPPING_STATUSES = ("EXACT_MATCH", "PROVIDER_ALIAS_MATCH", "NORMALISED_MATCH",
                    "AMBIGUOUS_NEEDS_REVIEW", "UNKNOWN_NEEDS_REVIEW", "REJECTED_INVALID")
RULE_SCOPES = ("GLOBAL", "PROVIDER")

_SCHEMA = {
    "canonical_underlyings": """
        CREATE TABLE IF NOT EXISTS canonical_underlyings (
            underlying_id TEXT PRIMARY KEY,
            display_label TEXT,
            asset_class TEXT NOT NULL,
            notes TEXT,
            created_at TEXT,
            schema_version TEXT,
            row_hash TEXT NOT NULL,
            CHECK (asset_class IN
                ('METAL','CRYPTO','ENERGY','EQUITY','INDEX','FX','COMMODITY','UNKNOWN')))""",
    "canonical_instruments": """
        CREATE TABLE IF NOT EXISTS canonical_instruments (
            instrument_id TEXT PRIMARY KEY,
            canonical_underlying_id TEXT NOT NULL,
            contract_type TEXT NOT NULL,
            base_asset TEXT,
            quote_asset TEXT,
            settlement_asset TEXT,
            display_label TEXT,
            notes TEXT,
            created_at TEXT,
            schema_version TEXT,
            row_hash TEXT NOT NULL,
            FOREIGN KEY (canonical_underlying_id) REFERENCES canonical_underlyings (underlying_id),
            CHECK (contract_type IN
                ('SPOT_REFERENCE','CFD','PERPETUAL','FUTURE','EQUITY_SHARE','INDEX_CFD',
                 'UNKNOWN_CONTRACT')))""",
    "global_aliases": """
        CREATE TABLE IF NOT EXISTS global_aliases (
            alias_uid TEXT PRIMARY KEY,
            normalised_token TEXT NOT NULL,
            raw_example TEXT,
            canonical_underlying_id TEXT,
            canonical_instrument_id TEXT,
            note TEXT,
            created_at TEXT,
            schema_version TEXT,
            row_hash TEXT NOT NULL)""",
    "provider_aliases": """
        CREATE TABLE IF NOT EXISTS provider_aliases (
            alias_uid TEXT PRIMARY KEY,
            provider_id TEXT NOT NULL,
            normalised_token TEXT NOT NULL,
            raw_example TEXT,
            canonical_underlying_id TEXT,
            canonical_instrument_id TEXT,
            mapping_rule_uid TEXT,
            effective_from TEXT,
            effective_to TEXT,
            created_at TEXT,
            schema_version TEXT,
            row_hash TEXT NOT NULL)""",
    "mapping_rules": """
        CREATE TABLE IF NOT EXISTS mapping_rules (
            mapping_rule_uid TEXT PRIMARY KEY,
            rule_version INTEGER NOT NULL,
            scope TEXT NOT NULL,
            provider_id TEXT,
            input_token TEXT NOT NULL,
            target_underlying_id TEXT,
            target_instrument_id TEXT,
            effective_from TEXT NOT NULL,
            effective_to TEXT,
            admin_reason TEXT,
            supersedes_rule_uid TEXT,
            created_at TEXT,
            schema_version TEXT,
            row_hash TEXT NOT NULL,
            CHECK (scope IN ('GLOBAL','PROVIDER')))""",
    "mapping_decisions": """
        CREATE TABLE IF NOT EXISTS mapping_decisions (
            rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id TEXT NOT NULL,
            original_raw_symbol TEXT,
            normalised_token TEXT,
            provider_id TEXT,
            source_platform TEXT,
            source_message_id TEXT,
            source_message_timestamp TEXT,
            input_provenance TEXT,
            candidate_underlyings TEXT,
            candidate_instruments TEXT,
            selected_underlying_id TEXT,
            selected_instrument_id TEXT,
            asset_class TEXT,
            contract_type TEXT,
            venue_contract TEXT NOT NULL,
            mapping_status TEXT NOT NULL,
            mapping_rule_versions TEXT,
            rule_effective_from TEXT,
            rule_effective_to TEXT,
            review_reason TEXT,
            automatically_resolved INTEGER,
            canonical_decision_hash TEXT NOT NULL,
            created_at TEXT,
            schema_version TEXT,
            CHECK (mapping_status IN
                ('EXACT_MATCH','PROVIDER_ALIAS_MATCH','NORMALISED_MATCH',
                 'AMBIGUOUS_NEEDS_REVIEW','UNKNOWN_NEEDS_REVIEW','REJECTED_INVALID')),
            CHECK (venue_contract = 'NOT_ROUTED'))""",
}
BUSINESS_TABLES = tuple(_SCHEMA.keys())

_INDEXES = [
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_rule_version "
    "ON mapping_rules (input_token, scope, provider_id, rule_version)",
    # INST-1A: NULL-SAFE semantic-duplicate guard. A semantic rule is identified by token +
    # scope + provider + target underlying + target instrument + version + effective window.
    # COALESCE sentinel '<<NULL>>' is OUTSIDE the legitimate value domain (ids/timestamps),
    # so NULL provider_id / target / effective_to can NOT bypass uniqueness. Distinct targets
    # (OIL->WTI vs OIL->BRENT) and versioned corrections remain permitted.
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_rule_semantic ON mapping_rules ("
    "input_token, scope, COALESCE(provider_id,'<<NULL>>'), "
    "COALESCE(target_underlying_id,'<<NULL>>'), COALESCE(target_instrument_id,'<<NULL>>'), "
    "rule_version, effective_from, COALESCE(effective_to,'<<NULL>>'))",
    "CREATE INDEX IF NOT EXISTS ix_rule_token ON mapping_rules (input_token, scope)",
    "CREATE INDEX IF NOT EXISTS ix_galias_token ON global_aliases (normalised_token)",
    "CREATE INDEX IF NOT EXISTS ix_palias_token ON provider_aliases (provider_id, normalised_token)",
]

_SCHEMA_META_DDL = """
    CREATE TABLE IF NOT EXISTS inst_schema_meta (
        meta_id INTEGER PRIMARY KEY AUTOINCREMENT,
        schema_name TEXT NOT NULL, schema_version TEXT NOT NULL, applied_at_utc TEXT)"""

COUNT_TABLES = ("canonical_underlyings", "canonical_instruments", "global_aliases",
                "provider_aliases", "mapping_rules", "mapping_decisions")


class InstrumentRegistryDB:
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
        for idx in _INDEXES:
            cur.execute(idx)
        for t in BUSINESS_TABLES:
            for trig in append_only_trigger_ddl(t):
                cur.execute(trig)
        cur.execute(_SCHEMA_META_DDL)
        if not cur.execute("SELECT COUNT(*) FROM inst_schema_meta WHERE schema_name=? AND "
                           "schema_version=?", (SCHEMA_NAME, SCHEMA_VERSION)).fetchone()[0]:
            cur.execute("INSERT INTO inst_schema_meta (schema_name, schema_version, applied_at_utc)"
                        " VALUES (?,?,?)", (SCHEMA_NAME, SCHEMA_VERSION, applied_at_utc))
        self.con.commit()

    # -- insert-only writer ---------------------------------------------------
    def _append(self, table, record, commit=True):
        if table not in BUSINESS_TABLES:
            raise AppendOnlyViolation(f"unknown business table {table!r}")
        cols = list(record.keys())
        sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})"
        reject_mutation(sql)
        self.con.execute(sql, [record[c] for c in cols])
        if commit:
            self.con.commit()
        return record

    def append_many_atomic(self, items):
        """items: list of (table, record). All commit together or none (full rollback)."""
        try:
            for table, rec in items:
                self._append(table, rec, commit=False)
            self.con.commit()
        except Exception:
            self.con.rollback()
            raise
        return len(items)

    # -- typed record builders (compute row_hash) -----------------------------
    @staticmethod
    def _h(rec):
        rec["row_hash"] = canonical_hash({k: v for k, v in rec.items() if k != "row_hash"})
        return rec

    def underlying(self, **f):
        return self._h({"underlying_id": f["underlying_id"], "display_label": f.get("display_label"),
                        "asset_class": f["asset_class"], "notes": f.get("notes"),
                        "created_at": f.get("created_at"), "schema_version": SCHEMA_VERSION})

    def instrument(self, **f):
        return self._h({"instrument_id": f["instrument_id"],
                        "canonical_underlying_id": f["canonical_underlying_id"],
                        "contract_type": f["contract_type"], "base_asset": f.get("base_asset"),
                        "quote_asset": f.get("quote_asset"),
                        "settlement_asset": f.get("settlement_asset"),
                        "display_label": f.get("display_label"), "notes": f.get("notes"),
                        "created_at": f.get("created_at"), "schema_version": SCHEMA_VERSION})

    def global_alias(self, **f):
        return self._h({"alias_uid": f["alias_uid"], "normalised_token": f["normalised_token"],
                        "raw_example": f.get("raw_example"),
                        "canonical_underlying_id": f.get("canonical_underlying_id"),
                        "canonical_instrument_id": f.get("canonical_instrument_id"),
                        "note": f.get("note"), "created_at": f.get("created_at"),
                        "schema_version": SCHEMA_VERSION})

    def provider_alias(self, **f):
        return self._h({"alias_uid": f["alias_uid"], "provider_id": f["provider_id"],
                        "normalised_token": f["normalised_token"], "raw_example": f.get("raw_example"),
                        "canonical_underlying_id": f.get("canonical_underlying_id"),
                        "canonical_instrument_id": f.get("canonical_instrument_id"),
                        "mapping_rule_uid": f.get("mapping_rule_uid"),
                        "effective_from": f.get("effective_from"),
                        "effective_to": f.get("effective_to"), "created_at": f.get("created_at"),
                        "schema_version": SCHEMA_VERSION})

    def rule(self, **f):
        return self._h({"mapping_rule_uid": f["mapping_rule_uid"], "rule_version": f["rule_version"],
                        "scope": f["scope"], "provider_id": f.get("provider_id"),
                        "input_token": f["input_token"],
                        "target_underlying_id": f.get("target_underlying_id"),
                        "target_instrument_id": f.get("target_instrument_id"),
                        "effective_from": f["effective_from"], "effective_to": f.get("effective_to"),
                        "admin_reason": f.get("admin_reason"),
                        "supersedes_rule_uid": f.get("supersedes_rule_uid"),
                        "created_at": f.get("created_at"), "schema_version": SCHEMA_VERSION})

    # -- read helpers ---------------------------------------------------------
    def count(self, table):
        return self.con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def counts(self):
        return {t: self.count(t) for t in COUNT_TABLES}

    def table_names(self):
        return sorted(r[0] for r in self.con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'") if r[0] != "sqlite_sequence")

    def trigger_names(self):
        return sorted(r[0] for r in self.con.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'"))

    def close(self):
        self.con.close()
