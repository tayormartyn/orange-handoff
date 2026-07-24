"""
Shared append-only primitives for the MPK canonical databases.

Two enforcement levels are provided:

  * DATABASE level  — append_only_trigger_ddl(table) builds BEFORE UPDATE / BEFORE DELETE
    triggers that RAISE(ABORT) with a deterministic message. Applied to every
    business/history table; NEVER applied to the schema-control table.

  * APPLICATION level — reject_mutation(sql) intercepts an UPDATE/DELETE/REPLACE statement
    against a business/history row and raises AppendOnlyViolation BEFORE it reaches the
    database. Schema statements (CREATE/ALTER/DROP) and INSERT/SELECT pass this guard, so
    schema maintenance is explicitly NOT confused with business-record mutation.

Pure stdlib. No I/O, no network, no spine imports.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3


class AppendOnlyViolation(Exception):
    """Raised by the application-level guard when a business-row mutation is attempted."""


# UPDATE/DELETE/REPLACE mutate existing rows -> forbidden on append-only business tables.
# (REPLACE == INSERT OR REPLACE, which can delete a conflicting row.)
_FORBIDDEN_ROW_MUTATIONS = ("UPDATE", "DELETE", "REPLACE")


def reject_mutation(sql: str) -> None:
    """Application-level guard: raise AppendOnlyViolation for a business-row mutation.

    This runs BEFORE any database call. INSERT, SELECT and schema statements
    (CREATE/ALTER/DROP) are permitted to pass — schema control is separate from
    business-record mutation by design.
    """
    s = (sql or "").strip()
    while s.startswith("("):
        s = s[1:].strip()
    head = s.split(None, 1)[0].upper() if s else ""
    if head in _FORBIDDEN_ROW_MUTATIONS:
        raise AppendOnlyViolation(
            f"append-only: business-record {head} rejected at application layer "
            f"(statement: {s[:60]!r})")
    # "INSERT OR REPLACE" begins with INSERT but carries REPLACE semantics -> also reject.
    if head == "INSERT" and " OR REPLACE" in s.upper().split(")")[0]:
        raise AppendOnlyViolation(
            "append-only: INSERT OR REPLACE rejected at application layer (replace semantics)")


def append_only_trigger_ddl(table: str):
    """Return the (no-update, no-delete) trigger DDL for an append-only business table."""
    return [
        (f"CREATE TRIGGER IF NOT EXISTS noupd_{table} BEFORE UPDATE ON {table} "
         f"BEGIN SELECT RAISE(ABORT, 'append-only: UPDATE forbidden on business/history "
         f"table {table}'); END;"),
        (f"CREATE TRIGGER IF NOT EXISTS nodel_{table} BEFORE DELETE ON {table} "
         f"BEGIN SELECT RAISE(ABORT, 'append-only: DELETE forbidden on business/history "
         f"table {table}'); END;"),
    ]


def canonical_hash(record: dict) -> str:
    """SHA-256 over a canonical (sorted-key) JSON rendering of a record."""
    return hashlib.sha256(
        json.dumps(record, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def ro_connect(path: str, immutable: bool = False) -> sqlite3.Connection:
    """Open a STRICTLY read-only connection to an existing (legacy/protected) database.

    Uses the SQLite URI mode=ro so the connection can never write. immutable=1 is added
    ONLY when the caller asserts the file is not concurrently written (it tells SQLite the
    file cannot change, which is unsafe for a live DB). This helper never creates a file.
    """
    uri = f"file:{path}?mode=ro" + ("&immutable=1" if immutable else "")
    return sqlite3.connect(uri, uri=True)
