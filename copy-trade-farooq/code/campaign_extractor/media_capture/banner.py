"""
Brick 5C Phase 2A truthful banner text (build-only). NOT printed by the running listener in
Phase 2A — the live banner is changed only at Phase 2B activation.
"""
from __future__ import annotations


def truthful_banner(media_capture_enabled: bool):
    lines = ["SIGNAL LISTENER (Telegram) — PREVIEW MODE",
             "Text/raw evidence capture is active (prospective_evidence_v1.db)."]
    if media_capture_enabled:
        lines += [
            "Supported Telegram image bytes ARE preserved (prospective_media_v1).",
            "No OCR or image interpretation occurs.",
            "Unsupported media (video/audio/etc.) remains reference/status only.",
        ]
    else:
        lines += [
            "Media references may be recorded; image-byte preservation is DISABLED.",
            "No media bytes are downloaded.",
        ]
    lines.append("No broker/quote/scoring/execution. Quotes NULL / BROKER_NOT_CONNECTED.")
    return lines
