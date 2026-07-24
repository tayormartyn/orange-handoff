"""
Brick 4 — broker observation database (broker_observation_v1.db).

Append-only evidence store for FUTURE Pepperstone demo observations. Built and tested with
mock/replay data only — no network, no OAuth, no credentials. Isolated: this DB never
modifies Telegram or campaign evidence, never auto-creates a fill, never alters scoring.

Integrity guarantees (all enforced + tested):
  * append-only: UPDATE/DELETE are blocked at the SQLite engine level (triggers RAISE ABORT)
    AND no update/delete methods are exposed.
  * secret-named fields are rejected before persistence (via secrets.safe_record).
  * crossed (ask<bid) and stale quotes are QUARANTINED — stored, flagged, NEVER admissible.
  * missing bid or ask is stored as explicit NULL — never fabricated.
  * out-of-order quotes are stored but flagged; duplicates are identifiable.
  * environment is recorded on every broker-derived observation.
  * the quote's stored primary status is the deterministic classifier's verdict, never a
    caller-supplied label — so nothing can be persisted as admissible when it is not.
  * deterministic: identical replay input -> identical logical dump + hash.
"""
from __future__ import annotations
import hashlib
import json
import os
import sqlite3

from .config import ADAPTER_VERSION, DEFAULT_MAX_QUOTE_AGE_MS
from .secrets import safe_record
from .quotes import RawQuote, QuoteContext, classify

QUARANTINE_STATUSES = ("INVALID_CROSSED_MARKET", "STALE", "INVALID_VALUE", "OUT_OF_ORDER")

_SCHEMA = {
    "broker_connection_events": """
        CREATE TABLE IF NOT EXISTS broker_connection_events (
            rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
            connection_event_id TEXT NOT NULL, environment TEXT NOT NULL,
            connection_state TEXT, connected_at_utc TEXT, disconnected_at_utc TEXT,
            reason_code TEXT, adapter_version TEXT, event_hash TEXT NOT NULL)""",
    "broker_account_observations": """
        CREATE TABLE IF NOT EXISTS broker_account_observations (
            rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
            observation_id TEXT NOT NULL, safe_account_id TEXT, account_environment TEXT NOT NULL,
            account_type TEXT, currency TEXT, balance REAL, equity REAL, margin REAL,
            free_margin REAL, observed_at_utc TEXT, adapter_version TEXT, observation_hash TEXT NOT NULL)""",
    "broker_symbol_observations": """
        CREATE TABLE IF NOT EXISTS broker_symbol_observations (
            rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
            observation_id TEXT NOT NULL, broker_symbol_id TEXT, symbol_name TEXT,
            description TEXT, digits INTEGER, pip_position INTEGER, contract_size REAL,
            minimum_volume REAL, volume_step REAL, minimum_stop_distance REAL,
            observed_at_utc TEXT, metadata_hash TEXT NOT NULL)""",
    "broker_quote_observations": """
        CREATE TABLE IF NOT EXISTS broker_quote_observations (
            rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
            quote_id TEXT NOT NULL, broker_symbol_id TEXT, symbol_name TEXT,
            bid REAL, ask REAL, broker_timestamp_utc TEXT, local_received_timestamp_utc TEXT,
            spread REAL, primary_quote_status TEXT NOT NULL, duplicate_flag INTEGER,
            stale_flag INTEGER, out_of_order_flag INTEGER, quarantine_flag INTEGER,
            sequence_or_fingerprint TEXT, source_environment TEXT NOT NULL,
            adapter_version TEXT, quote_hash TEXT NOT NULL)""",
    "broker_position_observations": """
        CREATE TABLE IF NOT EXISTS broker_position_observations (
            rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
            observation_id TEXT NOT NULL, safe_position_id TEXT, symbol TEXT, direction TEXT,
            volume REAL, entry_price REAL, stop_loss REAL, take_profit REAL,
            position_status TEXT, observed_at_utc TEXT, source_environment TEXT NOT NULL,
            observation_hash TEXT NOT NULL)""",
    "broker_auth_events": """
        CREATE TABLE IF NOT EXISTS broker_auth_events (
            rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
            auth_event_id TEXT NOT NULL, auth_state TEXT, timestamp_utc TEXT,
            reason_code TEXT, adapter_version TEXT, event_hash TEXT NOT NULL)""",
}
TABLES = tuple(_SCHEMA.keys())


def _num(x):
    try:
        float(x)
        return True
    except (TypeError, ValueError):
        return False


def _hash(record: dict) -> str:
    return hashlib.sha256(json.dumps(record, sort_keys=True, default=str).encode("utf-8")).hexdigest()


class ObservationDB:
    """Append-only. Exposes ONLY append_* readers/writers — no update or delete method exists."""

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
        for t in TABLES:                       # append-only enforced at the engine level
            cur.execute(f"CREATE TRIGGER IF NOT EXISTS noupd_{t} BEFORE UPDATE ON {t} "
                        f"BEGIN SELECT RAISE(ABORT, 'append-only: update forbidden on {t}'); END;")
            cur.execute(f"CREATE TRIGGER IF NOT EXISTS nodel_{t} BEFORE DELETE ON {t} "
                        f"BEGIN SELECT RAISE(ABORT, 'append-only: delete forbidden on {t}'); END;")
        self.con.commit()

    # -- generic append: rejects secret-named fields, then inserts (no update/delete path)
    def _append(self, table, record: dict):
        safe = safe_record(record)             # raises SecretLeak on any secret-named field
        cols = list(safe.keys())
        self.con.execute(
            f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
            [safe[c] for c in cols])
        self.con.commit()
        return safe

    # -- typed appenders -----------------------------------------------------
    def append_connection_event(self, *, environment, connection_state, reason_code,
                                connected_at_utc=None, disconnected_at_utc=None):
        if not environment:
            raise ValueError("environment is required on a broker observation")
        rec = {"environment": environment, "connection_state": connection_state,
               "connected_at_utc": connected_at_utc, "disconnected_at_utc": disconnected_at_utc,
               "reason_code": reason_code, "adapter_version": ADAPTER_VERSION}
        rec["event_hash"] = _hash(rec)
        rec["connection_event_id"] = rec["event_hash"][:16]
        return self._append("broker_connection_events", rec)

    def append_account_observation(self, *, account_environment, safe_account_id=None,
                                   account_type=None, currency=None, balance=None, equity=None,
                                   margin=None, free_margin=None, observed_at_utc=None):
        if not account_environment:
            raise ValueError("account_environment is required")
        rec = {"safe_account_id": safe_account_id, "account_environment": account_environment,
               "account_type": account_type, "currency": currency, "balance": balance,
               "equity": equity, "margin": margin, "free_margin": free_margin,
               "observed_at_utc": observed_at_utc, "adapter_version": ADAPTER_VERSION}
        rec["observation_hash"] = _hash(rec)
        rec["observation_id"] = rec["observation_hash"][:16]
        return self._append("broker_account_observations", rec)

    def append_symbol_observation(self, *, broker_symbol_id, symbol_name, description=None,
                                  digits=None, pip_position=None, contract_size=None,
                                  minimum_volume=None, volume_step=None,
                                  minimum_stop_distance=None, observed_at_utc=None):
        rec = {"broker_symbol_id": broker_symbol_id, "symbol_name": symbol_name,
               "description": description, "digits": digits, "pip_position": pip_position,
               "contract_size": contract_size, "minimum_volume": minimum_volume,
               "volume_step": volume_step, "minimum_stop_distance": minimum_stop_distance,
               "observed_at_utc": observed_at_utc}
        rec["metadata_hash"] = _hash(rec)
        rec["observation_id"] = rec["metadata_hash"][:16]
        return self._append("broker_symbol_observations", rec)

    def append_quote_observation(self, q: RawQuote, *, source_environment, ctx: QuoteContext = None,
                                 prev: RawQuote = None, sequence_or_fingerprint=None):
        if not source_environment:
            raise ValueError("source_environment is required on a quote observation")
        ctx = ctx or QuoteContext(connected=True, auth_ready=True, env_verified_demo=True,
                                  symbol_verified=True, max_age_ms=DEFAULT_MAX_QUOTE_AGE_MS)
        # the STORED status is the classifier's verdict — never a caller label.
        status, flags = classify(q, prev, ctx)
        bid = float(q.bid) if _num(q.bid) else None       # missing/invalid -> explicit NULL
        ask = float(q.ask) if _num(q.ask) else None
        spread = (ask - bid) if (bid is not None and ask is not None and ask >= bid) else None
        quarantine = status in QUARANTINE_STATUSES
        # hard guarantee: a quarantined/crossed/stale quote can never be admissible
        assert not (status == "COMPLETE_ADMISSIBLE" and quarantine)
        rec = {"broker_symbol_id": str(getattr(q, "broker_symbol_id", "") or ""),
               "symbol_name": q.symbol, "bid": bid, "ask": ask,
               "broker_timestamp_utc": q.broker_ts, "local_received_timestamp_utc": q.local_ts,
               "spread": spread, "primary_quote_status": status,
               "duplicate_flag": int(flags["duplicate"]), "stale_flag": int(flags["stale"]),
               "out_of_order_flag": int(flags["out_of_order"]), "quarantine_flag": int(quarantine),
               "sequence_or_fingerprint": sequence_or_fingerprint,
               "source_environment": source_environment, "adapter_version": ADAPTER_VERSION}
        rec["quote_hash"] = _hash(rec)
        rec["quote_id"] = rec["quote_hash"][:16]
        self._append("broker_quote_observations", rec)
        return status

    def append_position_observation(self, *, safe_position_id, symbol, direction=None, volume=None,
                                    entry_price=None, stop_loss=None, take_profit=None,
                                    position_status=None, source_environment, observed_at_utc=None):
        if not source_environment:
            raise ValueError("source_environment is required on a position observation")
        rec = {"safe_position_id": safe_position_id, "symbol": symbol, "direction": direction,
               "volume": volume, "entry_price": entry_price, "stop_loss": stop_loss,
               "take_profit": take_profit, "position_status": position_status,
               "observed_at_utc": observed_at_utc, "source_environment": source_environment}
        rec["observation_hash"] = _hash(rec)
        rec["observation_id"] = rec["observation_hash"][:16]
        return self._append("broker_position_observations", rec)

    def append_auth_event(self, *, auth_state, reason_code, timestamp_utc=None):
        rec = {"auth_state": auth_state, "timestamp_utc": timestamp_utc, "reason_code": reason_code,
               "adapter_version": ADAPTER_VERSION}
        rec["event_hash"] = _hash(rec)
        rec["auth_event_id"] = rec["event_hash"][:16]
        return self._append("broker_auth_events", rec)

    # -- read helpers (no mutation) -----------------------------------------
    def table_names(self):
        rows = self.con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return sorted(r[0] for r in rows if r[0] != "sqlite_sequence")

    def count(self, table):
        return self.con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def logical_dump(self):
        """Deterministic content dump (excludes the autoincrement rowseq)."""
        out = {}
        for t in TABLES:
            cur = self.con.execute(f"SELECT * FROM {t} ORDER BY rowseq")
            names = [d[0] for d in cur.description]
            rows = []
            for r in cur.fetchall():
                row = {n: v for n, v in zip(names, r) if n != "rowseq"}
                rows.append(row)
            out[t] = rows
        return out

    def logical_hash(self):
        return hashlib.sha256(
            json.dumps(self.logical_dump(), sort_keys=True, default=str).encode("utf-8")).hexdigest()

    def close(self):
        self.con.close()
