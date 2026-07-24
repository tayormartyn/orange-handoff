"""Append-only demo-execution audit store: data/demo_execution_v1.db. BEFORE UPDATE/DELETE RAISE;
no update/delete methods. Records this phase's proposal lifecycle only. Never touches signal /
review / paper-observation records."""
from __future__ import annotations
import json
import sqlite3
import time

import config as CFG

_SCHEMA = """
CREATE TABLE IF NOT EXISTS proposal_events (
  rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL UNIQUE,
  proposal_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload_json TEXT,
  at_utc TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS pe_no_update BEFORE UPDATE ON proposal_events
  BEGIN SELECT RAISE(ABORT, 'append-only: proposal_events is immutable'); END;
CREATE TRIGGER IF NOT EXISTS pe_no_delete BEFORE DELETE ON proposal_events
  BEGIN SELECT RAISE(ABORT, 'append-only: proposal_events is immutable'); END;
"""


class AuditDB:
    def __init__(self, path=None):
        self.path = path or CFG.AUDIT_DB
        import os
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def record(self, event_type, proposal_id, payload=None):
        if event_type not in (CFG.PHASE_EVENTS + CFG.UPDATE_PHASE_EVENTS + CFG.SUBMISSION_EVENTS
                               + CFG.MANAGEMENT_EVENTS):
            raise ValueError(f"event_type {event_type} not permitted this phase")
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        seq = self.conn.execute("SELECT COUNT(*) FROM proposal_events").fetchone()[0]
        event_id = f"{proposal_id}:{event_type}:{seq}"
        self.conn.execute(
            "INSERT INTO proposal_events (event_id,proposal_id,event_type,payload_json,at_utc) "
            "VALUES (?,?,?,?,?)", (event_id, proposal_id, event_type,
                                   json.dumps(payload or {}, default=str), now))
        self.conn.commit()
        return event_id

    def events_for(self, proposal_id):
        return [dict(zip(("event_type", "at_utc", "payload_json"), r)) for r in self.conn.execute(
            "SELECT event_type, at_utc, payload_json FROM proposal_events WHERE proposal_id=? "
            "ORDER BY rowseq", (proposal_id,))]

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM proposal_events").fetchone()[0]

    def close(self):
        self.conn.close()
