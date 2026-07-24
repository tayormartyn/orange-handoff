"""
Brick 4 — broker observation database tests. Offline, mock/replay only.

Hard-proves: append-only (attempt UPDATE/DELETE -> rejected), secret-field rejection,
crossed/stale quarantined-never-admissible, missing bid/ask -> NULL, no auto-fill,
no mutation of campaign/Telegram evidence, deterministic replay.
"""
import hashlib
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from broker_readonly.observation_db import ObservationDB, TABLES
from broker_readonly.quotes import RawQuote, QuoteContext
from broker_readonly.secrets import SecretLeak
from broker_readonly.source_scan import scan_no_order_code, scan_secret_leaks

PKG = os.path.join(ROOT, "broker_readonly")
BT = "2026-06-29T10:00:00+00:00"
LT = "2026-06-29T10:00:00.100+00:00"


def _db():
    return ObservationDB(":memory:")


def Q(bid, ask, bt=BT, lt=LT, sym="XAUUSD"):
    return RawQuote(symbol=sym, bid=bid, ask=ask, broker_ts=bt, local_ts=lt)


def _seed_quotes(db):
    seq = [Q(2000.0, 2000.5), Q(2000.0, 2000.5),
           Q(2001.0, 2001.5, bt="2026-06-29T10:00:01+00:00", lt="2026-06-29T10:00:01.100+00:00")]
    prev = None
    for q in seq:
        db.append_quote_observation(q, source_environment="demo", prev=prev)
        if q.bid and q.ask:
            prev = q


# ---- schema
def test_schema_creation_reproducible():
    a, b = _db(), _db()
    assert a.table_names() == b.table_names() == sorted(TABLES)


def test_only_six_broker_tables_no_campaign_or_telegram():
    db = _db()
    names = db.table_names()
    assert names == sorted(TABLES)
    assert not any("campaign" in n or "telegram" in n or "prospective" in n for n in names)


# ---- append-only (engine-level), proven by attempting update + delete
def test_append_only_update_rejected():
    db = _db()
    db.append_connection_event(environment="demo", connection_state="READ_ONLY_READY",
                               reason_code="ok")
    try:
        db.con.execute("UPDATE broker_connection_events SET reason_code='tampered'")
        db.con.commit()
        assert False, "update should have been rejected"
    except sqlite3.Error as e:
        assert "append-only" in str(e).lower()
    # row unchanged
    assert db.con.execute("SELECT reason_code FROM broker_connection_events").fetchone()[0] == "ok"


def test_append_only_delete_rejected():
    db = _db()
    db.append_auth_event(auth_state="READ_ONLY_READY", reason_code="ok")
    try:
        db.con.execute("DELETE FROM broker_auth_events")
        db.con.commit()
        assert False, "delete should have been rejected"
    except sqlite3.Error as e:
        assert "append-only" in str(e).lower()
    assert db.count("broker_auth_events") == 1


def test_no_update_or_delete_methods_exposed():
    members = dir(ObservationDB)
    assert not any(("update" in m or "delete" in m or "drop" in m) for m in members)


# ---- secret-field rejection
def test_secret_field_persist_rejected():
    db = _db()
    for bad in ({"auth_state": "x", "access_token": "S"}, {"environment": "demo", "client_secret": "S"},
                {"refresh_token": "S"}):
        try:
            db._append("broker_auth_events", bad)
            assert False, "secret field should be rejected"
        except SecretLeak:
            pass


def test_normal_auth_event_persists():
    db = _db()
    db.append_auth_event(auth_state="APPLICATION_AUTHENTICATED", reason_code="ok")
    assert db.count("broker_auth_events") == 1


# ---- quote integrity
def test_crossed_quote_quarantined_never_admissible():
    db = _db()
    db.append_quote_observation(Q(2001.0, 2000.0), source_environment="demo")
    row = db.con.execute("SELECT primary_quote_status, quarantine_flag, spread "
                         "FROM broker_quote_observations").fetchone()
    assert row[0] == "INVALID_CROSSED_MARKET" and row[1] == 1
    assert row[0] != "COMPLETE_ADMISSIBLE" and row[2] is None    # no spread for crossed


def test_stale_quote_quarantined_never_admissible():
    db = _db()
    db.append_quote_observation(Q(2000.0, 2000.5, lt="2026-06-29T10:00:10+00:00"),
                                source_environment="demo")    # 10s age > 5s
    row = db.con.execute("SELECT primary_quote_status, stale_flag, quarantine_flag "
                         "FROM broker_quote_observations").fetchone()
    assert row[0] == "STALE" and row[1] == 1 and row[2] == 1


def test_missing_bid_or_ask_stored_as_null():
    db = _db()
    db.append_quote_observation(Q(2000.0, None), source_environment="demo")    # ask missing
    db.append_quote_observation(Q(None, 2000.5), source_environment="demo")    # bid missing
    rows = db.con.execute("SELECT primary_quote_status, bid, ask "
                          "FROM broker_quote_observations ORDER BY rowseq").fetchall()
    assert rows[0][0] == "BID_ONLY" and rows[0][2] is None     # ask NULL, not fabricated
    assert rows[1][0] == "ASK_ONLY" and rows[1][1] is None     # bid NULL


def test_complete_admissible_stored():
    db = _db()
    st = db.append_quote_observation(Q(2000.0, 2000.5), source_environment="demo")
    assert st == "COMPLETE_ADMISSIBLE"
    row = db.con.execute("SELECT spread, quarantine_flag FROM broker_quote_observations").fetchone()
    assert abs(row[0] - 0.5) < 1e-9 and row[1] == 0


def test_out_of_order_flagged_and_duplicate_identifiable():
    db = _db()
    p = Q(2000.0, 2000.5, bt="2026-06-29T10:00:05+00:00")
    db.append_quote_observation(Q(2000.0, 2000.5, bt="2026-06-29T10:00:00+00:00"),
                                source_environment="demo", prev=p)
    db.append_quote_observation(Q(2000.0, 2000.5), source_environment="demo", prev=Q(2000.0, 2000.5))
    rows = db.con.execute("SELECT primary_quote_status, out_of_order_flag, duplicate_flag "
                          "FROM broker_quote_observations ORDER BY rowseq").fetchall()
    assert rows[0][0] == "OUT_OF_ORDER" and rows[0][1] == 1
    assert rows[1][0] == "DUPLICATE" and rows[1][2] == 1


def test_malformed_quote_value_quarantined():
    db = _db()
    db.append_quote_observation(Q("not-a-number", 2000.5), source_environment="demo")
    row = db.con.execute("SELECT primary_quote_status, bid, quarantine_flag "
                         "FROM broker_quote_observations").fetchone()
    assert row[0] == "INVALID_VALUE" and row[1] is None and row[2] == 1


# ---- environment required on broker observations
def test_environment_required_on_quote():
    db = _db()
    try:
        db.append_quote_observation(Q(2000.0, 2000.5), source_environment="")
        assert False
    except ValueError:
        pass


def test_environment_recorded_on_account():
    db = _db()
    db.append_account_observation(account_environment="demo", currency="GBP", balance=10000)
    assert db.con.execute("SELECT account_environment FROM broker_account_observations").fetchone()[0] == "demo"


# ---- no auto-fill, no mutation of campaign/Telegram evidence
def test_quote_append_creates_no_fill_or_position():
    db = _db()
    before = {t: db.count(t) for t in TABLES}
    db.append_quote_observation(Q(2000.0, 2000.5), source_environment="demo")
    after = {t: db.count(t) for t in TABLES}
    # ONLY the quote table grew; positions/connections/accounts/etc. untouched (no auto-fill)
    assert after["broker_quote_observations"] == before["broker_quote_observations"] + 1
    for t in TABLES:
        if t != "broker_quote_observations":
            assert after[t] == before[t]


def test_observation_db_does_not_touch_campaign_or_telegram_evidence():
    # hash a locked campaign truth before and after broker appends -> unchanged
    def truth_hash():
        fx = json.load(open(os.path.join(ROOT, "phase0", "fixtures", "fixture_2026-06-17.json"),
                            encoding="utf-8"))
        pl = {"authored_campaigns": fx["authored_campaigns"],
              "expected_truth": {m["message_id"]: m["expected_truth"] for m in fx["messages"]}}
        return hashlib.sha256(json.dumps(pl, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    before = truth_hash()
    db = _db()
    db.append_quote_observation(Q(2000.0, 2000.5), source_environment="demo")
    db.append_position_observation(safe_position_id="hashedP", symbol="XAUUSD", direction="BUY",
                                   volume=1, source_environment="demo")
    assert truth_hash() == before == "c8b1c3ebfb46441e113570f798e951ffce35829c4e4b50a052f9c2b8eba20339"


def test_position_observation_is_read_only_evidence():
    db = _db()
    db.append_position_observation(safe_position_id="P", symbol="XAUUSD", direction="BUY",
                                   volume=1, position_status="OPEN", source_environment="demo")
    assert db.count("broker_position_observations") == 1
    # no scoring/fill side effects: nothing else written
    assert sum(db.count(t) for t in TABLES) == 1


# ---- deterministic replay
def test_deterministic_replay_identical_logical_hash():
    a, b = _db(), _db()
    _seed_quotes(a)
    _seed_quotes(b)
    assert a.logical_hash() == b.logical_hash()


# ---- scans remain green (not loosened) with observation_db in the package
def test_no_order_code_scan_green():
    assert scan_no_order_code([PKG]) == []


def test_secret_leak_scan_green():
    assert scan_secret_leaks([PKG]) == []
