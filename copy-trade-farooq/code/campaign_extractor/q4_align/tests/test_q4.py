"""Q4A offline tests — deterministic, synthetic quotes/signals. No connection, no LLM."""
from __future__ import annotations
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_Q4 = os.path.dirname(_HERE)
_CE = os.path.dirname(_Q4)
_ROOT = os.path.dirname(_CE)
for p in (_Q4, _CE, _ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

import kernel as K
from align_db import AlignDB


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def q(session, seq, wall_ms, mono_ns, bid, ask, bid_prov=None, ask_prov=None, flags="OK",
      sym=41, broker_ts=None):
    return {"session": session, "seq": seq, "symbol_id": sym,
            "raw_bid": int(round(bid * 100000)) if bid is not None else None,
            "raw_ask": int(round(ask * 100000)) if ask is not None else None,
            "broker_ts": broker_ts if broker_ts is not None else 5_000_000 + seq,
            "wall_ms": wall_ms, "mono_ns": mono_ns, "bid": bid, "ask": ask,
            "spread": round(ask - bid, 2) if (bid is not None and ask is not None) else None,
            "flags": flags,
            "bid_prov_seq": bid_prov if bid_prov is not None else (seq if bid is not None else None),
            "ask_prov_seq": ask_prov if ask_prov is not None else (seq if ask is not None else None)}


def base_session(name="SB", n=5, wall0=1000000, step_ms=500, bid0=4000.00, spread=0.10, ask=True):
    qs = []
    for i in range(n):
        bid = round(bid0 + 0.01 * i, 2)
        qs.append(q(name, i + 1, wall0 + i * step_ms, i * step_ms * 1_000_000, bid,
                    round(bid + spread, 2) if ask else None, broker_ts=5_000_000 + i))
    return qs


def sig(direction, low, high, received_ms=1000600, posted_ms=None, parsed_ms=None,
        human=True, asset="XAUUSD"):
    s = {"source_telegram_message_id": "45999", "source_evidence_ref": "evref", "asset": asset,
         "direction": direction, "entry_low": low, "entry_high": high,
         "telegram_posted_at": iso(posted_ms if posted_ms is not None else received_ms - 2000),
         "listener_received_at": iso(received_ms), "human_confirmed": human}
    if parsed_ms is not None:
        s["parsed_at"] = iso(parsed_ms)
    return s


# anchor 1000600 -> first_after = seq3 (wall 1001000): bid 4000.02, ask 4000.12
def test_1_buy_inside():
    r = K.align(sig("BUY", "4000.00", "4000.20"), base_session())
    assert r["delivery"]["result"] == "INSIDE_ZONE" and r["delivery"]["executable_side"] == "ASK"
    assert r["delivery"]["executable_price"] == "4000.12"
    assert r["labels"] == {"assertion": "OBSERVATION_ONLY", "fill": "NOT_A_FILL",
                           "outcome": "NOT_AN_OUTCOME"}


def test_2_buy_outside():
    r = K.align(sig("BUY", "4000.00", "4000.11"), base_session())
    assert r["delivery"]["result"] == "OUTSIDE_ZONE"       # ask 4000.12 > 4000.11


def test_3_sell_inside():
    r = K.align(sig("SELL", "4000.00", "4000.20"), base_session())
    assert r["delivery"]["result"] == "INSIDE_ZONE" and r["delivery"]["executable_side"] == "BID"
    assert r["delivery"]["executable_price"] == "4000.02"


def test_4_sell_outside():
    r = K.align(sig("SELL", "4000.05", "4000.20"), base_session())
    assert r["delivery"]["result"] == "OUTSIDE_ZONE"       # bid 4000.02 < 4000.05


def test_5_no_coverage():
    r = K.align(sig("BUY", "4000.00", "4000.20", received_ms=999000), base_session())
    assert r["delivery"]["result"] == "UNKNOWN" and r["delivery"]["reason"] == "NO_COVERAGE"


def test_6_stale_side():
    qs = base_session(step_ms=1000)                        # mono gaps 1000ms
    for x in qs:
        if x["seq"] == 3:
            x["ask_prov_seq"] = 1                          # ask 2000ms old > 1600 reject
    r = K.align(sig("BUY", "4000.00", "4000.20", received_ms=1001500), qs)
    assert r["delivery"]["result"] == "UNKNOWN" and r["delivery"]["reason"] == "STALE_ASK"


def test_7_missing_executable_side():
    qs = base_session(ask=False)                           # bid-only session -> latest_ask None
    r = K.align(sig("BUY", "4000.00", "4000.20"), qs)
    assert r["delivery"]["result"] == "UNKNOWN" and r["delivery"]["reason"] == "MISSING_ASK"


def test_8_ambiguous_signal():
    r = K.align(sig("HOLD", "4000.00", "4000.20"), base_session())
    assert r["delivery"]["reason"] == "AMBIGUOUS_DIRECTION"
    assert r["actionable"]["reason"] == "AMBIGUOUS_DIRECTION"


def test_9_between_sessions():
    a = base_session("SA", wall0=1000000)
    b = base_session("SB", wall0=1010000)
    r = K.align(sig("BUY", "4000.00", "4000.20", received_ms=1009000), a + b)
    assert r["delivery"]["result"] == "UNKNOWN" and r["delivery"]["reason"] == "NO_COVERAGE"


def test_10_parse_time_handling():
    # (a) no parsed_at -> actionable PARSE_TIME_MISSING, delivery still resolves
    r = K.align(sig("BUY", "4000.00", "4000.20"), base_session())
    assert r["delivery"]["result"] == "INSIDE_ZONE"
    assert r["actionable"]["reason"] == "PARSE_TIME_MISSING"
    # (b) parsed_at present -> actionable resolves against first quote after parsed_at
    r2 = K.align(sig("BUY", "4000.00", "4000.20", parsed_ms=1001600), base_session())  # -> seq5
    assert r2["actionable"]["result"] in ("INSIDE_ZONE", "OUTSIDE_ZONE")


def test_11_clock_anomaly():
    r = K.align(sig("BUY", "4000.00", "4000.20", received_ms=1000600, posted_ms=1005000),
                base_session())
    assert r["delivery"]["reason"] == "CLOCK_ANOMALY" and r["actionable"]["reason"] == "CLOCK_ANOMALY"


def test_12_missing_threshold_config():
    r = K.align(sig("BUY", "4000.00", "4000.20"), base_session(), config={})
    assert r["delivery"]["reason"] == "THRESHOLD_CONFIG_MISSING"
    assert r["actionable"]["reason"] == "THRESHOLD_CONFIG_MISSING"


# ---- labels always present + never an outcome claim ----
def test_labels_and_no_outcome_claim():
    r = K.align(sig("BUY", "4000.00", "4000.20"), base_session())
    blob = str(r).lower()
    assert r["labels"]["assertion"] == "OBSERVATION_ONLY"
    for banned in ("win", "loss", "profit", "\"fill\"", "slippage", "campaign_r", "\"r\":"):
        assert banned not in blob


# ---- append-only alignment DB ----
def test_align_db_append_only():
    tmp = tempfile.mkdtemp(prefix="q4db_")
    try:
        db = AlignDB(os.path.join(tmp, "data", "q4_alignment_v1.db"))
        db.insert_run(K.align(sig("BUY", "4000.00", "4000.20"), base_session()))
        assert db.count() == 1
        for s in ("UPDATE alignment_runs SET direction='X'", "DELETE FROM alignment_runs"):
            try:
                db.conn.execute(s); db.conn.commit(); assert False
            except sqlite3.IntegrityError:
                pass
        db.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---- integration: read the real quotes DB (read-only) and align in a real session ----
def test_real_quotes_db_readonly_smoke():
    qdb = os.path.join(_ROOT, "data", "ctrader_quotes_v1.db")
    if not os.path.exists(qdb):
        print("  (skipped: no real quotes DB)"); return
    import quote_source as QS
    sessions = QS.list_sessions(qdb)
    big = None
    for s in sessions:
        qs = QS.load_session_quotes(s, qdb)
        if len(qs) > 100:
            big = qs; break
    if not big:
        print("  (skipped: no large healthy session)"); return
    mid = big[len(big) // 2]
    anchor_ms = mid["wall_ms"] - 1                          # ensure a quote lands at/after anchor
    s = {"source_telegram_message_id": "REAL", "source_evidence_ref": "ref", "asset": "XAUUSD",
         "direction": "BUY", "entry_low": "1", "entry_high": "999999",
         "telegram_posted_at": iso(anchor_ms - 2000), "listener_received_at": iso(anchor_ms),
         "human_confirmed": True}
    r = K.align(s, big)
    assert r["delivery"]["result"] in ("INSIDE_ZONE", "OUTSIDE_ZONE", "UNKNOWN")
    assert r["labels"]["fill"] == "NOT_A_FILL"
