"""
Q4B observer — ONE bounded (~4h) view-only XAUUSD quote session beside the Telegram listener.

argv: <quote_session_id> <manifest_path> <capture_seconds>. Uses the proven recorder
(subscribe_and_capture) with a caller-supplied session id, appends only to ctrader_quotes_v1.db,
and updates the Q4B manifest with the end state. No retry/reconnect/trading. Leaves the listener
untouched. Preserves all evidence already written on any early stop.
"""
from __future__ import annotations
import json
import os
import sqlite3
import sys
import time

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


def _counts(db_path):
    c = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    raw = c.execute("SELECT COUNT(*) FROM raw_spot_events").fetchone()[0]
    sess = c.execute("SELECT COUNT(DISTINCT connection_session_id) FROM raw_spot_events").fetchone()[0]
    c.close()
    return {"raw": raw, "sessions": sess}


def main():
    quote_sid, manifest_path, capture_seconds = sys.argv[1], sys.argv[2], int(sys.argv[3])
    env = DL.load_ctrader_env()
    tok = token_loader.load_cached_token()
    if not tok or not tok.get("access_token"):
        print("STOP: no cached token"); return 2

    r = spot_reader.subscribe_and_capture(
        tok["access_token"], client_id=env.get("CTRADER_CLIENT_ID"),
        client_secret=env.get("CTRADER_CLIENT_SECRET"), digits=2,
        capture_seconds=capture_seconds, max_events=200000, session_id=quote_sid,
        allow_trade_scope=True)   # READ-ONLY capture may use the SCOPE_TRADE token (no trading msg built)

    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception:
        manifest = {}
    manifest["observation_end_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    manifest["quote_capture_status"] = r.get("status")
    manifest["quote_capture_finish_reason"] = r.get("finish_reason")
    manifest["quote_events_captured"] = r.get("captured")
    manifest["unsubscribe_confirmed"] = r.get("unsubscribe_confirmed")
    manifest["clean_disconnect"] = r.get("clean_disconnect")
    manifest["connection_lost"] = r.get("connection_lost")
    manifest["quote_db_end_counts"] = _counts(r.get("db_path"))
    manifest["status"] = "OBSERVATION_COMPLETE"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)
    print(f"Q4B observer finished: status={r.get('status')} captured={r.get('captured')}")
    return 0 if r.get("status") == "CAPTURE_COMPLETE" else 1


if __name__ == "__main__":
    sys.exit(main())
