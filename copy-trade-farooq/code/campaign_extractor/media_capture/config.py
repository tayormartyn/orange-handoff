"""
Brick 5C Phase 2A config — fail-closed defaults. Activation to True is separately authorised
(Phase 2B). While False the listener behaves exactly as it does today (no media download).
"""
import os

_HERE = os.path.dirname(os.path.abspath(__file__))

# ---- ACTIVATION FLAG (default False — fail closed) ----
# Phase 2B CONTROLLED ACTIVATION (2026-06-30): set True under Martyn's manual restart control.
# Rollback = set back to False and restart the listener (text-only PREVIEW).
TELEGRAM_MEDIA_CAPTURE_ENABLED = True

# ---- conservative streaming size cap ----
# 10 MiB: Telegram-delivered photos are well under this; bounds disk + memory per item and
# stops a malicious/oversized document from being buffered. Enforced WHILE streaming.
TELEGRAM_MEDIA_MAX_BYTES = 10 * 1024 * 1024

# ---- bounded album cap ----
TELEGRAM_MEDIA_MAX_ALBUM_ITEMS = 10

# ---- permitted image categories (image-only; GIF/animation EXCLUDED on purpose) ----
PERMITTED_IMAGE_TYPES = ("jpeg", "png", "webp", "bmp")
PERMITTED_MIME = {
    "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/bmp": "bmp",
}
TYPE_TO_EXT = {"jpeg": "jpg", "png": "png", "webp": "webp", "bmp": "bmp"}

# ---- isolated storage (separate from every text/evidence/protected DB) ----
MEDIA_DIR = os.path.join(_HERE, "..", "prospective", "data", "prospective_media_v1")
MEDIA_DB = os.path.join(_HERE, "..", "prospective", "data", "prospective_media_v1.db")
MEDIA_DIR = os.path.abspath(MEDIA_DIR)
MEDIA_DB = os.path.abspath(MEDIA_DB)

PLATFORM_TELEGRAM = "TELEGRAM"
