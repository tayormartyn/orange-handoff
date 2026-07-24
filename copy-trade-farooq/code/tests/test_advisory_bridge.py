"""End-to-end advisory-bridge verification (fixture, not a broker order, not a replayed historical
message). Proves: new intake -> raw evidence -> ONE interpretation job -> contract 1.0.0 -> quote store
consulted -> advisory result stored -> exactly ONE alert; and full idempotency. No broker action."""
from __future__ import annotations
import json
import os
import sqlite3
import sys
import tempfile
import time as _time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DE = os.path.join(_ROOT, "campaign_extractor", "demo_executor")
_CON = os.path.join(_ROOT, "campaign_extractor", "paper_loop", "console")
for p in (_ROOT, _DE, _CON):
    if p not in sys.path:
        sys.path.insert(0, p)

import config as CFG
import advisory_bridge as AB
import operator_alerts as OA

NOW = 1_800_000_000_000
ACTIVATION = NOW - 120_000
FRESH = NOW - 60_000
FRESH_ISO = _time.strftime("%Y-%m-%dT%H:%M:%S", _time.gmtime(FRESH / 1000))
OLD_ISO = _time.strftime("%Y-%m-%dT%H:%M:%S", _time.gmtime((NOW - 10_000_000) / 1000))  # historical


def _quote_ctx():
    # BUY LIMIT entry 4116-4118 below market 4124; path stays above zone (untouched); QUOTES_ACTIVE
    q = type("Q", (), {"bid": 4124.0, "ask": 4124.2, "ts_ms": NOW - 2000})()
    path = [{"bid": 4125.0, "ask": 4125.2, "ts_ms": NOW - 50_000},
            {"bid": 4124.5, "ask": 4124.7, "ts_ms": NOW - 25_000},
            {"bid": 4124.0, "ask": 4124.2, "ts_ms": NOW - 2000}]
    return q, "QUOTES_ACTIVE", path


def _tmp(rows):
    d = tempfile.mkdtemp()
    AB.STATE_FILE = os.path.join(d, "bridge_state.json")
    AB.RESULTS_LOG = os.path.join(d, "results.jsonl")
    OA.ALERT_LOG = os.path.join(d, "alerts.jsonl")
    OA.STATE_FILE = os.path.join(d, "alert_state.json")
    db = os.path.join(d, "prospective.db")
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE prospective_message_evidence (rowseq INTEGER PRIMARY KEY AUTOINCREMENT, "
              "telegram_message_id TEXT, telegram_channel_id TEXT, telegram_posted_at_utc TEXT, "
              "raw_text TEXT, media_reference_or_hash TEXT)")
    for mid, posted, raw, media in rows:
        c.execute("INSERT INTO prospective_message_evidence (telegram_message_id, telegram_channel_id, "
                  "telegram_posted_at_utc, raw_text, media_reference_or_hash) VALUES (?,?,?,?,?)",
                  (mid, "-1001902136163", posted, raw, media))
    c.commit(); c.close()
    return d, db


def _evidence_count(db):
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    n = c.execute("SELECT COUNT(*) FROM prospective_message_evidence").fetchone()[0]
    c.close()
    return n


def test_end_to_end_sequence():
    d, db = _tmp([("500", FRESH_ISO, "GOLD BUY LIMIT 4116-4118 SL 4110 TP 4130", None)])
    AB.enable(ACTIVATION)                                 # bridge enabled; activation before the message
    ev_before = _evidence_count(db)
    results = AB.process(NOW, db_path=db, quote_ctx=_quote_ctx())
    # exactly one interpretation job/result
    assert len(results) == 1
    r = results[0]
    assert r["contract_version"] == "1.0.0" and r["intent"] == "NEW_SIGNAL"
    assert r["quote_consulted"] is True and r["quote_health_state"] == "QUOTES_ACTIVE"
    assert r["instrument"] == "XAUUSD" and r["direction"] == "BUY"
    # raw evidence unchanged (bridge is read-only over evidence)
    assert _evidence_count(db) == ev_before
    # console can fetch the stored advisory result
    assert AB.get_results(0)[0]["job_id"] == r["job_id"]
    # exactly one alert produced
    alerts = [json.loads(l) for l in open(OA.ALERT_LOG, encoding="utf-8") if l.strip()]
    assert len(alerts) == 1 and alerts[0]["type"] == "NEW SIGNAL CANDIDATE"


def test_second_delivery_is_idempotent():
    d, db = _tmp([("600", FRESH_ISO, "GOLD BUY LIMIT 4116-4118 SL 4110 TP 4130", None)])
    AB.enable(ACTIVATION)
    first = AB.process(NOW, db_path=db, quote_ctx=_quote_ctx())
    assert len(first) == 1
    second = AB.process(NOW, db_path=db, quote_ctx=_quote_ctx())   # same message again
    assert second == []                                  # no duplicate job/result
    results = AB.get_results(0)
    assert len(results) == 1                              # no duplicate stored result
    alerts = [json.loads(l) for l in open(OA.ALERT_LOG, encoding="utf-8") if l.strip()]
    assert len(alerts) == 1                               # no duplicate alert


def test_no_historical_replay_before_activation():
    d, db = _tmp([("1", OLD_ISO, "GOLD BUY LIMIT 4116-4118 SL 4110", None),   # historical (pre-activation)
                  ("700", FRESH_ISO, "GOLD BUY LIMIT 4120-4122 SL 4114 TP 4135", None)])  # new
    AB.enable(ACTIVATION)
    results = AB.process(NOW, db_path=db, quote_ctx=_quote_ctx())
    # only the post-activation message becomes a job; the historical one is NOT replayed
    assert len(results) == 1 and results[0]["message_id"] == "700"


def test_disabled_bridge_does_nothing():
    d, db = _tmp([("800", FRESH_ISO, "GOLD BUY LIMIT 4116-4118 SL 4110", None)])
    st = AB.load_state(); st["enabled"] = False; AB.save_state(st)
    assert AB.process(NOW, db_path=db, quote_ctx=_quote_ctx()) == []


def test_status_reports_enabled_and_activation():
    _tmp([])
    AB.enable(ACTIVATION)
    s = AB.status()
    assert s["ADVISORY_HANDOFF_ENABLED"] is True and s["activation_ts_ms"] == ACTIVATION


def test_no_broker_or_execution_in_bridge():
    src = open(os.path.join(_DE, "advisory_bridge.py"), encoding="utf-8").read()
    for bad in ("ProtoOA", "send_new_order", "send_management", "SerializeToString", "network_send",
                "make_permit", "make_lease", "module_b_parser", "import module_b"):
        assert bad not in src
    assert CFG.ORDER_SENDING_ENABLED is False and CFG.ORDER_MANAGEMENT_ENABLED is False
