"""
Brick 5C Phase 2A text-first pipeline (build-only; not wired into the live listener).

Order, enforced: (1) allowlist, (2) commit raw text evidence, (3) ONLY THEN attempt media.
Media runs in its own guarded block — any media error returns a status and leaves the
committed text row untouched. When the flag is False, no media download is attempted at all.
"""
from __future__ import annotations
import os

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)
# Collision-proof config load (never the ROOT project config.py) — see store.py for rationale.
import importlib.util as _ilu
_cfgspec = _ilu.spec_from_file_location("media_capture_config", os.path.join(_HERE, "config.py"))
CFG = _ilu.module_from_spec(_cfgspec)
_cfgspec.loader.exec_module(CFG)
import store as STORE

PLATFORM = CFG.PLATFORM_TELEGRAM


def _identity(message, media_index=0):
    return (PLATFORM, str(message["channel_id"]), str(message["message_id"]),
            int(message.get("revision", 1)), message.get("grouped_media_id"), media_index,
            message.get("media_reference"))


def process(message, *, text_db, media_db=None, downloader=None,
            flag_enabled=CFG.TELEGRAM_MEDIA_CAPTURE_ENABLED, max_bytes=None, media_dir=None,
            allowlist=None):
    """Process one captured message. text_db is the REAL ProspectiveDB (text schema unchanged).
    Returns {text_committed, text_evidence_id, media_status}."""
    if allowlist is not None and message["channel_id"] not in allowlist:
        raise PermissionError(f"channel {message['channel_id']} not on allowlist")

    # ---- 1+2: raw text evidence FIRST and committed (perishable; never lost to media) ----
    rec = text_db.append_message_evidence(
        telegram_channel_id=str(message["channel_id"]),
        telegram_message_id=str(message["message_id"]),
        telegram_posted_at_utc=message.get("posted_at"),
        listener_received_at_utc=message.get("received_at"),
        raw_text=message.get("raw_text"),                 # None for media-only -> NULL
        media_reference_or_hash=message.get("media_reference"),
        message_event_type="CREATED",
        message_revision_number=int(message.get("revision", 1)))
    result = {"text_committed": True, "text_evidence_id": rec.get("evidence_id"),
              "media_status": None}

    # ---- 3: media ONLY after a successful text commit, ONLY when activated ----
    if not flag_enabled:
        result["media_status"] = "DISABLED"
        return result
    desc = message.get("media_descriptor")
    if not desc or desc.get("media_type") in (None, "none"):
        result["media_status"] = "NO_MEDIA"
        return result
    try:
        result["media_status"] = STORE.preserve(
            desc, _identity(message, message.get("media_index", 0)), downloader, media_db,
            media_dir=media_dir, max_bytes=max_bytes,
            timestamps={"evidence_row_uid": rec.get("evidence_id"),
                        "posted_at": message.get("posted_at"),
                        "received_at": message.get("received_at")})
    except Exception as e:                  # catch-all: media can never break the committed text
        result["media_status"] = "MEDIA_DOWNLOAD_FAILED"
        result["media_error"] = type(e).__name__
    return result
