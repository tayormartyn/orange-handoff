"""
Append-only isolated evidence store for Q1 XAUUSD quotes: data/ctrader_quotes_v1.db.

Two tables kept SEPARATE: raw_spot_events (verbatim) and normalised_quotes (derived). Immutable
by construction — BEFORE UPDATE/DELETE triggers RAISE(ABORT) and there are NO update/delete
methods. Idempotent inserts via UNIQUE(connection_session_id, event_sequence) + INSERT OR IGNORE.
Writes ONLY here — never to the Telegram archive, campaign DB, shadow results, or baselines.
"""
from __future__ import annotations
import os
import sqlite3
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
DEFAULT_DB = os.path.join(PROJECT_ROOT, "data", "ctrader_quotes_v1.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_spot_events (
  rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
  connection_session_id TEXT NOT NULL,
  event_sequence INTEGER NOT NULL,
  payload_type INTEGER,
  masked_account_id TEXT,
  symbol_id INTEGER,
  raw_bid INTEGER,
  raw_ask INTEGER,
  broker_timestamp INTEGER,
  local_received_utc TEXT,
  local_received_monotonic_ns INTEGER,
  persisted_utc TEXT,
  UNIQUE(connection_session_id, event_sequence)
);
CREATE TABLE IF NOT EXISTS normalised_quotes (
  rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
  connection_session_id TEXT NOT NULL,
  event_sequence INTEGER NOT NULL,
  raw_bid INTEGER,
  raw_ask INTEGER,
  norm_bid REAL,
  norm_ask REAL,
  latest_bid REAL,
  latest_ask REAL,
  bid_provenance_session TEXT,
  bid_provenance_seq INTEGER,
  ask_provenance_session TEXT,
  ask_provenance_seq INTEGER,
  spread REAL,
  flags TEXT,
  persisted_utc TEXT,
  UNIQUE(connection_session_id, event_sequence)
);
CREATE TRIGGER IF NOT EXISTS raw_no_update BEFORE UPDATE ON raw_spot_events
  BEGIN SELECT RAISE(ABORT, 'append-only: raw_spot_events is immutable'); END;
CREATE TRIGGER IF NOT EXISTS raw_no_delete BEFORE DELETE ON raw_spot_events
  BEGIN SELECT RAISE(ABORT, 'append-only: raw_spot_events is immutable'); END;
CREATE TRIGGER IF NOT EXISTS norm_no_update BEFORE UPDATE ON normalised_quotes
  BEGIN SELECT RAISE(ABORT, 'append-only: normalised_quotes is immutable'); END;
CREATE TRIGGER IF NOT EXISTS norm_no_delete BEFORE DELETE ON normalised_quotes
  BEGIN SELECT RAISE(ABORT, 'append-only: normalised_quotes is immutable'); END;
"""

_RAW_COLS = ("connection_session_id", "event_sequence", "payload_type", "masked_account_id",
             "symbol_id", "raw_bid", "raw_ask", "broker_timestamp", "local_received_utc",
             "local_received_monotonic_ns")
_NORM_COLS = ("connection_session_id", "event_sequence", "raw_bid", "raw_ask", "norm_bid",
              "norm_ask", "latest_bid", "latest_ask", "bid_provenance_session",
              "bid_provenance_seq", "ask_provenance_session", "ask_provenance_seq", "spread",
              "flags")


def _now_utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class QuoteDB:
    def __init__(self, path=None):
        self.path = path or DEFAULT_DB
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def insert_raw(self, **fields):
        """Append one raw spot event. Idempotent on (session, sequence). Returns True if inserted."""
        row = {c: fields.get(c) for c in _RAW_COLS}
        row["persisted_utc"] = _now_utc()
        cols = list(row.keys())
        sql = (f"INSERT OR IGNORE INTO raw_spot_events ({','.join(cols)}) "
               f"VALUES ({','.join('?' for _ in cols)})")
        cur = self.conn.execute(sql, [row[c] for c in cols])
        self.conn.commit()
        return cur.rowcount > 0

    def insert_normalised(self, **fields):
        """Append one normalised quote. Idempotent on (session, sequence). Returns True if inserted."""
        row = {c: fields.get(c) for c in _NORM_COLS}
        row["persisted_utc"] = _now_utc()
        cols = list(row.keys())
        sql = (f"INSERT OR IGNORE INTO normalised_quotes ({','.join(cols)}) "
               f"VALUES ({','.join('?' for _ in cols)})")
        cur = self.conn.execute(sql, [row[c] for c in cols])
        self.conn.commit()
        return cur.rowcount > 0

    def count_raw(self):
        return self.conn.execute("SELECT COUNT(*) FROM raw_spot_events").fetchone()[0]

    def count_normalised(self):
        return self.conn.execute("SELECT COUNT(*) FROM normalised_quotes").fetchone()[0]

    def fetch_normalised(self, session_id, seq):
        cur = self.conn.execute(
            "SELECT * FROM normalised_quotes WHERE connection_session_id=? AND event_sequence=?",
            (session_id, seq))
        cols = [d[0] for d in cur.description]
        r = cur.fetchone()
        return dict(zip(cols, r)) if r else None

    def close(self):
        self.conn.close()
