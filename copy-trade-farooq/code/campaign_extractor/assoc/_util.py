"""ASSOC-1 append-only primitives (self-contained — keeps ASSOC-1 isolated)."""
from __future__ import annotations
import hashlib
import json
import sqlite3


class AppendOnlyViolation(Exception):
    pass


_FORBIDDEN = ("UPDATE", "DELETE", "REPLACE")


def reject_mutation(sql):
    s = (sql or "").strip()
    head = s.split(None, 1)[0].upper() if s else ""
    if head in _FORBIDDEN:
        raise AppendOnlyViolation(f"append-only: business-record {head} rejected")
    if head == "INSERT" and " OR REPLACE" in s.upper().split(")")[0]:
        raise AppendOnlyViolation("append-only: INSERT OR REPLACE rejected")


def append_only_trigger_ddl(table):
    return [
        (f"CREATE TRIGGER IF NOT EXISTS noupd_{table} BEFORE UPDATE ON {table} "
         f"BEGIN SELECT RAISE(ABORT, 'append-only: UPDATE forbidden on {table}'); END;"),
        (f"CREATE TRIGGER IF NOT EXISTS nodel_{table} BEFORE DELETE ON {table} "
         f"BEGIN SELECT RAISE(ABORT, 'append-only: DELETE forbidden on {table}'); END;"),
    ]


def canonical_hash(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True, default=str).encode()).hexdigest()


def ro_connect(path, immutable=False):
    uri = f"file:{path}?mode=ro" + ("&immutable=1" if immutable else "")
    return sqlite3.connect(uri, uri=True)
