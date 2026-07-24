"""Operator-alert engine tests — advisory only. Classification, sounds (result card is NEVER the urgent
new-signal sound), de-duplication, safe fields, test alert. No broker action; locks stay false."""
from __future__ import annotations
import json
import os
import sqlite3
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DE = os.path.join(_ROOT, "campaign_extractor", "demo_executor")
_CON = os.path.join(_ROOT, "campaign_extractor", "paper_loop", "console")
for p in (_ROOT, _DE, _CON):
    if p not in sys.path:
        sys.path.insert(0, p)

import config as CFG
import operator_alerts as OA

import time as _time
NOW = 1_800_000_000_000
FRESH = NOW - 60_000
STALE = NOW - 400_000
FRESH_ISO = _time.strftime("%Y-%m-%dT%H:%M:%S", _time.gmtime(FRESH / 1000))   # ISO matching the fresh ms
STALE_ISO = _time.strftime("%Y-%m-%dT%H:%M:%S", _time.gmtime(STALE / 1000))


def _tmp():
    d = tempfile.mkdtemp()
    OA.ALERT_LOG = os.path.join(d, "alerts.jsonl")
    OA.STATE_FILE = os.path.join(d, "state.json")
    return d


# ---- classification + sounds ----
def test_new_signal_candidate_urgent():
    a = OA.classify_alert("GOLD BUY LIMIT 4116-4118 SL 4110 TP 4130", posted_at_ms=FRESH, now_ms=NOW)
    assert a["type"] == "NEW SIGNAL CANDIDATE" and a["sound"] == "urgent"
    assert a["instrument"] == "XAUUSD" and a["direction"] == "BUY"


def test_result_card_never_urgent():
    a = OA.classify_alert("XAUUSD SELL 4119.44 -> 4111.85 profit 1518.00", posted_at_ms=FRESH, now_ms=NOW)
    assert a["type"] == "TRADE RESULT" and a["sound"] == "info" and a["sound"] != "urgent"


def test_cancellation_alert():
    a = OA.classify_alert("cancel gold", posted_at_ms=FRESH, now_ms=NOW)
    assert a["type"] == "CANCELLATION INSTRUCTION" and a["sound"] != "urgent"


def test_trade_update_alert():
    a = OA.classify_alert("move sl to be and take half", posted_at_ms=FRESH, now_ms=NOW)
    assert a["type"] == "TRADE UPDATE"


def test_stale_signal_blocked_no_alarm():
    a = OA.classify_alert("GOLD BUY LIMIT 4116-4118 SL 4110", posted_at_ms=STALE, now_ms=NOW)
    assert a["type"] == "STALE SIGNAL BLOCKED" and a["sound"] == "none"


def test_duplicate_ignored_no_alarm():
    a1 = OA.classify_alert("GOLD BUY LIMIT 4116-4118 SL 4110", posted_at_ms=FRESH, now_ms=NOW)
    a2 = OA.classify_alert("GOLD BUY LIMIT 4116-4118 SL 4110", posted_at_ms=FRESH, now_ms=NOW,
                           seen_semantic_keys={a1["semantic_key"]})
    assert a2["type"] == "DUPLICATE IGNORED" and a2["sound"] == "none"


def test_unknown_is_human_review():
    a = OA.classify_alert("gm traders good luck", posted_at_ms=FRESH, now_ms=NOW)
    assert a["type"] == "HUMAN REVIEW REQUIRED"


# ---- polling / dedup on a temp evidence DB ----
def _seed_db(path, rows):
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE prospective_message_evidence (rowseq INTEGER PRIMARY KEY AUTOINCREMENT, "
              "telegram_message_id TEXT, telegram_channel_id TEXT, telegram_posted_at_utc TEXT, "
              "raw_text TEXT, media_reference_or_hash TEXT)")
    for mid, posted, raw, media in rows:
        c.execute("INSERT INTO prospective_message_evidence (telegram_message_id, telegram_channel_id, "
                  "telegram_posted_at_utc, raw_text, media_reference_or_hash) VALUES (?,?,?,?,?)",
                  (mid, "-1001902136163", posted, raw, media))
    c.commit(); c.close()


def test_poll_dedups_and_does_not_realert():
    d = _tmp()
    db = os.path.join(d, "prospective.db")
    _seed_db(db, [("100", FRESH_ISO, "GOLD BUY LIMIT 4116-4118 SL 4110 TP 4130", None),
                  ("101", FRESH_ISO, "cancel gold", None)])
    first = OA.poll(NOW, db_path=db)
    assert {a["type"] for a in first} == {"NEW SIGNAL CANDIDATE", "CANCELLATION INSTRUCTION"}
    second = OA.poll(NOW, db_path=db)               # same messages -> NO re-alert
    assert second == []


def test_repost_same_message_id_no_new_alarm():
    d = _tmp()
    db = os.path.join(d, "prospective.db")
    _seed_db(db, [("200", FRESH_ISO, "GOLD BUY LIMIT 4116-4118 SL 4110", None)])
    a = OA.poll(NOW, db_path=db)
    assert len(a) == 1
    # the same message id again (a repost row) is deduped by the alert dedup key
    c = sqlite3.connect(db)
    c.execute("INSERT INTO prospective_message_evidence (telegram_message_id, telegram_channel_id, "
              "telegram_posted_at_utc, raw_text, media_reference_or_hash) VALUES ('200','-1001902136163',"
              "'2026-07-03T08:41:00','GOLD BUY LIMIT 4116-4118 SL 4110', NULL)")
    c.commit(); c.close()
    assert OA.poll(NOW, db_path=db) == []


# ---- test alert / safety ----
def test_test_alert_creates_no_intake():
    _tmp()
    a = OA.test_alert(NOW)
    assert a["type"] == "TEST ALERT" and a["message_id"] is None
    assert "no intake" in a["instruction"].lower()


def test_alerts_carry_no_secrets_or_raw_text():
    d = _tmp(); db = os.path.join(d, "p.db")
    _seed_db(db, [("300", FRESH_ISO, "GOLD BUY LIMIT 4116-4118 SL 4110 secret_token_abc", None)])
    a = OA.poll(NOW, db_path=db)[0]
    blob = json.dumps(a).lower()
    assert "secret_token_abc" not in blob and "access_token" not in blob   # raw text not echoed
    assert set(a.keys()) >= {"type", "sound", "instrument", "direction", "provider_message_time_ms",
                             "signal_age_seconds", "message_id"}


def test_toggle_enabled_state():
    _tmp()
    assert OA.set_enabled(False)["enabled"] is False
    assert OA.load_state()["enabled"] is False
    assert OA.set_enabled(True)["enabled"] is True


def test_no_broker_or_trading_in_alert_module():
    # forbid actual trading CALLS, not the docstring words describing what it does NOT do
    src = open(os.path.join(_DE, "operator_alerts.py"), encoding="utf-8").read()
    for bad in ("ProtoOA", "send_new_order", "send_management", "SerializeToString", "network_send",
                "make_lease", "make_permit", "execute_one_attempt"):
        assert bad not in src


def test_locks_false():
    assert CFG.ORDER_SENDING_ENABLED is False and CFG.ORDER_MANAGEMENT_ENABLED is False
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc
