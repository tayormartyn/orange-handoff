"""
Read-only accessors for legacy/protected databases.

Step 1 scope: this module ONLY provides strictly read-only inspection helpers. It creates
NO mapping, registers NO provider, and opens every legacy database via SQLite URI mode=ro
(optionally immutable=1 for files known not to be concurrently written). There is NO
writable cross-database relationship between the MPK canonical databases and any legacy
database — these helpers return Python values only.
"""
from __future__ import annotations
import hashlib
import os

import sys as _sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)
from appendonly import ro_connect

# project root = .../signal-terminal  (mpk -> campaign_extractor -> signal-terminal)
PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))


def file_sha256(path: str):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_baseline_28(signal_archive_path=None):
    """Read-only summary of the signed-off 28 baseline signals (mode=ro). Never writes."""
    path = signal_archive_path or os.path.join(PROJECT_ROOT, "data", "signal_archive.db")
    con = ro_connect(path, immutable=False)        # possibly-live DB -> no immutable
    try:
        cur = con.cursor()
        n = cur.execute(
            "SELECT COUNT(*) FROM signals WHERE source_message_key LIKE 'telegram:baseline:%'"
        ).fetchone()[0]
        rows = cur.execute(
            "SELECT source_message_key, provider, asset, direction, entry_low, entry_high, "
            "stop, tp1, tp2, tp3, classification FROM signals "
            "WHERE source_message_key LIKE 'telegram:baseline:%' ORDER BY source_message_key"
        ).fetchall()
        import json
        fp = hashlib.sha256(json.dumps(rows, sort_keys=True, default=str).encode()).hexdigest()
        return {"baseline_28_count": n, "rowset_fingerprint": fp}
    finally:
        con.close()
