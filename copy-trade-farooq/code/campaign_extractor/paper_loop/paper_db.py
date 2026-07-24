"""
Append-only PAPER observation store: data/paper_observations_v1.db. UPDATE/DELETE prohibited
(RAISE(ABORT) triggers + no update/delete methods); corrections create SUPERSEDING rows. Stores
quote-side evidence (bid/ask/side) only — there are NO P/L/R/outcome fields, and provider-displayed
screenshot P/L is structurally rejected from any outcome path. Every row is OBSERVATION_ONLY /
PAPER_ONLY / NOT_A_FILL / NOT_AN_OUTCOME.
"""
from __future__ import annotations
import json
import os
import sqlite3
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB = os.path.join(_ROOT, "data", "paper_observations_v1.db")


class PaperOutcomeFirewallError(Exception):
    pass


def reject_provider_pnl_from_outcome(evidence_domain):
    """Guard: provider-displayed evidence can never feed a paper outcome/R field."""
    if evidence_domain == "PROVIDER_DISPLAYED":
        raise PaperOutcomeFirewallError("PROVIDER_DISPLAYED P/L rejected from all paper outcome/R fields")
    return True


_SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_observations (
  rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
  observation_id TEXT NOT NULL UNIQUE,
  unified_signal_hash TEXT, unified_signal_json TEXT,
  provider_id TEXT NOT NULL, source_message_id TEXT,
  decision_timestamp TEXT, status TEXT NOT NULL, reason_code TEXT,
  delivery_result_json TEXT, actionable_result_json TEXT,
  quote_session_id TEXT, quote_event_id TEXT,
  bid TEXT, ask TEXT, executable_side TEXT, quote_timestamp TEXT, freshness_json TEXT,
  entry_low TEXT, entry_high TEXT, q4a_config_version TEXT,
  evidence_references TEXT, reviewer_reference TEXT,
  supersedes_observation_id TEXT,
  observation_only INTEGER NOT NULL DEFAULT 1, paper_only INTEGER NOT NULL DEFAULT 1,
  not_a_fill INTEGER NOT NULL DEFAULT 1, not_an_outcome INTEGER NOT NULL DEFAULT 1,
  persisted_utc TEXT);
CREATE TRIGGER IF NOT EXISTS paper_no_update BEFORE UPDATE ON paper_observations
  BEGIN SELECT RAISE(ABORT, 'append-only: paper_observations UPDATE prohibited'); END;
CREATE TRIGGER IF NOT EXISTS paper_no_delete BEFORE DELETE ON paper_observations
  BEGIN SELECT RAISE(ABORT, 'append-only: paper_observations DELETE prohibited'); END;
"""

_COLS = ("observation_id", "unified_signal_hash", "unified_signal_json", "provider_id",
         "source_message_id", "decision_timestamp", "status", "reason_code",
         "delivery_result_json", "actionable_result_json", "quote_session_id", "quote_event_id",
         "bid", "ask", "executable_side", "quote_timestamp", "freshness_json", "entry_low",
         "entry_high", "q4a_config_version", "evidence_references", "reviewer_reference",
         "supersedes_observation_id")


class PaperDB:
    def __init__(self, path=None):
        self.path = path or DEFAULT_DB
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def record(self, decision, *, observation_id, provider_id, reviewer_reference=None,
               quote_session_id=None, quote_event_id=None, supersedes_observation_id=None):
        from unified_signal import snapshot_hash
        u = decision.get("unified", {})
        act = decision.get("actionable") or {}
        row = {c: None for c in _COLS}
        row.update(observation_id=observation_id, provider_id=provider_id,
                   unified_signal_hash=snapshot_hash(u) if u else None,
                   unified_signal_json=json.dumps(u, default=str),
                   source_message_id=u.get("source_message_id"),
                   decision_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   status=decision["status"], reason_code=decision.get("reason"),
                   delivery_result_json=json.dumps(decision.get("delivery"), default=str),
                   actionable_result_json=json.dumps(decision.get("actionable"), default=str),
                   quote_session_id=quote_session_id or act.get("session"),
                   quote_event_id=str(act.get("matched_seq")) if act.get("matched_seq") else quote_event_id,
                   bid=act.get("bid"), ask=act.get("ask"), executable_side=act.get("executable_side"),
                   quote_timestamp=str(act.get("first_quote_after_anchor_wall_ms") or ""),
                   freshness_json=json.dumps({k: act.get(k) for k in
                       ("bid_source_age_ms", "ask_source_age_ms", "surrounding_coverage_gap_ms",
                        "post_anchor_delay_ms")}),
                   entry_low=str(u.get("entry_low")), entry_high=str(u.get("entry_high")),
                   q4a_config_version=decision.get("q4a_config_version"),
                   evidence_references=json.dumps(u.get("source_evidence_references"), default=str),
                   reviewer_reference=reviewer_reference or u.get("reviewer_reference"),
                   supersedes_observation_id=supersedes_observation_id)
        cols = list(_COLS) + ["persisted_utc"]
        vals = [row[c] for c in _COLS] + [time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())]
        self.conn.execute(f"INSERT INTO paper_observations ({','.join(cols)}) VALUES "
                          f"({','.join('?' for _ in cols)})", vals)
        self.conn.commit()
        return observation_id

    def by_provider(self, provider_id):
        return self.conn.execute("SELECT observation_id FROM paper_observations WHERE provider_id=?",
                                 (provider_id,)).fetchall()

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM paper_observations").fetchone()[0]

    def close(self):
        self.conn.close()
