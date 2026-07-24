"""
H1 — Hyperliquid observation database (hyperliquid_observation_v1.db).

A SEPARATE, ISOLATED append-only evidence store for public testnet market data. It is built
and tested with mock/replay data; it never reads from or writes to the gold / Telegram /
campaign stores. Every row is stamped with a fixed data_lineage so isolation is auditable:
this lineage must never appear in those other stores, and theirs must never appear here.

Integrity guarantees (all enforced + tested):
  * append-only: UPDATE/DELETE blocked at the SQLite engine level (triggers RAISE ABORT) AND
    no update/delete method is exposed.
  * secret/signing-named fields are rejected before persistence (secrets.safe_record).
  * the stored primary status is the deterministic classifier's verdict, never a caller label,
    so nothing can be persisted as admissible when it is not.
  * crossed / stale / empty / one-sided / out-of-order books are QUARANTINED — stored,
    flagged, never admissible.
  * both exchange and local-receipt timestamps are stored on every market observation.
  * deterministic: identical replay input -> identical logical dump + hash.
"""
from __future__ import annotations
import hashlib
import json
import os
import sqlite3

from . import OBSERVER_VERSION, DATA_LINEAGE
from .secrets import safe_record
from .observations import (BookSnapshot, TradeTick, ObsContext, classify_book,
                           classify_trade, BOOK_QUARANTINE)

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "data", "hyperliquid_observation_v1.db")

_SCHEMA = {
    "hl_connection_events": """
        CREATE TABLE IF NOT EXISTS hl_connection_events (
            rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
            connection_event_id TEXT NOT NULL, environment TEXT NOT NULL,
            endpoint TEXT, connection_state TEXT, reason_code TEXT,
            reconnect_count INTEGER, observed_at_utc TEXT,
            data_lineage TEXT NOT NULL, observer_version TEXT, event_hash TEXT NOT NULL)""",
    "hl_instrument_observations": """
        CREATE TABLE IF NOT EXISTS hl_instrument_observations (
            rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
            observation_id TEXT NOT NULL, environment TEXT NOT NULL,
            perp_name TEXT, asset_id INTEGER, sz_decimals INTEGER, max_leverage TEXT,
            verified INTEGER, universe_size INTEGER, observed_at_utc TEXT,
            data_lineage TEXT NOT NULL, observer_version TEXT, metadata_hash TEXT NOT NULL)""",
    "hl_book_observations": """
        CREATE TABLE IF NOT EXISTS hl_book_observations (
            rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
            observation_id TEXT NOT NULL, environment TEXT NOT NULL, coin TEXT,
            best_bid REAL, best_ask REAL, spread REAL, mid REAL,
            n_bids INTEGER, n_asks INTEGER,
            exch_time_ms INTEGER, local_recv_ms INTEGER,
            primary_status TEXT NOT NULL, duplicate_flag INTEGER, stale_flag INTEGER,
            out_of_order_flag INTEGER, quarantine_flag INTEGER,
            data_lineage TEXT NOT NULL, observer_version TEXT, obs_hash TEXT NOT NULL)""",
    "hl_trade_observations": """
        CREATE TABLE IF NOT EXISTS hl_trade_observations (
            rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
            observation_id TEXT NOT NULL, environment TEXT NOT NULL, coin TEXT,
            side TEXT, px REAL, sz REAL, tid TEXT, txhash TEXT,
            exch_time_ms INTEGER, local_recv_ms INTEGER,
            primary_status TEXT NOT NULL, duplicate_flag INTEGER, out_of_order_flag INTEGER,
            quarantine_flag INTEGER,
            data_lineage TEXT NOT NULL, observer_version TEXT, obs_hash TEXT NOT NULL)""",
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
    """Append-only. Exposes ONLY append_* writers + read helpers — no update/delete method."""

    def __init__(self, db_path=DEFAULT_DB_PATH):
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

    def _append(self, table, record: dict):
        safe = safe_record(record)             # raises SecretLeak on any secret/signing field
        cols = list(safe.keys())
        self.con.execute(
            f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
            [safe[c] for c in cols])
        self.con.commit()
        return safe

    # -- typed appenders -----------------------------------------------------
    def append_connection_event(self, *, environment, endpoint, connection_state, reason_code,
                                reconnect_count=0, observed_at_utc=None):
        if not environment:
            raise ValueError("environment is required on a connection event")
        rec = {"environment": environment, "endpoint": endpoint,
               "connection_state": connection_state, "reason_code": reason_code,
               "reconnect_count": reconnect_count, "observed_at_utc": observed_at_utc,
               "data_lineage": DATA_LINEAGE, "observer_version": OBSERVER_VERSION}
        rec["event_hash"] = _hash(rec)
        rec["connection_event_id"] = rec["event_hash"][:16]
        return self._append("hl_connection_events", rec)

    def append_instrument_observation(self, perp, *, environment, universe_size=None,
                                      observed_at_utc=None):
        if not environment:
            raise ValueError("environment is required on an instrument observation")
        rec = {"environment": environment, "perp_name": perp.name, "asset_id": perp.asset_id,
               "sz_decimals": perp.sz_decimals, "max_leverage": str(perp.max_leverage),
               "verified": int(bool(perp.verified)), "universe_size": universe_size,
               "observed_at_utc": observed_at_utc, "data_lineage": DATA_LINEAGE,
               "observer_version": OBSERVER_VERSION}
        rec["metadata_hash"] = _hash(rec)
        rec["observation_id"] = rec["metadata_hash"][:16]
        return self._append("hl_instrument_observations", rec)

    def append_book_observation(self, snap: BookSnapshot, *, environment,
                                ctx: ObsContext = None, prev: BookSnapshot = None):
        if not environment:
            raise ValueError("environment is required on a book observation")
        ctx = ctx or ObsContext(connected=True, env_verified_testnet=True, symbol_verified=True)
        status, flags, d = classify_book(snap, prev, ctx)   # STORED status = classifier verdict
        quarantine = status in BOOK_QUARANTINE
        assert not (status == "COMPLETE_ADMISSIBLE" and quarantine)
        rec = {"environment": environment, "coin": snap.coin,
               "best_bid": d["best_bid"] if _num(d["best_bid"]) else None,
               "best_ask": d["best_ask"] if _num(d["best_ask"]) else None,
               "spread": d["spread"], "mid": d["mid"], "n_bids": d["n_bids"], "n_asks": d["n_asks"],
               "exch_time_ms": _intornone(snap.exch_time_ms),
               "local_recv_ms": _intornone(snap.local_recv_ms),
               "primary_status": status, "duplicate_flag": int(flags["duplicate"]),
               "stale_flag": int(flags["stale"]), "out_of_order_flag": int(flags["out_of_order"]),
               "quarantine_flag": int(quarantine), "data_lineage": DATA_LINEAGE,
               "observer_version": OBSERVER_VERSION}
        rec["obs_hash"] = _hash(rec)
        rec["observation_id"] = rec["obs_hash"][:16]
        self._append("hl_book_observations", rec)
        return status

    def append_trade_observation(self, t: TradeTick, *, environment, ctx: ObsContext = None,
                                 seen_tids=None, last_trade_time_ms=None):
        if not environment:
            raise ValueError("environment is required on a trade observation")
        ctx = ctx or ObsContext(connected=True, env_verified_testnet=True, symbol_verified=True)
        status, flags = classify_trade(t, ctx, seen_tids, last_trade_time_ms)
        quarantine = status not in ("TRADE_ADMISSIBLE",)
        rec = {"environment": environment, "coin": t.coin, "side": str(t.side) if t.side else None,
               "px": float(t.px) if _num(t.px) else None, "sz": float(t.sz) if _num(t.sz) else None,
               "tid": str(t.tid) if t.tid is not None else None, "txhash": t.txhash,
               "exch_time_ms": _intornone(t.exch_time_ms),
               "local_recv_ms": _intornone(t.local_recv_ms),
               "primary_status": status, "duplicate_flag": int(flags["duplicate"]),
               "out_of_order_flag": int(flags["out_of_order"]), "quarantine_flag": int(quarantine),
               "data_lineage": DATA_LINEAGE, "observer_version": OBSERVER_VERSION}
        rec["obs_hash"] = _hash(rec)
        rec["observation_id"] = rec["obs_hash"][:16]
        self._append("hl_trade_observations", rec)
        return status

    # -- read helpers (no mutation) -----------------------------------------
    def table_names(self):
        rows = self.con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return sorted(r[0] for r in rows if r[0] != "sqlite_sequence")

    def count(self, table):
        return self.con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def lineages(self):
        """Distinct data_lineage values present across all tables (isolation audit)."""
        seen = set()
        for t in TABLES:
            for (lin,) in self.con.execute(f"SELECT DISTINCT data_lineage FROM {t}").fetchall():
                seen.add(lin)
        return sorted(seen)

    def logical_dump(self):
        out = {}
        for t in TABLES:
            cur = self.con.execute(f"SELECT * FROM {t} ORDER BY rowseq")
            names = [c[0] for c in cur.description]
            out[t] = [{n: v for n, v in zip(names, r) if n != "rowseq"} for r in cur.fetchall()]
        return out

    def logical_hash(self):
        return hashlib.sha256(
            json.dumps(self.logical_dump(), sort_keys=True, default=str).encode("utf-8")).hexdigest()

    def close(self):
        self.con.close()


def _intornone(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None
