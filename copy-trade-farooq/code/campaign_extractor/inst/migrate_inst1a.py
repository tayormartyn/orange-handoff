"""
INST-1A migration — add the NULL-safe semantic-duplicate UNIQUE index to an existing
instrument_registry_v1.db.

Deterministic, transactional, idempotent, FAIL-CLOSED: it scans for existing semantic
duplicates FIRST and refuses to proceed if any are found (it never UPDATE/DELETE/merges to
force a unique index to build). Append-only history is preserved. Touches only the INST-1
database passed in.
"""
from __future__ import annotations
import os
import sqlite3

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)
from seed import REGISTRY_DB_PATH

SCHEMA_VERSION = "inst-1a.0"
INDEX_NAME = "ux_rule_semantic"
SEMKEY = ("input_token, scope, COALESCE(provider_id,'<<NULL>>'), "
          "COALESCE(target_underlying_id,'<<NULL>>'), COALESCE(target_instrument_id,'<<NULL>>'), "
          "rule_version, effective_from, COALESCE(effective_to,'<<NULL>>')")
INDEX_DDL = (f"CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME} ON mapping_rules ("
             "input_token, scope, COALESCE(provider_id,'<<NULL>>'), "
             "COALESCE(target_underlying_id,'<<NULL>>'), COALESCE(target_instrument_id,'<<NULL>>'), "
             "rule_version, effective_from, COALESCE(effective_to,'<<NULL>>'))")


def scan_semantic_duplicates(con):
    return con.execute(
        f"SELECT {SEMKEY}, COUNT(*) c, GROUP_CONCAT(mapping_rule_uid) FROM mapping_rules "
        f"GROUP BY {SEMKEY} HAVING c > 1").fetchall()


def migrate(db_path=None, applied_at=None):
    db_path = db_path or REGISTRY_DB_PATH
    con = sqlite3.connect(db_path)
    try:
        dups = scan_semantic_duplicates(con)
        if dups:
            return {"status": "BLOCKED", "duplicate_groups": len(dups),
                    "duplicates": [{"semantic_key": d[:-2], "count": d[-2],
                                    "rule_uids": d[-1]} for d in dups]}
        already = con.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name=?",
            (INDEX_NAME,)).fetchone()[0] > 0
        con.execute("BEGIN")
        try:
            con.execute(INDEX_DDL)        # IF NOT EXISTS -> idempotent
            con.execute("""CREATE TABLE IF NOT EXISTS inst_schema_meta (
                meta_id INTEGER PRIMARY KEY AUTOINCREMENT, schema_name TEXT NOT NULL,
                schema_version TEXT NOT NULL, applied_at_utc TEXT)""")
            has_ver = con.execute(
                "SELECT COUNT(*) FROM inst_schema_meta WHERE schema_version=?",
                (SCHEMA_VERSION,)).fetchone()[0]
            if not has_ver:
                con.execute("INSERT INTO inst_schema_meta (schema_name, schema_version, "
                            "applied_at_utc) VALUES (?,?,?)",
                            ("instrument_registry", SCHEMA_VERSION, applied_at))
            con.commit()
        except Exception:
            con.rollback()
            raise
        present = con.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name=?",
            (INDEX_NAME,)).fetchone()[0] > 0
        return {"status": "ALREADY_APPLIED" if already else "MIGRATED",
                "index_present": present,
                "mapping_rule_count": con.execute(
                    "SELECT COUNT(*) FROM mapping_rules").fetchone()[0],
                "semantic_duplicate_groups": 0}
    finally:
        con.close()


if __name__ == "__main__":
    import json
    print(json.dumps(migrate(), indent=2, sort_keys=True))
