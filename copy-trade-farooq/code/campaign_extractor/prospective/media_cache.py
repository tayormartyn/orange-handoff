"""
Brick 5C — Immutable Telegram image preservation (OFFLINE build).

Content-addressed media cache: image bytes are stored under a SEPARATE immutable cache keyed
by SHA-256 of the EXACT bytes, linked deterministically to channel/message/revision/evidence,
with a named media status. Raw text is stored independently FIRST (by the recorder), so a
media failure NEVER rolls back raw text. Image types only; size-limited; path-traversal-proof
(the on-disk name is the content hash — never a Telegram/user-supplied name); album/multiple-
image support. NO OCR / vision / chart interpretation / scoring / broker / execution. No raw
media bytes or captions are written to logs.

OFFLINE: image bytes are supplied by the caller (approved local fixtures). Live Telegram
download (download_media) is NOT wired here — activation needs a controlled restart +
allowlist review (separate approval).
"""
from __future__ import annotations
import hashlib
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from broker_readonly.secrets import safe_record

DEFAULT_MAX_BYTES = 10 * 1024 * 1024            # 10 MB

_MAGIC = [(b"\xff\xd8\xff", "jpeg"), (b"\x89PNG\r\n\x1a\n", "png"),
          (b"GIF87a", "gif"), (b"GIF89a", "gif"), (b"BM", "bmp")]


def _sniff_image_type(data: bytes):
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    for magic, t in _MAGIC:
        if data.startswith(magic):
            return t
    return None


class MediaCache:
    def __init__(self, root, index_db=None, max_bytes=DEFAULT_MAX_BYTES):
        self.root = os.path.abspath(root)
        os.makedirs(self.root, exist_ok=True)
        self.max_bytes = max_bytes
        self.index_db = index_db or os.path.join(self.root, "media_index_v1.db")
        self.con = sqlite3.connect(self.index_db)
        self._create()

    def _create(self):
        self.con.execute(
            "CREATE TABLE IF NOT EXISTS media_index ("
            "rowseq INTEGER PRIMARY KEY AUTOINCREMENT, media_id TEXT NOT NULL, media_sha256 TEXT,"
            "telegram_channel_id TEXT, telegram_message_id TEXT, message_revision_number INTEGER,"
            "evidence_id TEXT, album_index INTEGER, byte_size INTEGER, image_type TEXT,"
            "media_status TEXT NOT NULL, source_provenance TEXT, cached_path TEXT, index_hash TEXT NOT NULL)")
        for op in ("UPDATE", "DELETE"):
            self.con.execute(
                f"CREATE TRIGGER IF NOT EXISTS no{op.lower()}_media BEFORE {op} ON media_index "
                f"BEGIN SELECT RAISE(ABORT, 'append-only: {op} forbidden on media_index'); END;")
        self.con.commit()

    def _append(self, rec: dict):
        safe = safe_record(rec)                 # reject secret-named fields before persistence
        cols = list(safe)
        self.con.execute(
            f"INSERT INTO media_index ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
            [safe[c] for c in cols])
        self.con.commit()

    def preserve(self, image_bytes, *, telegram_channel_id, telegram_message_id,
                 message_revision_number=1, evidence_id=None, album_index=0,
                 source_provenance="LIVE_CAPTURED"):
        """Validate (image-only, size-limited, traversal-proof) then store EXACT bytes,
        content-addressed and immutable. Returns a NAMED status; never raises in a way that
        could roll back the already-stored raw text."""
        sha = itype = path = None
        size = len(image_bytes) if image_bytes else 0

        if not image_bytes:
            status = "MEDIA_EMPTY"
        elif size > self.max_bytes:
            status = "MEDIA_REJECTED_TOO_LARGE"
        else:
            itype = _sniff_image_type(image_bytes)
            if itype is None:
                status = "MEDIA_REJECTED_NOT_IMAGE"          # image types only
            else:
                sha = hashlib.sha256(image_bytes).hexdigest()
                fname = f"{sha}.{itype}"                     # content-addressed name only
                full = os.path.abspath(os.path.join(self.root, fname))
                if os.path.commonpath([self.root, full]) != self.root:
                    status = "MEDIA_REJECTED_PATH"           # traversal guard (belt-and-braces)
                else:
                    if not os.path.exists(full):             # write-once / dedupe by hash
                        with open(full, "wb") as f:
                            f.write(image_bytes)
                    path, status = fname, "MEDIA_CACHED"

        rec = {"media_sha256": sha, "telegram_channel_id": str(telegram_channel_id),
               "telegram_message_id": str(telegram_message_id),
               "message_revision_number": message_revision_number, "evidence_id": evidence_id,
               "album_index": album_index, "byte_size": size, "image_type": itype,
               "media_status": status, "source_provenance": source_provenance, "cached_path": path}
        rec["index_hash"] = hashlib.sha256(repr(sorted(rec.items())).encode("utf-8")).hexdigest()
        rec["media_id"] = (sha[:16] if sha else rec["index_hash"][:16])
        self._append(rec)
        return status

    # ---- read helpers
    def count(self):
        return self.con.execute("SELECT COUNT(*) FROM media_index").fetchone()[0]

    def cached_files(self):
        skip = (".db", ".db-journal", ".db-wal", ".db-shm")
        return sorted(f for f in os.listdir(self.root) if not f.endswith(skip))

    def rows(self):
        cur = self.con.execute("SELECT media_sha256, byte_size, image_type, media_status, "
                               "album_index, source_provenance, cached_path FROM media_index ORDER BY rowseq")
        return cur.fetchall()

    def close(self):
        self.con.close()
