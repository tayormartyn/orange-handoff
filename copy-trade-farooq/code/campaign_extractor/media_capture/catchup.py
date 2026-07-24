"""
Brick 5C Phase 2A controlled catch-up — BUILD ONLY (never executed against Telegram here).

A later Phase 2B may run this to reconcile the bounded restart-gap window. It takes an EXPLICIT
allowlisted channel, EXPLICIT lower/upper message-id bounds, and a READ-ONLY message iterator
(injected; the live version would wrap client.iter_messages — never executed in 2A). It:
  * processes only messages whose id is within [lower, upper];
  * reuses the idempotent text + media dedup logic (overlap with live capture is skipped, not
    duplicated, and existing rows are never relabelled);
  * produces a reconciliation report.
It NEVER scrapes broad history, adds a channel, infers messages outside the window, creates
campaigns, or performs OCR/interpretation.
"""
from __future__ import annotations
import os

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)
import pipeline as PIPE


def _text_exists(text_db, channel_id, message_id):
    return text_db.con.execute(
        "SELECT COUNT(*) FROM prospective_message_evidence WHERE telegram_channel_id=? "
        "AND telegram_message_id=?", (str(channel_id), str(message_id))).fetchone()[0] > 0


def run_catchup(channel_id, lower_id, upper_id, message_iter, *, text_db, media_db=None,
                downloader=None, allowlist, flag_enabled=False):
    """message_iter: iterable of message dicts (read-only; injected). Returns a report."""
    if channel_id not in allowlist:
        raise PermissionError(f"channel {channel_id} not on allowlist for catch-up")
    if lower_id is None or upper_id is None or lower_id > upper_id:
        raise ValueError("catch-up requires explicit lower_id <= upper_id bounds")

    report = {"channel_id": str(channel_id), "bounds": [lower_id, upper_id],
              "considered": 0, "out_of_bounds_skipped": 0, "text_new": 0,
              "text_duplicate_skipped": 0, "media_status_counts": {}}
    for msg in message_iter:
        mid = int(msg["message_id"])
        if mid < lower_id or mid > upper_id:
            report["out_of_bounds_skipped"] += 1          # NEVER process outside the window
            continue
        report["considered"] += 1
        if _text_exists(text_db, channel_id, mid):
            report["text_duplicate_skipped"] += 1         # overlap with live capture -> skip, no relabel
            continue
        res = PIPE.process(msg, text_db=text_db, media_db=media_db, downloader=downloader,
                           flag_enabled=flag_enabled, allowlist=allowlist)
        report["text_new"] += 1
        ms = res.get("media_status")
        if ms is not None:
            report["media_status_counts"][ms] = report["media_status_counts"].get(ms, 0) + 1
    return report
