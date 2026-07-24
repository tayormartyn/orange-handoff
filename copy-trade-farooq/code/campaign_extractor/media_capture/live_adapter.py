"""
Brick 5C Phase 2B live adapter — the thin glue between Telethon and the reviewed Phase 2A
store. build_descriptor() is pure/offline-testable; stream_download() applies the size cap
WHILE downloading; preserve_live() orchestrates dedup -> download -> atomic preserve.

No OCR/vision/interpretation. Image-only. A failure here returns a status; the caller has
ALREADY committed the text row, so text is never affected.
"""
from __future__ import annotations
import os

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)
import store as STORE


class MediaTooLarge(Exception):
    pass


def _err(e):
    """Bounded, safe diagnostic string for a media-handling exception. Includes the exception type
    and message (attribute/type errors describe attributes/APIs, not user content), truncated so a
    failure row is self-diagnosing without ever storing message content."""
    try:
        msg = str(e)
    except Exception:
        msg = ""
    s = f"{type(e).__name__}: {msg}" if msg else type(e).__name__
    return s[:180]


def build_descriptor(message):
    """Pure mapping of a Telethon message to the store descriptor (no download)."""
    media = getattr(message, "media", None)
    if media is None:
        return {"media_type": "none"}
    cls = type(media).__name__
    grouped = getattr(message, "grouped_id", None)
    grouped = str(grouped) if grouped else None
    if "Photo" in cls and getattr(media, "photo", None) is not None:
        photo = media.photo
        sizes = []
        try:
            for s in (getattr(photo, "sizes", None) or []):
                sz = getattr(s, "size", None)
                if sz is None:
                    ss = getattr(s, "sizes", None)      # PhotoSizeProgressive (list of ints)
                    try:
                        sz = max(ss) if ss else 0
                    except Exception:
                        sz = 0
                sizes.append({"bytes": sz or 0, "ref": getattr(s, "type", "") or str(sz)})
        except Exception:
            # A malformed/unknown size object must not crash descriptor building. classify() still
            # returns PHOTO on empty sizes (ref resolved later) so the image can still be captured.
            sizes = []
        return {"media_type": "photo", "sizes": sizes,
                "telegram_media_id": str(getattr(photo, "id", None)), "grouped_id": grouped}
    if "Document" in cls and getattr(media, "document", None) is not None:
        doc = media.document
        return {"media_type": "document", "mime": (getattr(doc, "mime_type", "") or "").lower(),
                "telegram_media_id": str(getattr(doc, "id", None)), "grouped_id": grouped}
    return {"media_type": cls, "grouped_id": grouped}     # video/voice/webpage/etc -> unsupported


async def stream_download(client, message, max_bytes):
    """Stream the media via the sanctioned iter_download primitive, aborting the moment the cap is
    exceeded (bounded memory). A download/attribute error here is caught by preserve_live and RECORDED
    as MEDIA_DOWNLOAD_FAILED (never a silent drop)."""
    buf = bytearray()
    total = 0
    async for chunk in client.iter_download(message.media):
        total += len(chunk)
        if total > max_bytes:
            raise MediaTooLarge()
        buf += chunk
    return bytes(buf)


async def preserve_live(client, message, *, media_db, media_dir, max_bytes, identity,
                        timestamps=None):
    """Returns a media capture status. Caller must have committed the text row first. The ENTIRE body
    fails SAFE: any unexpected error (e.g. an AttributeError from a client/download attribute mismatch)
    is recorded as MEDIA_HANDLING_ERROR rather than raised — the text evidence is never affected and the
    image simply falls back to human review / OCR-later instead of losing anything."""
    try:
        desc = build_descriptor(message)
        kind = STORE.classify(desc)[0]
        if kind == "NONE":
            return "NO_MEDIA"
        if kind == "UNSUPPORTED":
            # record without downloading any bytes
            return STORE.preserve_bytes(b"", desc, identity, media_db, media_dir=media_dir,
                                        max_bytes=max_bytes, timestamps=timestamps)
        if media_db.exists(platform=identity[0], channel_id=identity[1], message_id=identity[2],
                           revision=identity[3], grouped_id=identity[4], media_index=identity[5],
                           media_ref=identity[6]):
            return "DUPLICATE_MEDIA_REFERENCE"        # reconnect/replay -> no re-download
        try:
            data = await stream_download(client, message, max_bytes)
        except MediaTooLarge:
            return STORE.record_failure(media_db, identity, "MEDIA_TOO_LARGE", kind=kind,
                                        reason="exceeded cap while streaming", timestamps=timestamps)
        except Exception as e:
            return STORE.record_failure(media_db, identity, "MEDIA_DOWNLOAD_FAILED", kind=kind,
                                        reason=_err(e), timestamps=timestamps)
        return STORE.preserve_bytes(data, desc, identity, media_db, media_dir=media_dir,
                                    max_bytes=max_bytes, timestamps=timestamps)
    except Exception as e:                            # noqa: BLE001 — fail SAFE, never lose the text row
        # record_failure is resilient (falls back to an allowed status), so a handling error is
        # recorded rather than silently dropped; _err(e) captures the real message for diagnosis.
        return STORE.record_failure(media_db, identity, "MEDIA_HANDLING_ERROR", kind="unknown",
                                    reason=_err(e), timestamps=timestamps)
