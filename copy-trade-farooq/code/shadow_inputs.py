"""
shadow_inputs.py — SHADOW MODE Phase 1b, load every signal's shadow inputs from the
permanent archive (read-only). One place that knows how to read the archive, so the
ledgers/runner never touch SQL directly.

For each signal it assembles:
  * the levels (direction, conservative reference entry, stop, targets),
  * the provider ledger (calculated_r + r_is_known + category)   — Ledger A,
  * the posted time (T-C) and the re-entry BOUNDARY (next same-asset signal),
  * the primary management-evidence time (when the provider managed/closed it),
  * the price instrument + whether we have a validated Phase 1a feed for it.

Conservative reference entry (matches the brief + the sizing engine): a SELL uses
the LOWER edge of the entry range, a BUY the UPPER edge — the worse, easier-to-fill
edge — so R is never flattered by assuming the best corner of the zone.
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import shadow_config as cfg

ARCHIVE_DB = "data/signal_archive.db"

# Phase 1a PROVED only the gold feed. Anything else has no validated price source yet.
VALIDATED_INSTRUMENTS = {"XAUUSD": "XAUUSD"}


def _parse_ts(s):
    if not s:
        return None
    s = str(s).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def reference_entry(direction, entry_low, entry_high):
    """Conservative reference entry: SELL -> lower edge, BUY -> upper edge."""
    lo = Decimal(str(entry_low))
    hi = Decimal(str(entry_high))
    d = (direction or "").upper()
    if d in ("LONG", "BUY"):
        return max(lo, hi)
    return min(lo, hi)


def _targets(row):
    out = []
    for k in ("tp1", "tp2", "tp3"):
        v = (row[k] or "").strip()
        if v:
            out.append(v)
    return out


def load_signals(db_path=ARCHIVE_DB):
    """Return a list of shadow-input dicts, ordered by posted time."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    sigs = conn.execute("""
        SELECT s.*, p.outcome_category, p.calculated_r, p.r_is_known,
               p.primary_evidence_message_key, p.binary_rollup
        FROM signals s
        LEFT JOIN outcome_projections p ON p.signal_id = s.signal_id
        ORDER BY s.sent_at_utc, s.source_signal_index
    """).fetchall()

    # next same-asset signal time = the re-entry boundary for replay
    posted = {}
    for s in sigs:
        posted.setdefault(s["asset"], []).append(_parse_ts(s["sent_at_utc"]))
    for a in posted:
        posted[a] = sorted(t for t in posted[a] if t)

    def boundary_for(asset, t):
        later = [x for x in posted.get(asset, []) if x and x > t]
        horizon = t + timedelta(hours=cfg.MAX_REPLAY_HORIZON_HOURS)
        return min(later[0], horizon) if later else horizon

    out = []
    for s in sigs:
        t = _parse_ts(s["sent_at_utc"])
        if t is None:
            continue
        mgmt_key = s["primary_evidence_message_key"]
        mgmt_time = None
        if mgmt_key:
            r = conn.execute(
                "SELECT sent_at_utc FROM raw_message_versions WHERE message_key=? "
                "ORDER BY version_number LIMIT 1", (mgmt_key,)).fetchone()
            if r:
                mgmt_time = _parse_ts(r["sent_at_utc"])
        out.append({
            "signal_id": s["signal_id"],
            "asset": s["asset"],
            "instrument": VALIDATED_INSTRUMENTS.get(s["asset"]),   # None if no feed
            "direction": s["direction"],
            "entry_low": s["entry_low"], "entry_high": s["entry_high"],
            "ref_entry": str(reference_entry(s["direction"], s["entry_low"], s["entry_high"])),
            "stop": s["stop"],
            "targets": _targets(s),
            "posted_at": t,
            "boundary": boundary_for(s["asset"], t),
            "mgmt_time": mgmt_time,
            "category": s["outcome_category"],
            "provider_r": s["calculated_r"],
            "provider_r_is_known": bool(s["r_is_known"]),
            "binary_rollup": s["binary_rollup"],
        })
    conn.close()
    return out


if __name__ == "__main__":
    for s in load_signals():
        feed = s["instrument"] or "NO-FEED"
        print(f"{s['posted_at'].date()} {s['asset']:7} {s['direction']:5} "
              f"ref={s['ref_entry']:>8} sl={s['stop']:>6} tps={len(s['targets'])} "
              f"{s['category']:26} A={s['provider_r']} feed={feed} "
              f"mgmt={s['mgmt_time'].strftime('%m-%d %H:%M') if s['mgmt_time'] else '-'}")
