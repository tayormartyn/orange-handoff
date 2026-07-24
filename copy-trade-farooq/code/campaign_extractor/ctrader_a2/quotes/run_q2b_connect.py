"""
Q2B driver — ONE ~5-minute controlled XAUUSD capture. Run under .venv-ctrader.

Proves clean restart + session isolation (prior sessions' rows byte-fingerprinted before/after),
measures real bid/ask provenance age, and recommends evidence-based stale-warning / stale-rejection
thresholds. Append-only; no retry/reconnect/trading.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
import sqlite3
import statistics
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_A2 = os.path.dirname(_HERE)
_CE = os.path.dirname(_A2)
_ROOT = os.path.dirname(_CE)
for p in (_HERE, _A2, _CE, _ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from ctrader_a1 import dotenv_loader as DL
import token_loader
import spot_reader

CAPTURE_SECONDS = 5 * 60
XAUUSD_DIGITS = 2


def _pct(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    k = max(0, min(len(s) - 1, int(math.ceil((p / 100.0) * len(s))) - 1))
    return s[k]


def _fingerprint_excluding(conn, exclude_session):
    rows = conn.execute(
        "SELECT connection_session_id, event_sequence, raw_bid, raw_ask, broker_timestamp "
        "FROM raw_spot_events WHERE connection_session_id != ? "
        "ORDER BY connection_session_id, event_sequence", (exclude_session,)).fetchall()
    return len(rows), hashlib.sha256(json.dumps(rows, default=str).encode()).hexdigest()[:16]


def _session_counts(conn):
    return {r[0]: r[1] for r in conn.execute(
        "SELECT connection_session_id, COUNT(*) FROM raw_spot_events GROUP BY connection_session_id"
    ).fetchall()}


def _provenance_ages(conn, session_id):
    """For each normalised row, age (ms) of the latest bid and latest ask relative to this event."""
    ns = {r[0]: r[1] for r in conn.execute(
        "SELECT event_sequence, local_received_monotonic_ns FROM raw_spot_events "
        "WHERE connection_session_id=?", (session_id,)).fetchall()}
    norm = conn.execute(
        "SELECT event_sequence, bid_provenance_seq, ask_provenance_seq FROM normalised_quotes "
        "WHERE connection_session_id=?", (session_id,)).fetchall()
    bid_ages, ask_ages, worst = [], [], []
    for seq, bseq, aseq in norm:
        now = ns.get(seq)
        b = (now - ns[bseq]) / 1e6 if (bseq in ns and now is not None) else None
        a = (now - ns[aseq]) / 1e6 if (aseq in ns and now is not None) else None
        if b is not None:
            bid_ages.append(b)
        if a is not None:
            ask_ages.append(a)
        if b is not None and a is not None:
            worst.append(max(a, b))
    return bid_ages, ask_ages, worst


def _dist(vals):
    if not vals:
        return None
    return {"n": len(vals), "min_ms": round(min(vals), 3), "median_ms": round(statistics.median(vals), 3),
            "p95_ms": round(_pct(vals, 95), 3), "p99_ms": round(_pct(vals, 99), 3),
            "max_ms": round(max(vals), 3)}


def _round_up(x, step):
    return int(math.ceil(x / step) * step)


def main():
    env = DL.load_ctrader_env()
    cid, csec = env.get("CTRADER_CLIENT_ID"), env.get("CTRADER_CLIENT_SECRET")
    tok = token_loader.load_cached_token()
    if not tok or not tok.get("access_token"):
        print("STOP: no cached access token"); return 2

    db_path = spot_reader.QuoteDB(None).path
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    before_total = conn.execute("SELECT COUNT(*) FROM raw_spot_events").fetchone()[0]
    before_sessions = _session_counts(conn)
    # fingerprint ALL current rows (they are all "prior" until the new session appears)
    before_rows = conn.execute(
        "SELECT connection_session_id, event_sequence, raw_bid, raw_ask, broker_timestamp "
        "FROM raw_spot_events ORDER BY connection_session_id, event_sequence").fetchall()
    before_fp = (len(before_rows), hashlib.sha256(json.dumps(before_rows, default=str).encode()).hexdigest()[:16])
    conn.close()

    r = spot_reader.subscribe_and_capture(
        tok["access_token"], client_id=cid, client_secret=csec, digits=XAUUSD_DIGITS,
        capture_seconds=CAPTURE_SECONDS)
    new_sid = r["session_id"]

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    after_total = conn.execute("SELECT COUNT(*) FROM raw_spot_events").fetchone()[0]
    after_sessions = _session_counts(conn)
    prior_fp = _fingerprint_excluding(conn, new_sid)   # prior rows only, after the run
    bid_ages, ask_ages, worst = _provenance_ages(conn, new_sid)
    conn.close()

    prior_unchanged = (prior_fp == before_fp)
    bid_d, ask_d, worst_d = _dist(bid_ages), _dist(ask_ages), _dist(worst)

    # evidence-based thresholds from the WORST-side age distribution
    reco = None
    if worst_d:
        warn = _round_up(worst_d["p99_ms"], 50)
        reject = max(_round_up(worst_d["max_ms"] * 1.5, 100), warn * 2)
        reco = {"stale_warning_ms": warn, "stale_rejection_ms": reject,
                "basis": "warning = p99 of worst-side provenance age (round up 50ms); "
                         "rejection = max(1.5x max observed, 2x warning)"}

    print("=== Q2B CAPTURE RESULT (sanitised) ===")
    print(json.dumps(r, indent=2, default=str))
    print("=== Q2B SESSION ISOLATION ===")
    print(json.dumps({
        "new_session_id": new_sid,
        "db_total_before": before_total, "db_total_after": after_total,
        "rows_added": after_total - before_total,
        "prior_sessions_before": before_sessions,
        "prior_sessions_after_excluding_new": {k: v for k, v in after_sessions.items() if k != new_sid},
        "prior_rows_unchanged": prior_unchanged,
        "prior_fingerprint_before": before_fp, "prior_fingerprint_after": prior_fp,
    }, indent=2, default=str))
    print("=== Q2B PROVENANCE AGE (new session) ===")
    print(json.dumps({"bid_provenance_age": bid_d, "ask_provenance_age": ask_d,
                      "worst_side_age": worst_d, "recommended_thresholds": reco},
                     indent=2, default=str))
    ok = (r.get("status") == "CAPTURE_COMPLETE" and prior_unchanged)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
