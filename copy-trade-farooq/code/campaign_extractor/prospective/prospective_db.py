"""
Brick 5 — prospective Telegram evidence database (prospective_evidence_v1.db).

Append-only, observational. Records future Telegram messages + candidate campaign events
WITHOUT inferring fills, entries, exits, R, or win/loss — there are deliberately NO columns
for any of those. Broker quote fields stay NULL with BROKER_NOT_CONNECTED until a broker is
separately connected. Built/tested with offline fixtures only.

Append-only is enforced at the SQLite engine level (UPDATE/DELETE triggers RAISE ABORT) and
no update/delete method is exposed. Secret-named fields are rejected before persistence.
"""
from __future__ import annotations
import hashlib
import json
import os
import sqlite3

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
_sys.path.insert(0, os.path.dirname(_HERE))          # campaign_extractor on path
from broker_readonly.secrets import safe_record       # shared secret guard

_SCHEMA = {
    "prospective_message_evidence": """
        CREATE TABLE IF NOT EXISTS prospective_message_evidence (
            rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
            evidence_id TEXT NOT NULL, telegram_channel_id TEXT, telegram_message_id TEXT,
            telegram_posted_at_utc TEXT, listener_received_at_utc TEXT,
            raw_text TEXT, raw_text_hash TEXT,
            media_reference_or_hash TEXT, parser_started_at_utc TEXT, parser_completed_at_utc TEXT,
            listener_latency_ms REAL, parser_latency_ms REAL, extractor_version TEXT,
            message_event_type TEXT, message_revision_number INTEGER, supersedes_evidence_id TEXT,
            telegram_edited_at_utc TEXT, listener_observed_at_utc TEXT,
            telegram_sender_id TEXT, telegram_sender_username TEXT, telegram_sender_display TEXT,
            telegram_is_forwarded INTEGER, telegram_fwd_origin TEXT,
            evidence_hash TEXT NOT NULL)""",
    "prospective_candidate_events": """
        CREATE TABLE IF NOT EXISTS prospective_candidate_events (
            rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_event_id TEXT NOT NULL, telegram_message_id TEXT, proposed_event_type TEXT,
            asset TEXT, direction TEXT, proposed_campaign_id TEXT, proposed_leg_id TEXT,
            association_status TEXT, exact_supporting_text TEXT, supporting_media_fact_id TEXT,
            extraction_confidence REAL, validator_status TEXT, rejection_reason TEXT,
            extractor_version TEXT, validator_version TEXT, candidate_hash TEXT NOT NULL)""",
    "prospective_campaign_links": """
        CREATE TABLE IF NOT EXISTS prospective_campaign_links (
            rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id TEXT NOT NULL, candidate_event_id TEXT, campaign_id TEXT, leg_id TEXT,
            association_status TEXT, association_method TEXT, supporting_message_ids TEXT,
            created_at_utc TEXT, link_hash TEXT NOT NULL)""",
    "prospective_quote_context": """
        CREATE TABLE IF NOT EXISTS prospective_quote_context (
            rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
            context_id TEXT NOT NULL, telegram_message_id TEXT, broker_symbol_id TEXT,
            quote_before_message_id TEXT, first_quote_after_message_id TEXT, nearest_quote_id TEXT,
            quote_age_ms REAL, bid REAL, ask REAL, broker_timestamp_utc TEXT,
            local_received_timestamp_utc TEXT, quote_status TEXT, context_status TEXT,
            context_hash TEXT NOT NULL)""",
}
TABLES = tuple(_SCHEMA.keys())

# columns that must NEVER exist here — the recorder cannot infer outcomes
FORBIDDEN_OUTCOME_TOKENS = ("realized_r", "realised_r", "_r_", "fill", "pnl", "win", "loss",
                            "score", "exit_price", "profit")


def _hash(record: dict) -> str:
    return hashlib.sha256(json.dumps(record, sort_keys=True, default=str).encode("utf-8")).hexdigest()


class ProspectiveDB:
    def __init__(self, db_path):
        self.db_path = db_path
        if db_path != ":memory:":
            d = os.path.dirname(db_path)
            if d:
                os.makedirs(d, exist_ok=True)
        self.con = sqlite3.connect(db_path)
        self._create()

    def _create(self):
        cur = self.con.cursor()
        for ddl in _SCHEMA.values():
            cur.execute(ddl)
        # additive migration: sender columns for existing DBs (append-only-safe; old rows -> NULL)
        have = {r[1] for r in cur.execute("PRAGMA table_info(prospective_message_evidence)")}
        for col in ("telegram_sender_id", "telegram_sender_username", "telegram_sender_display",
                    "telegram_fwd_origin"):
            if col not in have:
                cur.execute(f"ALTER TABLE prospective_message_evidence ADD COLUMN {col} TEXT")
        if "telegram_is_forwarded" not in have:
            cur.execute("ALTER TABLE prospective_message_evidence ADD COLUMN telegram_is_forwarded INTEGER")
        for t in TABLES:
            cur.execute(f"CREATE TRIGGER IF NOT EXISTS noupd_{t} BEFORE UPDATE ON {t} "
                        f"BEGIN SELECT RAISE(ABORT, 'append-only: update forbidden on {t}'); END;")
            cur.execute(f"CREATE TRIGGER IF NOT EXISTS nodel_{t} BEFORE DELETE ON {t} "
                        f"BEGIN SELECT RAISE(ABORT, 'append-only: delete forbidden on {t}'); END;")
        self.con.commit()

    def _append(self, table, record: dict):
        safe = safe_record(record)              # raises SecretLeak on any secret-named field
        cols = list(safe.keys())
        self.con.execute(
            f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
            [safe[c] for c in cols])
        self.con.commit()
        return safe

    # -- appenders ----------------------------------------------------------
    def append_message_evidence(self, *, telegram_channel_id, telegram_message_id,
                                telegram_posted_at_utc, listener_received_at_utc, raw_text,
                                media_reference_or_hash=None, parser_started_at_utc=None,
                                parser_completed_at_utc=None, listener_latency_ms=None,
                                parser_latency_ms=None, extractor_version=None,
                                message_event_type="CREATED", message_revision_number=1,
                                supersedes_evidence_id=None, telegram_edited_at_utc=None,
                                listener_observed_at_utc=None, telegram_sender_id=None,
                                telegram_sender_username=None, telegram_sender_display=None,
                                telegram_is_forwarded=None, telegram_fwd_origin=None):
        """Append-only raw message evidence.

        raw_text stores the EXACT Unicode message text/caption (recoverable); it is message
        CONTENT, not a credential (its column name is not secret-marked). raw_text_hash is:
          * SHA-256 over the EXACT stored raw_text encoded as UTF-8,
          * with NO trimming / case-folding / Unicode normalisation,
          * and NULL when raw_text is NULL (media-only) — so NULL and "" stay DISTINCT
            states (NULL -> hash NULL; "" -> sha256 of the empty string).
        Edits are NEW append-only revisions (message_event_type=EDITED, incremented
        message_revision_number, supersedes_evidence_id -> prior row); originals are never
        overwritten. Deletion capture is NOT implemented (see module limitations)."""
        raw_text_hash = (hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
                         if raw_text is not None else None)
        rec = {"telegram_channel_id": telegram_channel_id, "telegram_message_id": telegram_message_id,
               "telegram_posted_at_utc": telegram_posted_at_utc,
               "listener_received_at_utc": listener_received_at_utc,
               "raw_text": raw_text, "raw_text_hash": raw_text_hash,
               "media_reference_or_hash": media_reference_or_hash,
               "parser_started_at_utc": parser_started_at_utc,
               "parser_completed_at_utc": parser_completed_at_utc,
               "listener_latency_ms": listener_latency_ms, "parser_latency_ms": parser_latency_ms,
               "extractor_version": extractor_version,
               "message_event_type": message_event_type,
               "message_revision_number": message_revision_number,
               "supersedes_evidence_id": supersedes_evidence_id,
               "telegram_edited_at_utc": telegram_edited_at_utc,
               "listener_observed_at_utc": listener_observed_at_utc,
               "telegram_sender_id": telegram_sender_id,
               "telegram_sender_username": telegram_sender_username,
               "telegram_sender_display": telegram_sender_display,
               "telegram_is_forwarded": telegram_is_forwarded,
               "telegram_fwd_origin": telegram_fwd_origin}
        rec["evidence_hash"] = _hash(rec)
        rec["evidence_id"] = rec["evidence_hash"][:16]
        return self._append("prospective_message_evidence", rec)

    def append_candidate_event(self, *, telegram_message_id, proposed_event_type, asset=None,
                               direction=None, proposed_campaign_id=None, proposed_leg_id=None,
                               association_status=None, exact_supporting_text=None,
                               supporting_media_fact_id=None, extraction_confidence=None,
                               validator_status=None, rejection_reason=None, extractor_version=None,
                               validator_version=None):
        rec = {"telegram_message_id": telegram_message_id, "proposed_event_type": proposed_event_type,
               "asset": asset, "direction": direction, "proposed_campaign_id": proposed_campaign_id,
               "proposed_leg_id": proposed_leg_id, "association_status": association_status,
               "exact_supporting_text": exact_supporting_text,
               "supporting_media_fact_id": supporting_media_fact_id,
               "extraction_confidence": extraction_confidence, "validator_status": validator_status,
               "rejection_reason": rejection_reason, "extractor_version": extractor_version,
               "validator_version": validator_version}
        rec["candidate_hash"] = _hash(rec)
        rec["candidate_event_id"] = rec["candidate_hash"][:16]
        return self._append("prospective_candidate_events", rec)

    def append_campaign_link(self, *, candidate_event_id, campaign_id, leg_id, association_status,
                             association_method, supporting_message_ids, created_at_utc=None):
        rec = {"candidate_event_id": candidate_event_id, "campaign_id": campaign_id, "leg_id": leg_id,
               "association_status": association_status, "association_method": association_method,
               "supporting_message_ids": json.dumps(supporting_message_ids, sort_keys=True)
               if not isinstance(supporting_message_ids, str) else supporting_message_ids,
               "created_at_utc": created_at_utc}
        rec["link_hash"] = _hash(rec)
        rec["link_id"] = rec["link_hash"][:16]
        return self._append("prospective_campaign_links", rec)

    def append_quote_context(self, *, telegram_message_id, context_status, broker_symbol_id=None,
                             quote_before_message_id=None, first_quote_after_message_id=None,
                             nearest_quote_id=None, quote_age_ms=None, bid=None, ask=None,
                             broker_timestamp_utc=None, local_received_timestamp_utc=None,
                             quote_status=None):
        # broker not connected in this phase -> price fields MUST be NULL; never fabricated.
        if context_status not in ("BROKER_NOT_CONNECTED", "AUTH_NOT_AVAILABLE"):
            raise ValueError("quote context must be BROKER_NOT_CONNECTED / AUTH_NOT_AVAILABLE "
                             "until a broker is connected")
        if any(v is not None for v in (bid, ask, broker_timestamp_utc, local_received_timestamp_utc)):
            raise ValueError("broker quote fields must be NULL while broker is not connected")
        rec = {"telegram_message_id": telegram_message_id, "broker_symbol_id": broker_symbol_id,
               "quote_before_message_id": quote_before_message_id,
               "first_quote_after_message_id": first_quote_after_message_id,
               "nearest_quote_id": nearest_quote_id, "quote_age_ms": quote_age_ms,
               "bid": None, "ask": None, "broker_timestamp_utc": None,
               "local_received_timestamp_utc": None,
               "quote_status": quote_status or context_status, "context_status": context_status}
        rec["context_hash"] = _hash(rec)
        rec["context_id"] = rec["context_hash"][:16]
        return self._append("prospective_quote_context", rec)

    # -- read helpers -------------------------------------------------------
    def table_names(self):
        rows = self.con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return sorted(r[0] for r in rows if r[0] != "sqlite_sequence")

    def column_names(self, table):
        return [r[1] for r in self.con.execute(f"PRAGMA table_info({table})").fetchall()]

    def count(self, table):
        return self.con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def logical_dump(self):
        out = {}
        for t in TABLES:
            cur = self.con.execute(f"SELECT * FROM {t} ORDER BY rowseq")
            names = [d[0] for d in cur.description]
            out[t] = [{n: v for n, v in zip(names, r) if n != "rowseq"} for r in cur.fetchall()]
        return out

    def logical_hash(self):
        return hashlib.sha256(
            json.dumps(self.logical_dump(), sort_keys=True, default=str).encode("utf-8")).hexdigest()

    def close(self):
        self.con.close()
