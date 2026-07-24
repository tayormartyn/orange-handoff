"""Q1 offline tests — mocked spot events + temp DB. No connection. Covers all 13 requirements."""
from __future__ import annotations
import importlib.util
import os
import shutil
import sqlite3
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_QUOTES = os.path.dirname(_HERE)
_A2 = os.path.dirname(_QUOTES)
_CE = os.path.dirname(_A2)
_ROOT = os.path.dirname(_CE)
for p in (_QUOTES, _A2, _CE, _ROOT):
    if p not in sys.path:
        sys.path.insert(0, p)

from quote_db import QuoteDB
from normaliser import SpotNormaliser
import spot_reader as SR


# ---- mock spot event whose type name matches the real protobuf class ----
class _SpotEvent:
    pass
_SpotEvent.__name__ = "ProtoOASpotEvent"


def _spot(bid=None, ask=None, ts=None, symbol_id=41, payload_type=2131):
    e = _SpotEvent()
    e.symbolId = symbol_id
    e.payloadType = payload_type
    if bid is not None:
        e.bid = bid
    if ask is not None:
        e.ask = ask
    if ts is not None:
        e.timestamp = ts
    return e


class _WrongMsg:
    pass
_WrongMsg.__name__ = "ProtoOATraderRes"


def _fresh_db():
    tmp = tempfile.mkdtemp(prefix="q1_")
    return tmp, QuoteDB(os.path.join(tmp, "data", "ctrader_quotes_v1.db"))


def _ingest(db, norm, ev, seq, ns=1000):
    return SR.ingest_spot_message(ev, session_id="S1", seq=seq, normaliser=norm, db=db,
                                  masked_account_id="****8849", now_utc="2026-07-01T00:00:00Z",
                                  monotonic_ns=ns)


# ===================================================== (2) price conversion
def test_price_conversion():
    n = SpotNormaliser(digits=2)
    rec = n.ingest(201534000, 201536000, "S1", 1, 1000)
    assert rec["norm_bid"] == 2015.34 and rec["norm_ask"] == 2015.36
    assert rec["spread"] == 0.02 and rec["flags"] == "OK"


# ===================================================== (3) bid-only  (4) ask-only
def test_bid_only_and_ask_only():
    n = SpotNormaliser(digits=2)
    b = n.ingest(201540000, None, "S1", 1, 1000)
    assert b["norm_bid"] == 2015.40 and b["norm_ask"] is None and "BID_ONLY" in b["flags"]
    assert b["spread"] is None                                   # only one side known
    a = SpotNormaliser(digits=2).ingest(None, 201560000, "S1", 1, 1000)
    assert a["norm_ask"] == 2015.60 and a["norm_bid"] is None and "ASK_ONLY" in a["flags"]


# ===================================================== (5) paired quote + provenance
def test_paired_quote_with_provenance():
    n = SpotNormaliser(digits=2)
    n.ingest(201540000, None, "S1", 1, 1000)                    # bid from seq 1
    rec = n.ingest(None, 201560000, "S1", 2, 1100)              # ask from seq 2
    assert rec["latest_bid"] == 2015.40 and rec["latest_ask"] == 2015.60
    assert rec["bid_provenance_seq"] == 1 and rec["ask_provenance_seq"] == 2      # which event each
    assert rec["bid_provenance_session"] == "S1" and rec["ask_provenance_session"] == "S1"
    assert rec["spread"] == 0.20


# ===================================================== (6) no missing value becomes zero
def test_no_missing_becomes_zero():
    n = SpotNormaliser(digits=2)
    rec = n.ingest(201540000, None, "S1", 1, 1000)
    assert rec["norm_ask"] is None and rec["latest_ask"] is None      # not 0
    tmp, db = _fresh_db()
    try:
        _ingest(db, SpotNormaliser(digits=2), _spot(bid=201540000), 1)
        row = db.fetch_normalised("S1", 1)
        assert row["norm_ask"] is None and row["latest_ask"] is None and row["raw_ask"] is None
    finally:
        db.close(); shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== (7) negative spread not silent
def test_negative_spread_flagged():
    n = SpotNormaliser(digits=2)
    n.ingest(201540000, None, "S1", 1, 1000)                    # bid 2015.40
    rec = n.ingest(None, 201530000, "S1", 2, 1100)              # ask 2015.30 -> spread -0.10
    assert rec["spread"] == -0.10 and "NEGATIVE_SPREAD" in rec["flags"]


# ===================================================== malformed negative raw
def test_malformed_negative_raw_not_adopted():
    n = SpotNormaliser(digits=2)
    rec = n.ingest(-5, None, "S1", 1, 1000)
    assert "MALFORMED_BID" in rec["flags"] and rec["norm_bid"] is None and rec["latest_bid"] is None


# ===================================================== (9) broker/local timestamps
def test_timestamps_stored():
    tmp, db = _fresh_db()
    try:
        _ingest(db, SpotNormaliser(digits=2), _spot(bid=201540000, ask=201560000, ts=1719835200000), 1)
        r = db.conn.execute("SELECT broker_timestamp, local_received_utc, "
                            "local_received_monotonic_ns, persisted_utc FROM raw_spot_events").fetchone()
        assert r[0] == 1719835200000 and r[1] == "2026-07-01T00:00:00Z" and r[2] == 1000 and r[3]
    finally:
        db.close(); shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== stale side blocks spread
def test_stale_blocks_spread():
    n = SpotNormaliser(digits=2, stale_after_ns=1000)
    n.ingest(201540000, None, "S1", 1, 0)                       # bid at ns=0
    rec = n.ingest(None, 201560000, "S1", 2, 5000)              # ask at ns=5000 -> bid stale
    assert rec["spread"] is None and "STALE" in rec["flags"]


# ===================================================== (8) idempotent persistence
def test_idempotent_persistence():
    tmp, db = _fresh_db()
    try:
        n = SpotNormaliser(digits=2)
        r1 = _ingest(db, n, _spot(bid=201540000, ask=201560000), 7)
        r2 = _ingest(db, SpotNormaliser(digits=2), _spot(bid=201540000, ask=201560000), 7)  # same seq
        assert r1["inserted_raw"] is True and r2["inserted_raw"] is False
        assert db.count_raw() == 1 and db.count_normalised() == 1
    finally:
        db.close(); shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== append-only immutability
def test_append_only_triggers():
    tmp, db = _fresh_db()
    try:
        _ingest(db, SpotNormaliser(digits=2), _spot(bid=201540000), 1)
        for sql in ("UPDATE raw_spot_events SET raw_bid=0",
                    "DELETE FROM raw_spot_events",
                    "UPDATE normalised_quotes SET spread=0",
                    "DELETE FROM normalised_quotes"):
            try:
                db.conn.execute(sql); db.conn.commit(); assert False, f"mutation allowed: {sql}"
            except sqlite3.IntegrityError:
                pass
    finally:
        db.close(); shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== (10) unexpected payload fails closed
def test_unexpected_payload_fails_closed():
    tmp, db = _fresh_db()
    try:
        out = _ingest(db, SpotNormaliser(digits=2), _WrongMsg(), 1)
        assert out["accepted"] is False and out["reason"].startswith("UNEXPECTED_PAYLOAD")
        assert db.count_raw() == 0 and db.count_normalised() == 0     # nothing persisted
    finally:
        db.close(); shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== incomplete event not discarded
def test_incomplete_event_not_discarded():
    tmp, db = _fresh_db()
    try:
        out = _ingest(db, SpotNormaliser(digits=2), _spot(), 1)       # no bid/ask
        assert out["accepted"] is True and "INCOMPLETE_NO_SIDES" in out["flags"]
        assert db.count_raw() == 1 and db.count_normalised() == 1     # recorded, not dropped
    finally:
        db.close(); shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== (11) error/429 stop, zero retry
def test_error_and_429_raise_and_no_retry_loop():
    import live_transport as LT
    from errors import RateLimited429, BrokerError
    from types import SimpleNamespace
    try:
        LT.raise_if_error(SimpleNamespace(errorCode="RATE_LIMIT_EXCEEDED"), "SPOT"); assert False
    except RateLimited429:
        pass

    class _Err:
        pass
    _Err.__name__ = "ProtoOAErrorRes"
    e = _Err(); e.errorCode = "SOME_ERROR"
    try:
        LT.raise_if_error(e, "SPOT"); assert False
    except BrokerError:
        pass
    # structural: exactly one reactor.run(), no retry loop, unsubscribe present
    src = open(os.path.join(_QUOTES, "spot_reader.py"), encoding="utf-8").read()
    assert src.count("reactor.run()") == 1
    for banned in ("while True", "for _retry", "reconnect"):
        assert banned not in src


# ===================================================== (12) unsubscribe + clean-disconnect wiring
def test_unsubscribe_and_disconnect_wiring():
    src = open(os.path.join(_QUOTES, "spot_reader.py"), encoding="utf-8").read()
    assert "build_unsubscribe_req" in src and "reactor.stop()" in src
    assert "ProtoOAUnsubscribeSpotsReq" in src and "setDisconnectedCallback" in src


# ===================================================== (13) no order/trading code or import
def test_no_order_or_trading_code():
    from broker_readonly.source_scan import scan_no_order_code
    assert scan_no_order_code([_QUOTES]) == []
    # forbidden tokens built from fragments so the scanner doesn't flag THIS test as a violation
    banned = ("New" + "Order", "ProtoOANew" + "OrderReq", "Close" + "Position", "Amend" + "Order",
              "Cancel" + "Order", "place_" + "order", "Subscribe" + "Trade", "Execution" + "Event")
    for name in ("spot_reader.py", "normaliser.py", "quote_db.py", "__init__.py"):
        src = open(os.path.join(_QUOTES, name), encoding="utf-8").read()
        for tok in banned:
            assert tok not in src


# ===================================================== (1) wrapped ProtoOASpotEvent extraction (venv)
def test_wrapped_spot_event_extraction_venv_only():
    if importlib.util.find_spec("ctrader_open_api") is None:
        print("  (skipped: run under .venv-ctrader)")
        return
    import ctrader_open_api.messages.OpenApiMessages_pb2 as MSG
    import ctrader_open_api.messages.OpenApiCommonMessages_pb2 as COM
    ev = MSG.ProtoOASpotEvent()
    ev.ctidTraderAccountId = 999
    ev.symbolId = 41
    ev.bid = 201534000
    ev.ask = 201536000
    ev.timestamp = 1719835200000
    env = COM.ProtoMessage(); env.payloadType = ev.payloadType; env.payload = ev.SerializeToString()
    assert type(env).__name__ == "ProtoMessage"
    tmp, db = _fresh_db()
    try:
        out = SR.ingest_spot_message(env, session_id="S1", seq=1, normaliser=SpotNormaliser(digits=2),
                                     db=db, masked_account_id="****8849",
                                     now_utc="2026-07-01T00:00:00Z", monotonic_ns=1000)
        assert out["accepted"] is True and out["spread"] == 0.02
        row = db.fetch_normalised("S1", 1)
        assert row["norm_bid"] == 2015.34 and row["norm_ask"] == 2015.36
        raw = db.conn.execute("SELECT raw_bid, raw_ask, broker_timestamp FROM raw_spot_events").fetchone()
        assert raw == (201534000, 201536000, 1719835200000)
    finally:
        db.close(); shutil.rmtree(tmp, ignore_errors=True)


# ===================================================== subscribe/unsubscribe builders (venv)
def test_spot_request_builders_venv_only():
    if importlib.util.find_spec("ctrader_open_api") is None:
        print("  (skipped: run under .venv-ctrader)")
        return
    sub = SR.build_subscribe_req(12345, 41)
    assert sub.ctidTraderAccountId == 12345 and list(sub.symbolId) == [41]
    assert sub.subscribeToSpotTimestamp is True
    uns = SR.build_unsubscribe_req(12345, 41)
    assert uns.ctidTraderAccountId == 12345 and list(uns.symbolId) == [41]
