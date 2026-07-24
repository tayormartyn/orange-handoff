"""
INST-1 append-only primitives (self-contained — no mpk/ import, keeps INST-1 isolated).
"""
from __future__ import annotations
import hashlib
import json
import sqlite3


class AppendOnlyViolation(Exception):
    """Application-level guard: a business-row mutation was attempted."""


_FORBIDDEN_ROW_MUTATIONS = ("UPDATE", "DELETE", "REPLACE")


def reject_mutation(sql: str) -> None:
    s = (sql or "").strip()
    while s.startswith("("):
        s = s[1:].strip()
    head = s.split(None, 1)[0].upper() if s else ""
    if head in _FORBIDDEN_ROW_MUTATIONS:
        raise AppendOnlyViolation(
            f"append-only: business-record {head} rejected at application layer")
    if head == "INSERT" and " OR REPLACE" in s.upper().split(")")[0]:
        raise AppendOnlyViolation("append-only: INSERT OR REPLACE rejected (replace semantics)")


def append_only_trigger_ddl(table: str):
    return [
        (f"CREATE TRIGGER IF NOT EXISTS noupd_{table} BEFORE UPDATE ON {table} "
         f"BEGIN SELECT RAISE(ABORT, 'append-only: UPDATE forbidden on {table}'); END;"),
        (f"CREATE TRIGGER IF NOT EXISTS nodel_{table} BEFORE DELETE ON {table} "
         f"BEGIN SELECT RAISE(ABORT, 'append-only: DELETE forbidden on {table}'); END;"),
    ]


def canonical_hash(record) -> str:
    return hashlib.sha256(
        json.dumps(record, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def ro_connect(path: str, immutable: bool = False) -> sqlite3.Connection:
    uri = f"file:{path}?mode=ro" + ("&immutable=1" if immutable else "")
    return sqlite3.connect(uri, uri=True)
