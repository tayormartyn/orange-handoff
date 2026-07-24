"""
Q2A driver — ONE bounded 15-minute XAUUSD continuity capture. Run under .venv-ctrader.

Appends a new session to data/ctrader_quotes_v1.db (never deletes/updates earlier rows), then
computes a sanitised continuity report from the NEW session only. No trading path anywhere.
"""
from __future__ import annotations
import json
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

CAPTURE_SECONDS = 15 * 60           # 15 minutes
XAUUSD_DIGITS = 2


def _pct(sorted_vals, p):
    if not sorted_vals:
        return None
    k = max(0, min(len(sorted_vals) - 1, int(round((p / 100.0) * (len(sorted_vals) - 1)))))
    return sorted_vals[k]


def _continuity(db_path, session_id):
    c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    rows = c.execute(
        "SELECT event_sequence, raw_bid, raw_ask, broker_timestamp, local_received_utc, "
        "local_received_monotonic_ns FROM raw_spot_events WHERE connection_session_id=? "
        "ORDER BY event_sequence", (session_id,)).fetchall()
    nrows = c.execute("SELECT COUNT(*) FROM normalised_quotes WHERE connection_session_id=?",
                      (session_id,)).fetchone()[0]
    bid_present = sum(1 for r in rows if r[1] is not None)
    ask_present = sum(1 for r in rows if r[2] is not None)
    paired = c.execute("SELECT COUNT(*) FROM normalised_quotes WHERE connection_session_id=? "
                       "AND spread IS NOT NULL AND flags NOT LIKE '%NEGATIVE_SPREAD%'",
                       (session_id,)).fetchone()[0]
    incomplete = c.execute("SELECT COUNT(*) FROM normalised_quotes WHERE connection_session_id=? "
                           "AND flags LIKE '%INCOMPLETE_NO_SIDES%'", (session_id,)).fetchone()[0]
    malformed_neg = c.execute("SELECT COUNT(*) FROM normalised_quotes WHERE connection_session_id=? "
                              "AND (flags LIKE '%MALFORMED%' OR flags LIKE '%NEGATIVE_SPREAD%')",
                              (session_id,)).fetchone()[0]
    stale = c.execute("SELECT COUNT(*) FROM normalised_quotes WHERE connection_session_id=? "
                      "AND flags LIKE '%STALE%'", (session_id,)).fetchone()[0]

    # inter-event gaps (ms) from local monotonic ns
    ns = [r[5] for r in rows if r[5] is not None]
    gaps = sorted((ns[i] - ns[i - 1]) / 1e6 for i in range(1, len(ns)))
    gap_stats = {"min_ms": round(gaps[0], 3) if gaps else None,
                 "median_ms": round(statistics.median(gaps), 3) if gaps else None,
                 "p95_ms": round(_pct(gaps, 95), 3) if gaps else None,
                 "max_ms": round(gaps[-1], 3) if gaps else None}

    # broker timestamp monotonicity
    bts = [r[3] for r in rows if r[3] is not None]
    bt_monotonic = all(bts[i] >= bts[i - 1] for i in range(1, len(bts)))
    bt_regressions = sum(1 for i in range(1, len(bts)) if bts[i] < bts[i - 1])

    # duplicate events (same broker_ts + bid + ask)
    keys = [(r[3], r[1], r[2]) for r in rows]
    duplicates = len(keys) - len(set(keys))

    # sequence anomalies (should be 1..N contiguous, unique)
    seqs = [r[0] for r in rows]
    seq_anomalies = 0 if seqs == list(range(1, len(seqs) + 1)) else len(
        set(range(1, len(seqs) + 1)) ^ set(seqs)) + (len(seqs) - len(set(seqs)))

    samples = c.execute("SELECT event_sequence, norm_bid, norm_ask, spread FROM normalised_quotes "
                        "WHERE connection_session_id=? ORDER BY event_sequence", (session_id,)).fetchall()
    first_last_local = (rows[0][4] if rows else None, rows[-1][4] if rows else None)
    first_last_broker = (bts[0] if bts else None, bts[-1] if bts else None)
    c.close()
    return {
        "total_spot_events": len(rows), "normalised_rows": nrows,
        "bid_present": bid_present, "ask_present": ask_present, "valid_paired": paired,
        "incomplete": incomplete, "malformed_or_negative": malformed_neg,
        "stale_count_persisted": stale,
        "first_last_broker_ts": first_last_broker, "first_last_local_utc": first_last_local,
        "inter_event_gap_ms": gap_stats, "broker_ts_monotonic": bt_monotonic,
        "broker_ts_regressions": bt_regressions, "duplicate_events": duplicates,
        "sequence_anomalies": seq_anomalies,
        "first_sample": samples[0] if samples else None,
        "last_sample": samples[-1] if samples else None,
    }


def main():
    env = DL.load_ctrader_env()
    cid, csec = env.get("CTRADER_CLIENT_ID"), env.get("CTRADER_CLIENT_SECRET")
    tok = token_loader.load_cached_token()
    if not tok or not tok.get("access_token"):
        print("STOP: no cached access token"); return 2

    db_path = spot_reader.QuoteDB(None).path
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    before_raw = conn.execute("SELECT COUNT(*) FROM raw_spot_events").fetchone()[0]
    before_norm = conn.execute("SELECT COUNT(*) FROM normalised_quotes").fetchone()[0]
    conn.close()

    r = spot_reader.subscribe_and_capture(
        tok["access_token"], client_id=cid, client_secret=csec, digits=XAUUSD_DIGITS,
        capture_seconds=CAPTURE_SECONDS)

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    after_raw = conn.execute("SELECT COUNT(*) FROM raw_spot_events").fetchone()[0]
    after_norm = conn.execute("SELECT COUNT(*) FROM normalised_quotes").fetchone()[0]
    conn.close()

    print("=== Q2A CAPTURE RESULT (sanitised) ===")
    print(json.dumps(r, indent=2, default=str))
    print("=== Q2A COUNTS ===")
    print(json.dumps({"intended_seconds": CAPTURE_SECONDS, "db_before": {"raw": before_raw, "norm": before_norm},
                      "db_after": {"raw": after_raw, "norm": after_norm},
                      "rows_added": {"raw": after_raw - before_raw, "norm": after_norm - before_norm}},
                     indent=2))
    print("=== Q2A CONTINUITY (new session) ===")
    print(json.dumps(_continuity(db_path, r["session_id"]), indent=2, default=str))
    return 0 if r.get("status") == "CAPTURE_COMPLETE" else 1


if __name__ == "__main__":
    sys.exit(main())
