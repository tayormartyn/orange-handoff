"""
shadow_db.py — SHADOW MODE Phase 1b storage (a SEPARATE database, on purpose).

JUDGMENT CALL (flagged): the shadow results live in their OWN database,
`data/shadow.db`, NOT inside the signed-off `signal_archive.db`. Reasons:
  * the archive is the immutable SOURCE OF TRUTH (signed-off evidence); shadow
    output is DERIVED and fully rebuildable, so it must not risk the archive's
    integrity-check or schema version;
  * every shadow row references a `signal_id` from the archive and the immutable
    Phase 1a price files + a frozen config hash, so the lineage is explicit;
  * dropping/rebuilding shadow results is then a one-file operation that can never
    touch the archive.

Four tables, append-only:
  shadow_configs          one row per frozen config version (the assumption set + hash)
  shadow_runs             one row per execution of the shadow calc
  shadow_results          one row per (signal, scenario) within a run
  shadow_gate_evaluations one row per GO/NO-GO style gate evaluated in a run

PAPER mode. Read-only to the archive; writes only to its own file.
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone

DATA_DIR = "data"
SHADOW_DB_PATH = os.path.join(DATA_DIR, "shadow.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS shadow_configs (
    config_version   TEXT PRIMARY KEY,
    config_hash      TEXT NOT NULL,
    config_json      TEXT NOT NULL,
    frozen_at_utc    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS shadow_runs (
    run_id              TEXT PRIMARY KEY,
    started_at_utc      TEXT NOT NULL,
    completed_at_utc    TEXT,
    config_version      TEXT NOT NULL REFERENCES shadow_configs(config_version),
    config_hash         TEXT NOT NULL,
    archive_db_path     TEXT NOT NULL,
    price_source        TEXT NOT NULL,        -- e.g. "dukascopy-xauusd / phase1a-cache"
    code_version        TEXT NOT NULL,
    signals_total       INTEGER,
    signals_priced      INTEGER,
    status              TEXT NOT NULL,
    notes               TEXT
);

-- One row per (signal, scenario). A "scenario" for Ledger C is a (delay, slippage)
-- pair; Ledger A and Ledger B are stored as their own scenario rows so a signal's
-- whole picture is queryable from one table.
CREATE TABLE IF NOT EXISTS shadow_results (
    result_id           TEXT PRIMARY KEY,
    run_id              TEXT NOT NULL REFERENCES shadow_runs(run_id),
    signal_id           TEXT NOT NULL,        -- references archive signals.signal_id
    asset               TEXT NOT NULL,
    direction           TEXT NOT NULL,
    ledger              TEXT NOT NULL,        -- "A_provider" | "B_theoretical" | "C_shadow"
    provenance          TEXT NOT NULL,        -- RECONSTRUCTED_DELAY_SCENARIO | OBSERVED_RECEIPT_TIME | PROVIDER
    delay_sec           INTEGER,              -- NULL for A/B
    slippage_usd        TEXT,                 -- NULL for A/B
    outcome_category    TEXT,                 -- archive category (context)
    r_value             TEXT,                 -- the R for this ledger/scenario (str Decimal) or NULL
    r_is_known          INTEGER NOT NULL DEFAULT 0,
    r_low               TEXT,                 -- pessimistic bound (ambiguous paths)
    r_high              TEXT,                 -- optimistic bound
    path_status         TEXT,                 -- RESOLVED | PATH_AMBIGUOUS | NO_EXECUTABLE_QUOTE | MISSED_ENTRY | UNQUANTIFIABLE | CLOSED_MARKET
    quote_grade         TEXT,                 -- Phase 1a price grade at the fill instant
    timestamp_grade     TEXT,                 -- always T-C for historical
    detail_json         TEXT,                 -- full reconstruction detail (fills, levels, leakage)
    price_source_ref    TEXT,                 -- which hour files / hashes backed this result
    config_hash         TEXT NOT NULL,
    computed_at_utc     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_results_run ON shadow_results(run_id);
CREATE INDEX IF NOT EXISTS ix_results_signal ON shadow_results(signal_id);

CREATE TABLE IF NOT EXISTS shadow_gate_evaluations (
    gate_id         TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL REFERENCES shadow_runs(run_id),
    gate_name       TEXT NOT NULL,
    passed          INTEGER NOT NULL,
    detail          TEXT,
    evaluated_at_utc TEXT NOT NULL
);
"""


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def connect(db_path=SHADOW_DB_PATH):
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.executescript(_SCHEMA)
    return conn


def ensure_config(conn, config_version, config_hash, config_dict):
    """Record a frozen config version (idempotent; never overwrites a differing hash)."""
    row = conn.execute("SELECT config_hash FROM shadow_configs WHERE config_version=?",
                       (config_version,)).fetchone()
    if row is not None:
        if row["config_hash"] != config_hash:
            raise ValueError(
                f"config {config_version} already stored with a DIFFERENT hash "
                f"({row['config_hash'][:12]}... != {config_hash[:12]}...) — bump the "
                f"version instead of editing a frozen config")
        return
    conn.execute(
        "INSERT INTO shadow_configs(config_version, config_hash, config_json, frozen_at_utc) "
        "VALUES (?,?,?,?)",
        (config_version, config_hash, json.dumps(config_dict, sort_keys=True), _utc_now()))


def start_run(conn, config_version, config_hash, archive_db_path, price_source,
              code_version, signals_total):
    # Any prior run still marked 'running' is an aborted/killed run — mark it so,
    # so consumers can cleanly filter to status='complete'. (Append-only; rebuildable.)
    conn.execute("UPDATE shadow_runs SET status='aborted' WHERE status='running'")
    run_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO shadow_runs(run_id, started_at_utc, config_version, config_hash, "
        "archive_db_path, price_source, code_version, signals_total, status) "
        "VALUES (?,?,?,?,?,?,?,?,'running')",
        (run_id, _utc_now(), config_version, config_hash, archive_db_path,
         price_source, code_version, signals_total))
    return run_id


def finish_run(conn, run_id, signals_priced, status="complete", notes=None):
    conn.execute(
        "UPDATE shadow_runs SET completed_at_utc=?, signals_priced=?, status=?, notes=? "
        "WHERE run_id=?", (_utc_now(), signals_priced, status, notes, run_id))


def insert_result(conn, run_id, config_hash, **f):
    """Insert one (signal, scenario) result row. `f` carries the result fields."""
    conn.execute(
        "INSERT INTO shadow_results(result_id, run_id, signal_id, asset, direction, "
        "ledger, provenance, delay_sec, slippage_usd, outcome_category, r_value, "
        "r_is_known, r_low, r_high, path_status, quote_grade, timestamp_grade, "
        "detail_json, price_source_ref, config_hash, computed_at_utc) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), run_id, f["signal_id"], f["asset"], f["direction"],
         f["ledger"], f["provenance"], f.get("delay_sec"), f.get("slippage_usd"),
         f.get("outcome_category"), f.get("r_value"), 1 if f.get("r_is_known") else 0,
         f.get("r_low"), f.get("r_high"), f.get("path_status"), f.get("quote_grade"),
         f.get("timestamp_grade"),
         json.dumps(f.get("detail", {}), default=str, sort_keys=True),
         f.get("price_source_ref"), config_hash, _utc_now()))


def insert_gate(conn, run_id, gate_name, passed, detail):
    conn.execute(
        "INSERT INTO shadow_gate_evaluations(gate_id, run_id, gate_name, passed, "
        "detail, evaluated_at_utc) VALUES (?,?,?,?,?,?)",
        (str(uuid.uuid4()), run_id, gate_name, 1 if passed else 0, detail, _utc_now()))


if __name__ == "__main__":
    c = connect()
    print("shadow.db ready at", SHADOW_DB_PATH)
    print("tables:", [r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")])
