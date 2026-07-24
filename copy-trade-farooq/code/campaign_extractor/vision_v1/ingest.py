"""
Immutable image ingestion + provenance. Originals are hashed, copied read-only, and NEVER edited,
recompressed or overwritten. Derived crops are separate files with their own hashes linked to the
original's hash. Includes a tiny stdlib PNG writer/dimension reader (no Pillow dependency).
"""
from __future__ import annotations
import hashlib
import os
import shutil
import stat
import struct
import time
import zlib

VISION_FIXTURE_ROOT = None   # set by caller; default resolved in ingest_image


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def detect_mime(path):
    with open(path, "rb") as f:
        head = f.read(12)
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


def image_dimensions(path):
    """Return (width, height) for PNG/JPEG without Pillow; (None, None) if unknown."""
    with open(path, "rb") as f:
        data = f.read()
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    if data[:3] == b"\xff\xd8\xff":
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            seg = struct.unpack(">H", data[i + 2:i + 4])[0]
            i += 2 + seg
    return None, None


def make_png(width, height, color=(30, 30, 30)):
    """Build a valid PNG (RGB) in-memory — used to create deterministic test fixtures."""
    raw = b""
    row = b"\x00" + bytes(color) * width
    for _ in range(height):
        raw += row
    def chunk(tag, body):
        c = tag + body
        return struct.pack(">I", len(body)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
            chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def ingest_image(src_path, candidate_db, *, media_id=None, source_message_id=None,
                 source_timestamp=None, dest_root=None):
    """Immutably ingest an original image and record it. Idempotent by content hash: re-ingesting
    the same bytes returns the existing media_id and does not duplicate or overwrite."""
    if not os.path.isfile(src_path):
        raise FileNotFoundError(src_path)
    digest = sha256_file(src_path)
    existing = candidate_db.get_image_by_sha(digest)
    if existing:
        return existing["media_id"], False           # idempotent

    ext = (os.path.splitext(src_path)[1].lstrip(".") or "bin").lower()
    mime = detect_mime(src_path)
    w, h = image_dimensions(src_path)
    size = os.path.getsize(src_path)
    mid = media_id or f"media-{digest[:16]}"
    root = dest_root or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "data", "vision_fixtures_v1")
    mdir = os.path.join(root, mid)
    os.makedirs(mdir, exist_ok=True)
    dest = os.path.join(mdir, f"original_{digest}.{ext}")
    if not os.path.exists(dest):
        shutil.copy2(src_path, dest)
        try:
            os.chmod(dest, stat.S_IREAD)              # originals never edited/overwritten
        except OSError:
            pass
    candidate_db.insert_image(
        media_id=mid, source_message_id=source_message_id, source_timestamp=source_timestamp,
        original_path=os.path.relpath(dest, root), sha256=digest, mime_type=mime, file_size=size,
        pixel_width=w, pixel_height=h,
        ingested_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    return mid, True


def register_derived(candidate_db, *, media_id, original_sha256, artifact_type, path_bytes,
                     region_id=None):
    """Register a derived crop/enhancement as its OWN file+hash, linked to the ORIGINAL's hash."""
    dgst = sha256_bytes(path_bytes)
    candidate_db.insert_derived(artifact_id=f"deriv-{dgst[:16]}", media_id=media_id,
                                original_sha256=original_sha256, artifact_type=artifact_type,
                                sha256=dgst, region_id=region_id)
    return dgst
