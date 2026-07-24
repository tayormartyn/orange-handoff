"""
READ-ONLY loader for data/ctrader_quotes_v1.db -> the quote dicts the kernel consumes.

Opens SQLite in read-only mode (never writes/locks for write). One session at a time. Joins raw
timestamps + normalised values into the flat records the kernel expects.
"""
from __future__ import annotations
import os
import sqlite3
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(_HERE))
DEFAULT_QUOTES_DB = os.path.join(PROJECT_ROOT, "data", "ctrader_quotes_v1.db")


def _wall_ms(utc_text):
    if not utc_text:
        return None
    dt = datetime.fromisoformat(str(utc_text).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def load_session_quotes(session_id, db_path=None):
    """Return the kernel-shaped quote list for one session (read-only)."""
    path = db_path or DEFAULT_QUOTES_DB
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    rows = conn.execute(
        "SELECT r.event_sequence, r.symbol_id, r.raw_bid, r.raw_ask, r.broker_timestamp, "
        "r.local_received_utc, r.local_received_monotonic_ns, n.latest_bid, n.latest_ask, n.spread, "
        "n.flags, n.bid_provenance_seq, n.ask_provenance_seq "
        "FROM raw_spot_events r JOIN normalised_quotes n "
        "ON r.connection_session_id=n.connection_session_id AND r.event_sequence=n.event_sequence "
        "WHERE r.connection_session_id=? ORDER BY r.event_sequence", (session_id,)).fetchall()
    conn.close()
    out = []
    for (seq, sym, rbid, rask, bts, utc, mono, lbid, lask, spread, flags, bprov, aprov) in rows:
        out.append({"session": session_id, "seq": seq, "symbol_id": sym,
                    "raw_bid": rbid, "raw_ask": rask, "broker_ts": bts,
                    "wall_ms": _wall_ms(utc), "mono_ns": mono,
                    "bid": lbid, "ask": lask, "spread": spread, "flags": flags,  # latest-known
                    "bid_prov_seq": bprov, "ask_prov_seq": aprov})
    return out


def list_sessions(db_path=None):
    path = db_path or DEFAULT_QUOTES_DB
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    s = [r[0] for r in conn.execute(
        "SELECT DISTINCT connection_session_id FROM raw_spot_events").fetchall()]
    conn.close()
    return s
