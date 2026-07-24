"""
ASSOC-1 decision store (association_decisions_v1.db) — append-only, isolated.

Stores association DECISIONS only. Never writes to any campaign / provider / instrument /
Gold / Telegram / broker database. Corrections are represented by a NEW row with
supersedes_decision_uid (not part of the live ASSOC-1 workflow).
"""
from __future__ import annotations
import json
import os
import sqlite3

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)
from _util import AppendOnlyViolation, append_only_trigger_ddl, reject_mutation

SCHEMA_NAME = "association_decisions"
SCHEMA_VERSION = "assoc-1.0"
DATA_DIR = os.path.join(_HERE, "data")
DB_PATH = os.path.join(DATA_DIR, "association_decisions_v1.db")

_DDL = """
    CREATE TABLE IF NOT EXISTS association_decisions (
        rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
        association_decision_uid TEXT NOT NULL,
        source_message_uid TEXT NOT NULL,
        provider_id TEXT NOT NULL,
        source_channel_id TEXT,
        source_message_timestamp TEXT,
        management_intent TEXT,
        association_status TEXT NOT NULL,
        associated_campaign_uid TEXT,
        candidate_campaign_uids TEXT,
        campaigns_considered TEXT,
        association_context TEXT,
        exclusion_reasons TEXT,
        rule_fired TEXT,
        evidence_tier TEXT,
        evidence_references TEXT,
        review_reason TEXT,
        instruction_executed INTEGER NOT NULL,
        broker_confirmed INTEGER NOT NULL,
        supersedes_decision_uid TEXT,
        correction_reason TEXT,
        review_provenance TEXT,
        decision_hash TEXT NOT NULL,
        engine_version TEXT,
        created_at TEXT,
        schema_version TEXT,
        CHECK (association_status IN
            ('ASSOCIATED','NEEDS_REVIEW','UNASSOCIATED','REJECTED_PROVIDER_MISMATCH',
             'REJECTED_UNTRACKED_PROVIDER')),
        CHECK (instruction_executed = 0),
        CHECK (broker_confirmed = 0))"""


class AssociationDecisionsDB:
    def __init__(self, db_path):
        self.db_path = db_path
        if db_path != ":memory:":
            d = os.path.dirname(db_path)
            if d:
                os.makedirs(d, exist_ok=True)
        self.con = sqlite3.connect(db_path)
        cur = self.con.cursor()
        cur.execute(_DDL)
        for trig in append_only_trigger_ddl("association_decisions"):
            cur.execute(trig)
        cur.execute("""CREATE TABLE IF NOT EXISTS assoc_schema_meta (
            meta_id INTEGER PRIMARY KEY AUTOINCREMENT, schema_name TEXT, schema_version TEXT,
            applied_at_utc TEXT)""")
        if not cur.execute("SELECT COUNT(*) FROM assoc_schema_meta WHERE schema_version=?",
                           (SCHEMA_VERSION,)).fetchone()[0]:
            cur.execute("INSERT INTO assoc_schema_meta (schema_name, schema_version) VALUES (?,?)",
                        (SCHEMA_NAME, SCHEMA_VERSION))
        self.con.commit()

    def append(self, decision, *, created_at=None, supersedes_decision_uid=None,
               correction_reason=None, review_provenance=None):
        rec = {
            "association_decision_uid": decision["association_decision_uid"],
            "source_message_uid": decision["source_message_uid"],
            "provider_id": decision["provider_id"],
            "source_channel_id": decision["source_channel_id"],
            "source_message_timestamp": decision["source_message_timestamp"],
            "management_intent": decision["management_intent"],
            "association_status": decision["association_status"],
            "associated_campaign_uid": decision["associated_campaign_uid"],
            "candidate_campaign_uids": json.dumps(decision["candidate_campaign_uids"], sort_keys=True),
            "campaigns_considered": json.dumps(decision["campaigns_considered"], sort_keys=True),
            "association_context": decision["association_context"],
            "exclusion_reasons": json.dumps(decision["exclusion_reasons"], sort_keys=True),
            "rule_fired": decision["rule_fired"],
            "evidence_tier": decision["evidence_tier"],
            "evidence_references": json.dumps(decision["evidence_references"], sort_keys=True),
            "review_reason": decision["review_reason"],
            "instruction_executed": 1 if decision["instruction_executed"] else 0,
            "broker_confirmed": 1 if decision["broker_confirmed"] else 0,
            "supersedes_decision_uid": supersedes_decision_uid,
            "correction_reason": correction_reason,
            "review_provenance": review_provenance,
            "decision_hash": decision["decision_hash"],
            "engine_version": decision["engine_version"],
            "created_at": created_at,
            "schema_version": SCHEMA_VERSION,
        }
        cols = list(rec.keys())
        sql = f"INSERT INTO association_decisions ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})"
        reject_mutation(sql)
        self.con.execute(sql, [rec[c] for c in cols])
        self.con.commit()
        return rec

    def count(self):
        return self.con.execute("SELECT COUNT(*) FROM association_decisions").fetchone()[0]

    def close(self):
        self.con.close()
