"""
ASSOC-1R provenance — READ-ONLY load of the live-captured XAUUSD sequence from
prospective_evidence_v1.db, plus the separately-labelled manual screenshot fixtures.

Never writes; never invents a message id or hash; never relabels a manual screenshot as
LIVE_CAPTURED. Real message ids/hashes come verbatim from the live DB.
"""
from __future__ import annotations
import os
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROSPECTIVE_DB = os.path.join(ROOT, "campaign_extractor", "prospective", "data",
                              "prospective_evidence_v1.db")
TRACKED_CHANNEL = "-1001902136163"
# the XAUUSD campaign window (verified by read-only inspection)
WINDOW_FIRST, WINDOW_LAST = 45331, 45345


def load_live_rows(db_path=None):
    """Read-only: return the live-captured rows in the XAUUSD window, with real ids+hashes."""
    db_path = db_path or PROSPECTIVE_DB
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "SELECT telegram_message_id, telegram_posted_at_utc, listener_received_at_utc, "
            "raw_text, raw_text_hash, media_reference_or_hash, message_event_type "
            "FROM prospective_message_evidence WHERE telegram_channel_id=? "
            "AND CAST(telegram_message_id AS INTEGER) BETWEEN ? AND ? "
            "ORDER BY CAST(telegram_message_id AS INTEGER)",
            (TRACKED_CHANNEL, WINDOW_FIRST, WINDOW_LAST)).fetchall()
        out = []
        for (mid, posted, recv, raw, h, media, ev) in rows:
            text = raw or ""
            header_sender = None
            if " Posted in " in text:
                header_sender = text.split(" Posted in ", 1)[0].strip()
            out.append({
                "message_id": str(mid), "posted_at": posted, "received_at": recv,
                "raw_text": text, "raw_text_hash": h, "has_media": bool(media),
                "message_event_type": ev, "header_sender": header_sender,
                "channel_id": TRACKED_CHANNEL, "provenance": "LIVE_CAPTURED",
            })
        return out
    finally:
        con.close()


# Position screenshots Martyn supplied manually. The text-only listener did NOT capture image
# bytes, so these values are IMAGE-ONLY and remain a separate manual fixture. They are NEVER
# summed and never establish a broker/result fact.
MANUAL_SCREENSHOT_FIXTURES = [
    {"fixture_id": "manual_pos_entry", "provenance": "MANUAL_SCREENSHOT_FIXTURE",
     "image_only_field": "entry", "value": "4060.39", "broker_confirmed": False},
    {"fixture_id": "manual_pos_float_1", "provenance": "MANUAL_SCREENSHOT_FIXTURE",
     "image_only_field": "floating_profit", "value": "831.00", "broker_confirmed": False},
    {"fixture_id": "manual_pos_float_2", "provenance": "MANUAL_SCREENSHOT_FIXTURE",
     "image_only_field": "floating_profit", "value": "1239.00", "broker_confirmed": False},
    {"fixture_id": "manual_pos_float_3", "provenance": "MANUAL_SCREENSHOT_FIXTURE",
     "image_only_field": "floating_profit", "value": "1457.00", "broker_confirmed": False},
]
