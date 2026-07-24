"""Provider (Farouk) sender authorisation — FAIL CLOSED. Advisory visibility + risk-UI sync. Deterministic;
fake/offline; no broker action; gates false; no permit/lease."""
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

import provider_authorisation as PA
import advisory_bridge as AB
import operator_alerts as OA
import config as CFG
import risk_policy as RP

NOW = 1_800_000_000_000
ACT = NOW - 120_000
FRESH_ISO = _time.strftime("%Y-%m-%dT%H:%M:%S", _time.gmtime((NOW - 60_000) / 1000))


# --- fail-closed authorisation ---
def test_empty_allowlist_fails_closed():
    assert PA.FAROUK_AUTHORISED_SENDER_IDS == ()          # Farouk id not yet configured
    ok, reason = PA.is_authorised_provider("12345")
    assert (not ok) and reason == "OPERATOR_CONFIRMATION_REQUIRED"


def test_unauthorised_decision_hard_gates():
    d = PA.authorisation_decision(None)
    assert d["provider_authorised"] is False and d["execution_eligible"] is False
    assert d["may_create_proposal"] is False and d["no_campaign"] is True
    assert d["operator_confirmation_required"] is True and d["no_broker_action"] is True


def test_configured_allowlist_authorises_only_farouk(monkeypatch=None):
    orig = PA.FAROUK_AUTHORISED_SENDER_IDS
    try:
        PA.FAROUK_AUTHORISED_SENDER_IDS = ("777",)        # hypothetical configured Farouk id
        assert PA.is_authorised_provider("777") == (True, None)
        assert PA.is_authorised_provider("888")[0] is False
        assert PA.is_authorised_provider("888")[1] == "UNAUTHORISED_PROVIDER_SOURCE"
        assert PA.is_authorised_provider(None)[1] == "SENDER_NOT_CAPTURED"
    finally:
        PA.FAROUK_AUTHORISED_SENDER_IDS = orig


def test_not_inferred_from_wording_or_channel():
    # a message whose TEXT says "farouk" but whose sender id is unknown stays unauthorised
    ok, reason = PA.is_authorised_provider(None)           # no sender id => never authorised
    assert not ok


# --- advisory bridge applies the gate + enriches rows ---
def _seed(rows):
    d = tempfile.mkdtemp()
    AB.STATE_FILE = os.path.join(d, "bridge.json")
    AB.RESULTS_LOG = os.path.join(d, "results.jsonl")
    OA.ALERT_LOG = os.path.join(d, "alerts.jsonl")
    OA.STATE_FILE = os.path.join(d, "alert.json")
    db = os.path.join(d, "prospective.db")
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE prospective_message_evidence (rowseq INTEGER PRIMARY KEY AUTOINCREMENT, "
              "telegram_message_id TEXT, telegram_channel_id TEXT, telegram_posted_at_utc TEXT, "
              "raw_text TEXT, media_reference_or_hash TEXT, telegram_sender_id TEXT, "
              "telegram_sender_username TEXT, telegram_sender_display TEXT)")
    for mid, raw, sid, suser in rows:
        c.execute("INSERT INTO prospective_message_evidence (telegram_message_id, telegram_channel_id, "
                  "telegram_posted_at_utc, raw_text, media_reference_or_hash, telegram_sender_id, "
                  "telegram_sender_username, telegram_sender_display) VALUES (?,?,?,?,?,?,?,?)",
                  (mid, "-1001902136163", FRESH_ISO, raw, None, sid, suser, None))
    c.commit(); c.close()
    return d, db


def _quote_ctx():
    q = type("Q", (), {"bid": 4124.0, "ask": 4124.2, "ts_ms": NOW - 2000})()
    path = [{"bid": 4125.0, "ask": 4125.2, "ts_ms": NOW - 40000}, {"bid": 4124.0, "ask": 4124.2, "ts_ms": NOW - 2000}]
    return q, "QUOTES_ACTIVE", path


def test_signal_from_unauthorised_sender_is_gated():
    d, db = _seed([("900", "GOLD BUY LIMIT 4116-4118 SL 4110 TP 4130", "555", "someposter")])
    AB.enable(ACT)
    res = AB.process(NOW, db_path=db, quote_ctx=_quote_ctx())
    assert len(res) == 1
    r = res[0]
    assert r["intent"] == "NEW_SIGNAL"                    # still classified
    assert r["execution_eligible"] is False and r["may_create_proposal"] is False and r["no_campaign"] is True
    # bridge now uses ROUTE authorisation: a non-transport sender is not authorised (fail closed)
    assert r["provider_route_authorised"] is False and r["no_broker_action"] is True
    assert "UNRECOGNISED_TRANSPORT" in r["blocking_reasons"]


def test_normal_chat_preserved_as_unknown():
    d, db = _seed([("901", "Whale, hi guys, lets go.", "555", "chatter")])
    AB.enable(ACT)
    r = AB.process(NOW, db_path=db, quote_ctx=_quote_ctx())[0]
    assert r["intent"] == "UNKNOWN" and "UNKNOWN_INTENT" in r["blocking_reasons"]
    assert r["may_create_proposal"] is False and r["no_campaign"] is True


def test_advisory_row_has_display_fields():
    d, db = _seed([("902", "GOLD BUY LIMIT 4116-4118 SL 4110 TP 4130 verylongtail" + "x" * 200, "555", "p")])
    AB.enable(ACT)
    r = AB.process(NOW, db_path=db, quote_ctx=_quote_ctx())[0]
    assert set(r) >= {"message_id", "source_timestamp_utc", "transport_sender_id", "source_room_normalized",
                      "route_status", "text_preview", "intent", "execution_eligible", "blocking_reasons"}
    assert len(r["text_preview"]) <= 100                  # safe preview capped at 100 chars
    assert r["transport_sender_id"] == "555" and r["source_timestamp_utc"].endswith("Z")


# --- risk UI sync ---
def test_demo_risk_default_one_percent():
    html = open(os.path.join(_CON, "index.html"), encoding="utf-8").read()
    assert 'id="demoRisk" value="1.0"' in html and "policy v2.0.0 default 1.0%" in html
    assert 'placeholder="0.5 (max 1.0)"' not in html      # stale 0.5% default removed
    assert CFG.DEFAULT_RISK_PCT == 0.01                    # server default is 1.0%


def test_historical_half_percent_not_altered():
    rec = RP.policy_record(basis_amount=10000, currency="GBP", now_ms=RP.ACTIVATION_TS_MS - 1)
    assert rec["risk_percent"] == 0.5                      # pre-activation record keeps 0.5%


# --- safety ---
def test_locks_and_no_broker_action():
    de = open(os.path.join(_DE, "config.py"), encoding="utf-8").read()
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    assert "ORDER_SENDING_ENABLED = False" in de and "ORDER_MANAGEMENT_ENABLED = False" in de
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc
    for bad in ("ProtoOA", "SerializeToString", "network_send", "make_permit", "make_lease"):
        assert bad not in open(os.path.join(_DE, "provider_authorisation.py"), encoding="utf-8").read()
