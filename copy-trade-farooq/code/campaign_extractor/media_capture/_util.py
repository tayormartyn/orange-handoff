"""Media-capture append-only primitives (self-contained)."""
from __future__ import annotations
import hashlib
import json
import sqlite3


class AppendOnlyViolation(Exception):
    pass


def reject_mutation(sql):
    head = (sql or "").strip().split(None, 1)[0].upper() if sql else ""
    if head in ("UPDATE", "DELETE", "REPLACE"):
        raise AppendOnlyViolation(f"append-only: {head} rejected")


def append_only_trigger_ddl(table):
    return [
        (f"CREATE TRIGGER IF NOT EXISTS noupd_{table} BEFORE UPDATE ON {table} "
         f"BEGIN SELECT RAISE(ABORT, 'append-only: UPDATE forbidden on {table}'); END;"),
        (f"CREATE TRIGGER IF NOT EXISTS nodel_{table} BEFORE DELETE ON {table} "
         f"BEGIN SELECT RAISE(ABORT, 'append-only: DELETE forbidden on {table}'); END;"),
    ]


def canonical_hash(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def ro_connect(path, immutable=False):
    uri = f"file:{path}?mode=ro" + ("&immutable=1" if immutable else "")
    return sqlite3.connect(uri, uri=True)


# magic-byte image sniff. GIF intentionally NOT in the permitted set (animation risk).
_MAGIC = [(b"\xff\xd8\xff", "jpeg"), (b"\x89PNG\r\n\x1a\n", "png"), (b"BM", "bmp")]


def sniff_image_type(data: bytes):
    if not data:
        return None
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    for magic, t in _MAGIC:
        if data.startswith(magic):
            return t
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "gif"            # detected but NOT permitted -> caller rejects as unsupported
    return None
