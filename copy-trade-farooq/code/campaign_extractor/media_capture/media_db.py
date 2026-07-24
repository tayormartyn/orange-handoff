"""
Brick 5C Phase 2A media metadata DB (prospective_media_v1.db) — append-only, isolated.

Stores ONLY media linkage/metadata. Never stores image blobs (bytes live as content-addressed
files in prospective_media_v1/). Linked to the text evidence by immutable identity. A semantic
dedup UNIQUE index prevents duplicate rows on reconnect/replay/catch-up. content_sha256 is
metadata, NOT identity.
"""
from __future__ import annotations
import os
import sqlite3

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)
from _util import AppendOnlyViolation, append_only_trigger_ddl, canonical_hash, reject_mutation

SCHEMA_NAME = "prospective_media"
SCHEMA_VERSION = "media-5c2a.0"

STATUSES = ("MEDIA_CAPTURED", "NO_MEDIA", "UNSUPPORTED_MEDIA_TYPE", "MEDIA_DOWNLOAD_FAILED",
            "MEDIA_TOO_LARGE", "INVALID_MEDIA", "MEDIA_REFERENCE_MISSING",
            "DUPLICATE_MEDIA_REFERENCE", "STORAGE_WRITE_FAILED", "METADATA_WRITE_FAILED",
            "ORPHAN_FILE_NEEDS_RECONCILIATION", "FILE_MISSING_OR_HASH_MISMATCH",
            "MEDIA_HANDLING_ERROR")

_DDL = """
    CREATE TABLE IF NOT EXISTS media_records (
        rowseq INTEGER PRIMARY KEY AUTOINCREMENT,
        media_record_uid TEXT NOT NULL,
        evidence_row_uid TEXT,
        platform TEXT NOT NULL,
        channel_id TEXT NOT NULL,
        message_id TEXT NOT NULL,
        message_revision_number INTEGER NOT NULL,
        telegram_media_reference TEXT,
        grouped_media_id TEXT,
        media_index INTEGER NOT NULL,
        media_type TEXT,
        mime_type TEXT,
        safe_extension TEXT,
        byte_count INTEGER,
        content_sha256 TEXT,
        storage_relative_path TEXT,
        capture_status TEXT NOT NULL,
        failure_reason TEXT,
        telegram_posted_at_utc TEXT,
        listener_received_at_utc TEXT,
        media_download_started_at_utc TEXT,
        media_download_completed_at_utc TEXT,
        schema_version TEXT,
        created_at TEXT,
        CHECK (capture_status IN
            ('MEDIA_CAPTURED','NO_MEDIA','UNSUPPORTED_MEDIA_TYPE','MEDIA_DOWNLOAD_FAILED',
             'MEDIA_TOO_LARGE','INVALID_MEDIA','MEDIA_REFERENCE_MISSING',
             'DUPLICATE_MEDIA_REFERENCE','STORAGE_WRITE_FAILED','METADATA_WRITE_FAILED',
             'ORPHAN_FILE_NEEDS_RECONCILIATION','FILE_MISSING_OR_HASH_MISMATCH',
             'MEDIA_HANDLING_ERROR')))"""

# semantic logical-media identity (NULL-safe via COALESCE sentinel) — NOT content hash
_DEDUP_INDEX = (
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_media_identity ON media_records ("
    "platform, channel_id, message_id, message_revision_number, "
    "COALESCE(grouped_media_id,'<<NONE>>'), media_index, "
    "COALESCE(telegram_media_reference,'<<NONE>>'))")


def identity_uid(platform, channel_id, message_id, revision, grouped_id, media_index, media_ref):
    return "media_" + canonical_hash([platform, str(channel_id), str(message_id), revision,
                                      grouped_id, media_index, media_ref])[:24]


class MediaDB:
    def __init__(self, db_path):
        self.db_path = db_path
        d = os.path.dirname(db_path)
        if d:
            os.makedirs(d, exist_ok=True)
        self.con = sqlite3.connect(db_path)
        cur = self.con.cursor()
        cur.execute(_DDL)
        cur.execute(_DEDUP_INDEX)
        for trig in append_only_trigger_ddl("media_records"):
            cur.execute(trig)
        cur.execute("CREATE TABLE IF NOT EXISTS media_schema_meta (meta_id INTEGER PRIMARY KEY "
                    "AUTOINCREMENT, schema_name TEXT, schema_version TEXT)")
        if not cur.execute("SELECT COUNT(*) FROM media_schema_meta WHERE schema_version=?",
                           (SCHEMA_VERSION,)).fetchone()[0]:
            cur.execute("INSERT INTO media_schema_meta (schema_name, schema_version) VALUES (?,?)",
                        (SCHEMA_NAME, SCHEMA_VERSION))
        self.con.commit()

    def exists(self, *, platform, channel_id, message_id, revision, grouped_id, media_index,
               media_ref):
        return self.con.execute(
            "SELECT COUNT(*) FROM media_records WHERE platform=? AND channel_id=? AND message_id=? "
            "AND message_revision_number=? AND COALESCE(grouped_media_id,'<<NONE>>')=? "
            "AND media_index=? AND COALESCE(telegram_media_reference,'<<NONE>>')=?",
            (platform, str(channel_id), str(message_id), revision, grouped_id or "<<NONE>>",
             media_index, media_ref or "<<NONE>>")).fetchone()[0] > 0

    def append(self, rec: dict):
        cols = list(rec.keys())
        sql = f"INSERT INTO media_records ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})"
        reject_mutation(sql)
        self.con.execute(sql, [rec[c] for c in cols])
        self.con.commit()
        return rec

    def count(self):
        return self.con.execute("SELECT COUNT(*) FROM media_records").fetchone()[0]

    def by_status(self, status):
        return self.con.execute("SELECT COUNT(*) FROM media_records WHERE capture_status=?",
                                (status,)).fetchone()[0]

    def rows(self):
        cur = self.con.execute("SELECT message_id, media_index, content_sha256, capture_status, "
                               "storage_relative_path FROM media_records ORDER BY rowseq")
        return cur.fetchall()

    def close(self):
        self.con.close()
