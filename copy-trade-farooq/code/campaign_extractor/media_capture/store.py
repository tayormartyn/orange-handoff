"""
Brick 5C Phase 2A media store — atomic, content-addressed, streaming-size-capped.

Sequence: temp file in target FS -> stream with byte cap -> validate image category ->
SHA-256 over completed bytes -> fsync+close -> atomic rename to {sha}.{ext} -> append metadata.
Never overwrites an existing final file. Final names are derived ONLY from the content hash +
validated extension (never a Telegram/user filename). Image-only (jpeg/png/webp/bmp); GIF/video
rejected. A media failure NEVER raises in a way that could roll back already-committed text.
"""
from __future__ import annotations
import hashlib
import os
import tempfile

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)
# Collision-proof: load media_capture's OWN config by file path under a unique module name. A bare
# `import config` would resolve to the ROOT project config.py (which the listener imports first and
# which has no image settings, e.g. PERMITTED_IMAGE_TYPES) -> AttributeError. This never does that.
import importlib.util as _ilu
_cfgspec = _ilu.spec_from_file_location("media_capture_config", os.path.join(_HERE, "config.py"))
CFG = _ilu.module_from_spec(_cfgspec)
_cfgspec.loader.exec_module(CFG)
from _util import sniff_image_type
from media_db import identity_uid


def classify(descriptor):
    """Return (kind, mime, ext_hint, selected_ref). kind in PHOTO/IMAGE_DOCUMENT/UNSUPPORTED/NONE."""
    if not descriptor or descriptor.get("media_type") in (None, "none"):
        return "NONE", None, None, None
    mt = descriptor.get("media_type")
    if mt == "photo":
        sizes = descriptor.get("sizes") or []
        if not sizes:
            return "PHOTO", "image/jpeg", None, None        # ref resolved later; may be missing
        largest = max(sizes, key=lambda s: s.get("bytes", 0))    # original Telegram-delivered size
        return "PHOTO", "image/jpeg", None, largest.get("ref")
    if mt == "document":
        mime = (descriptor.get("mime") or "").lower()
        if mime in CFG.PERMITTED_MIME:
            return "IMAGE_DOCUMENT", mime, CFG.PERMITTED_MIME[mime], descriptor.get("telegram_media_id")
        return "UNSUPPORTED", mime or None, None, descriptor.get("telegram_media_id")
    return "UNSUPPORTED", None, None, descriptor.get("telegram_media_id")   # video/voice/etc


def _rec(identity, *, status, kind=None, mime=None, ext=None, byte_count=None, sha=None,
         path=None, failure_reason=None, ts=None):
    ts = ts or {}
    rec = {
        "media_record_uid": identity_uid(*identity),
        "evidence_row_uid": ts.get("evidence_row_uid"),
        "platform": identity[0], "channel_id": str(identity[1]), "message_id": str(identity[2]),
        "message_revision_number": identity[3], "grouped_media_id": identity[4],
        "media_index": identity[5], "telegram_media_reference": identity[6],
        "media_type": kind, "mime_type": mime, "safe_extension": ext, "byte_count": byte_count,
        "content_sha256": sha, "storage_relative_path": path, "capture_status": status,
        "failure_reason": failure_reason,
        "telegram_posted_at_utc": ts.get("posted_at"),
        "listener_received_at_utc": ts.get("received_at"),
        "media_download_started_at_utc": ts.get("dl_start"),
        "media_download_completed_at_utc": ts.get("dl_end"),
        "schema_version": "media-5c2a.0", "created_at": ts.get("created_at"),
    }
    return rec


def preserve(descriptor, identity, downloader, media_db, *, media_dir=None,
             max_bytes=None, timestamps=None):
    """Returns a capture status string. identity = (platform, channel_id, message_id, revision,
    grouped_id, media_index, media_ref). Appends an append-only media row for every terminal
    outcome except DUPLICATE (which is the original row) and ORPHAN (DB unavailable)."""
    media_dir = media_dir or CFG.MEDIA_DIR
    max_bytes = max_bytes or CFG.TELEGRAM_MEDIA_MAX_BYTES
    os.makedirs(media_dir, exist_ok=True)
    kind, mime, ext_hint, selected_ref = classify(descriptor)

    if kind == "NONE":
        return "NO_MEDIA"
    if kind == "UNSUPPORTED":
        media_db.append(_rec(identity, status="UNSUPPORTED_MEDIA_TYPE", kind=kind, mime=mime,
                             failure_reason="non-image / unverified media", ts=timestamps))
        return "UNSUPPORTED_MEDIA_TYPE"
    media_ref = identity[6] or selected_ref
    if not media_ref:
        media_db.append(_rec(identity, status="MEDIA_REFERENCE_MISSING", kind=kind, ts=timestamps))
        return "MEDIA_REFERENCE_MISSING"
    if media_db.exists(platform=identity[0], channel_id=identity[1], message_id=identity[2],
                       revision=identity[3], grouped_id=identity[4], media_index=identity[5],
                       media_ref=identity[6]):
        return "DUPLICATE_MEDIA_REFERENCE"          # reconnect/replay -> no second row, no overwrite

    # ---- stream to a temp file in the target filesystem, enforcing the cap WHILE streaming ----
    fd, tmp = tempfile.mkstemp(dir=media_dir, prefix=".incoming_", suffix=".part")
    total = 0
    h = hashlib.sha256()
    try:
        with os.fdopen(fd, "wb") as f:
            for chunk in downloader(descriptor, selected_ref):
                total += len(chunk)
                if total > max_bytes:
                    raise _TooLarge()
                f.write(chunk)
                h.update(chunk)
            f.flush()
            os.fsync(f.fileno())
    except _TooLarge:
        _safe_remove(tmp)
        media_db.append(_rec(identity, status="MEDIA_TOO_LARGE", kind=kind,
                             failure_reason=f"exceeded {max_bytes} bytes while streaming",
                             ts=timestamps))
        return "MEDIA_TOO_LARGE"
    except Exception as e:                          # download/network/write error
        _safe_remove(tmp)
        media_db.append(_rec(identity, status="MEDIA_DOWNLOAD_FAILED", kind=kind,
                             failure_reason=type(e).__name__, ts=timestamps))
        return "MEDIA_DOWNLOAD_FAILED"

    # ---- validate the completed bytes are a permitted image ----
    with open(tmp, "rb") as f:
        head = f.read(16)
    itype = sniff_image_type(head)
    if itype is None or itype not in CFG.PERMITTED_IMAGE_TYPES:
        _safe_remove(tmp)
        media_db.append(_rec(identity, status="INVALID_MEDIA", kind=kind,
                             failure_reason=f"category={itype}", ts=timestamps))
        return "INVALID_MEDIA"

    sha = h.hexdigest()
    ext = ext_hint or CFG.TYPE_TO_EXT.get(itype, itype)
    final_name = f"{sha}.{ext}"
    final = os.path.abspath(os.path.join(media_dir, final_name))
    if os.path.commonpath([media_dir, final]) != media_dir:    # traversal backstop
        _safe_remove(tmp)
        media_db.append(_rec(identity, status="STORAGE_WRITE_FAILED", kind=kind,
                             failure_reason="path guard", ts=timestamps))
        return "STORAGE_WRITE_FAILED"
    try:
        if os.path.exists(final):
            _safe_remove(tmp)                        # write-once: identical bytes already stored
        else:
            os.replace(tmp, final)                   # atomic rename
    except Exception as e:
        _safe_remove(tmp)
        media_db.append(_rec(identity, status="STORAGE_WRITE_FAILED", kind=kind,
                             failure_reason=type(e).__name__, ts=timestamps))
        return "STORAGE_WRITE_FAILED"

    # ---- append metadata (after the file is durably in place) ----
    try:
        media_db.append(_rec(identity, status="MEDIA_CAPTURED", kind=kind, mime=mime, ext=ext,
                             byte_count=total, sha=sha, path=final_name, ts=timestamps))
        return "MEDIA_CAPTURED"
    except Exception:
        # file is durable + content-addressed; metadata could not be written -> reconcile later.
        return "ORPHAN_FILE_NEEDS_RECONCILIATION"


def record_failure(media_db, identity, status, *, kind=None, reason=None, timestamps=None):
    """Append-only record of a failure status. NEVER silently drops: if the requested status is not
    accepted by the DB (e.g. an older CHECK constraint that predates this status), fall back to an
    always-allowed status and preserve the true status + reason in failure_reason. Returns the status
    actually intended; only returns a sentinel if even the fallback write is impossible."""
    try:
        media_db.append(_rec(identity, status=status, kind=kind, failure_reason=reason, ts=timestamps))
        return status
    except Exception as e:
        detail = f"{status}" + (f":{reason}" if reason else "") + f" [fallback:{type(e).__name__}]"
        try:
            media_db.append(_rec(identity, status="MEDIA_DOWNLOAD_FAILED", kind=kind or "unknown",
                                 failure_reason=detail, ts=timestamps))
            return status
        except Exception:
            return "MEDIA_HANDLING_ERROR_UNRECORDABLE"


def preserve_bytes(data, descriptor, identity, media_db, *, media_dir=None, max_bytes=None,
                   timestamps=None):
    """Preserve ALREADY-DOWNLOADED bytes (live path: async stream-download capped the size,
    then this stores atomically). Same validation/dedup/atomic/append guarantees as preserve()."""
    media_dir = media_dir or CFG.MEDIA_DIR
    max_bytes = max_bytes or CFG.TELEGRAM_MEDIA_MAX_BYTES
    os.makedirs(media_dir, exist_ok=True)
    kind, mime, ext_hint, selected_ref = classify(descriptor)
    if kind == "NONE":
        return "NO_MEDIA"
    if kind == "UNSUPPORTED":
        media_db.append(_rec(identity, status="UNSUPPORTED_MEDIA_TYPE", kind=kind, mime=mime,
                             failure_reason="non-image / unverified media", ts=timestamps))
        return "UNSUPPORTED_MEDIA_TYPE"
    if not (identity[6] or selected_ref):
        media_db.append(_rec(identity, status="MEDIA_REFERENCE_MISSING", kind=kind, ts=timestamps))
        return "MEDIA_REFERENCE_MISSING"
    if media_db.exists(platform=identity[0], channel_id=identity[1], message_id=identity[2],
                       revision=identity[3], grouped_id=identity[4], media_index=identity[5],
                       media_ref=identity[6]):
        return "DUPLICATE_MEDIA_REFERENCE"
    if not data:
        media_db.append(_rec(identity, status="INVALID_MEDIA", kind=kind,
                             failure_reason="empty bytes", ts=timestamps))
        return "INVALID_MEDIA"
    if len(data) > max_bytes:
        media_db.append(_rec(identity, status="MEDIA_TOO_LARGE", kind=kind,
                             failure_reason=f"exceeded {max_bytes} bytes", ts=timestamps))
        return "MEDIA_TOO_LARGE"
    itype = sniff_image_type(data[:16])
    if itype is None or itype not in CFG.PERMITTED_IMAGE_TYPES:
        media_db.append(_rec(identity, status="INVALID_MEDIA", kind=kind,
                             failure_reason=f"category={itype}", ts=timestamps))
        return "INVALID_MEDIA"
    sha = hashlib.sha256(data).hexdigest()
    ext = ext_hint or CFG.TYPE_TO_EXT.get(itype, itype)
    final = os.path.abspath(os.path.join(media_dir, f"{sha}.{ext}"))
    if os.path.commonpath([media_dir, final]) != media_dir:
        media_db.append(_rec(identity, status="STORAGE_WRITE_FAILED", kind=kind,
                             failure_reason="path guard", ts=timestamps))
        return "STORAGE_WRITE_FAILED"
    fd, tmp = tempfile.mkstemp(dir=media_dir, prefix=".incoming_", suffix=".part")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if os.path.exists(final):
            _safe_remove(tmp)                    # write-once: identical bytes already stored
        else:
            os.replace(tmp, final)               # atomic rename
    except Exception as e:
        _safe_remove(tmp)
        media_db.append(_rec(identity, status="STORAGE_WRITE_FAILED", kind=kind,
                             failure_reason=type(e).__name__, ts=timestamps))
        return "STORAGE_WRITE_FAILED"
    try:
        media_db.append(_rec(identity, status="MEDIA_CAPTURED", kind=kind, mime=mime, ext=ext,
                             byte_count=len(data), sha=sha, path=f"{sha}.{ext}", ts=timestamps))
        return "MEDIA_CAPTURED"
    except Exception:
        return "ORPHAN_FILE_NEEDS_RECONCILIATION"


def reconcile(row, media_dir=None):
    """row=(message_id, media_index, content_sha256, capture_status, storage_relative_path).
    Verify the on-disk file matches the recorded hash. No redownload/overwrite in this phase."""
    media_dir = media_dir or CFG.MEDIA_DIR
    _, _, sha, status, relpath = row
    if status != "MEDIA_CAPTURED" or not relpath:
        return "OK_NON_FILE"
    full = os.path.join(media_dir, relpath)
    if not os.path.exists(full):
        return "FILE_MISSING_OR_HASH_MISMATCH"
    actual = hashlib.sha256(open(full, "rb").read()).hexdigest()
    return "OK" if actual == sha else "FILE_MISSING_OR_HASH_MISMATCH"


class _TooLarge(Exception):
    pass


def _safe_remove(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
