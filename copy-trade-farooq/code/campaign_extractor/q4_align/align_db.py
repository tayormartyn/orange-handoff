"""
Append-only Q4 alignment evidence store: data/q4_alignment_v1.db. WRITE-ONLY TARGET for Q4.

Immutable by construction (BEFORE UPDATE/DELETE RAISE(ABORT); no update/delete methods). Stores
one row per alignment run with the signal reference, both anchor results, timing, and the hard
OBSERVATION_ONLY / NOT_A_FILL / NOT_AN_OUTCOME labels. Never writes to quote/Telegram/campaign data.
"""
from __future__ import annotations
import json
import os
import sqlite3
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))
DEFAULT_DB = os.path.join(PROJECT_ROOT, "data", "q4_alignment_v1.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS alignment_runs (
  rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
  message_id TEXT,
  evidence_ref TEXT,
  direction TEXT,
  config_version TEXT,
  delivery_result TEXT,
  delivery_reason TEXT,
  actionable_result TEXT,
  actionable_reason TEXT,
  assertion_label TEXT NOT NULL,
  fill_label TEXT NOT NULL,
  outcome_label TEXT NOT NULL,
  result_json TEXT NOT NULL,
  persisted_utc TEXT
);
CREATE TRIGGER IF NOT EXISTS align_no_update BEFORE UPDATE ON alignment_runs
  BEGIN SELECT RAISE(ABORT, 'append-only: alignment_runs is immutable'); END;
CREATE TRIGGER IF NOT EXISTS align_no_delete BEFORE DELETE ON alignment_runs
  BEGIN SELECT RAISE(ABORT, 'append-only: alignment_runs is immutable'); END;
"""


class AlignDB:
    def __init__(self, path=None):
        self.path = path or DEFAULT_DB
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def insert_run(self, result):
        lbl = result.get("labels", {})
        sig = result.get("signal", {})
        row = (
            sig.get("message_id"), sig.get("evidence_ref"), sig.get("direction"),
            result.get("config_version"),
            result.get("delivery", {}).get("result"), result.get("delivery", {}).get("reason"),
            result.get("actionable", {}).get("result"), result.get("actionable", {}).get("reason"),
            lbl.get("assertion", "OBSERVATION_ONLY"), lbl.get("fill", "NOT_A_FILL"),
            lbl.get("outcome", "NOT_AN_OUTCOME"),
            json.dumps(result, default=str),
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        self.conn.execute(
            "INSERT INTO alignment_runs (message_id,evidence_ref,direction,config_version,"
            "delivery_result,delivery_reason,actionable_result,actionable_reason,"
            "assertion_label,fill_label,outcome_label,result_json,persisted_utc) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", row)
        self.conn.commit()
        return True

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM alignment_runs").fetchone()[0]

    def close(self):
        self.conn.close()
