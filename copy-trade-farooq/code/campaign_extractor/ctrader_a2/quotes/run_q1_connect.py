"""
Q1 PHASE 2 driver — ONE bounded XAUUSD live capture. Run under .venv-ctrader.

Loads cached token + creds (never printed), runs subscribe_and_capture (~45s, one reactor
lifecycle, no retry), then reads data/ctrader_quotes_v1.db (read-only) to print a SANITISED
report. No trading path anywhere.
"""
from __future__ import annotations
import json
import os
import sqlite3
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

CAPTURE_SECONDS = 45
XAUUSD_DIGITS = 2


def _report(db_path, session_id):
    c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    q = lambda sql, *a: c.execute(sql, a).fetchone()[0]
    raw_total = q("SELECT COUNT(*) FROM raw_spot_events WHERE connection_session_id=?", session_id)
    with_bid = q("SELECT COUNT(*) FROM raw_spot_events WHERE connection_session_id=? AND raw_bid IS NOT NULL", session_id)
    with_ask = q("SELECT COUNT(*) FROM raw_spot_events WHERE connection_session_id=? AND raw_ask IS NOT NULL", session_id)
    norm_total = q("SELECT COUNT(*) FROM normalised_quotes WHERE connection_session_id=?", session_id)
    paired = q("SELECT COUNT(*) FROM normalised_quotes WHERE connection_session_id=? AND spread IS NOT NULL AND flags NOT LIKE '%NEGATIVE_SPREAD%'", session_id)
    incomplete = q("SELECT COUNT(*) FROM normalised_quotes WHERE connection_session_id=? AND flags LIKE '%INCOMPLETE_NO_SIDES%'", session_id)
    bad = q("SELECT COUNT(*) FROM normalised_quotes WHERE connection_session_id=? AND (flags LIKE '%MALFORMED%' OR flags LIKE '%NEGATIVE_SPREAD%' OR flags LIKE '%STALE%')", session_id)
    bts = c.execute("SELECT MIN(broker_timestamp), MAX(broker_timestamp) FROM raw_spot_events WHERE connection_session_id=? AND broker_timestamp IS NOT NULL", (session_id,)).fetchone()
    lts = c.execute("SELECT MIN(local_received_utc), MAX(local_received_utc) FROM raw_spot_events WHERE connection_session_id=?", (session_id,)).fetchone()
    samples = c.execute("SELECT event_sequence, norm_bid, norm_ask, spread, flags FROM normalised_quotes WHERE connection_session_id=? ORDER BY event_sequence LIMIT 6", (session_id,)).fetchall()
    c.close()
    return {"raw_total": raw_total, "with_bid": with_bid, "with_ask": with_ask,
            "norm_total": norm_total, "valid_paired": paired, "incomplete": incomplete,
            "malformed_negative_stale": bad, "broker_ts_first_last": bts,
            "local_first_last": lts, "samples": samples}


def main():
    env = DL.load_ctrader_env()
    cid, csec = env.get("CTRADER_CLIENT_ID"), env.get("CTRADER_CLIENT_SECRET")
    tok = token_loader.load_cached_token()
    if not tok or not tok.get("access_token"):
        print("STOP: no cached access token"); return 2
    if not cid or not csec:
        print("STOP: client credentials not present"); return 2

    r = spot_reader.subscribe_and_capture(
        tok["access_token"], client_id=cid, client_secret=csec, digits=XAUUSD_DIGITS,
        capture_seconds=CAPTURE_SECONDS)

    print("=== Q1 LIVE CAPTURE RESULT (sanitised) ===")
    print(json.dumps({k: v for k, v in r.items() if k != "error" or v}, indent=2, default=str))
    if r.get("status") == "CAPTURE_COMPLETE":
        rep = _report(r["db_path"], r["session_id"])
        print("=== Q1 EVIDENCE SUMMARY (from DB) ===")
        print(json.dumps(rep, indent=2, default=str))
    return 0 if r.get("status") == "CAPTURE_COMPLETE" else 1


if __name__ == "__main__":
    sys.exit(main())
