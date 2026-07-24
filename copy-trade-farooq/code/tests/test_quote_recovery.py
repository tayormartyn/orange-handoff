"""Read-only quote recovery tests — quote-health states, quote-path coverage, scope acceptance, and
the no-trading guarantee. Deterministic/offline; no broker action; locks stay false."""
from __future__ import annotations
import glob
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DE = os.path.join(_ROOT, "campaign_extractor", "demo_executor")
_Q = os.path.join(_ROOT, "campaign_extractor", "ctrader_a2", "quotes")
_A1 = os.path.join(_ROOT, "campaign_extractor")
for p in (_ROOT, _DE, _Q, _A1):
    if p not in sys.path:
        sys.path.insert(0, p)

import config as CFG
import quote_health as QH
import quote_path as QP

NOW = 1_800_000_000_000
S = 1000


def _h(**o):
    d = dict(latest_bid=4182.0, latest_ask=4182.1, latest_event_ms=NOW - 5 * S, now_ms=NOW,
             phase="subscribed", connected=True, subscribed=True, events_this_session=42)
    d.update(o)
    return QH.health(**d)


# ---- 1-3, 9-10 quote-health states ----
def test_connecting_not_active():
    assert _h(phase="connecting")["state"] == QH.CONNECTING


def test_authenticated_not_active():
    assert _h(phase="authenticated")["state"] == QH.AUTHENTICATED


def test_subscribed_without_event_not_active():
    assert _h(subscribed=True, latest_event_ms=None, events_this_session=0)["state"] == QH.SILENT
    assert _h(phase="subscribing", subscribed=False)["state"] == QH.SUBSCRIBING


def test_fresh_event_is_active():
    assert _h(latest_event_ms=NOW - 5 * S, events_this_session=42)["state"] == QH.ACTIVE


def test_stale_reports_stale():
    assert _h(latest_event_ms=NOW - 600 * S)["state"] == QH.STALE


def test_disconnected_and_market_closed_and_error():
    assert _h(connected=False)["state"] == QH.DISCONNECTED
    assert _h(market_closed=True)["state"] == QH.MARKET_CLOSED
    assert _h(last_error="CH_SOME")["state"] == QH.ERROR


# ---- 7-8 malformed / bid>ask ----
def test_malformed_and_inverted_quote_not_active():
    assert QH.valid_quote(None, 4182.1) is False
    assert QH.valid_quote(4183.0, 4182.0) is False        # bid > ask
    assert QH.valid_quote(4182.0, 4182.1) is True
    # an inverted latest quote cannot be ACTIVE
    assert _h(latest_bid=4183.0, latest_ask=4182.0)["state"] == QH.SILENT


# ---- 13 out-of-order ----
def test_out_of_order_detected_by_coverage_order():
    q = [{"bid": 1, "ask": 2, "ts_ms": NOW}, {"bid": 1, "ask": 2, "ts_ms": NOW - 5 * S}]
    cov = QP.coverage(q, start_ms=NOW - 10 * S, end_ms=NOW)
    assert cov["first_quote_ms"] < cov["last_quote_ms"]   # sorted chronologically regardless of arrival


# ---- 14-16 quote-path coverage ----
def test_isolated_quote_is_not_coverage():
    cov = QP.coverage([{"bid": 4180, "ask": 4180.1, "ts_ms": NOW - 30 * S}], start_ms=NOW - 300 * S, end_ms=NOW)
    assert cov["coverage_available"] is False and cov["reason"] == "ISOLATED_QUOTE_NOT_COVERAGE"


def test_quote_path_gap_detected():
    q = [{"bid": 4180, "ask": 4180.1, "ts_ms": NOW - 300 * S},
         {"bid": 4181, "ask": 4181.1, "ts_ms": NOW - 10 * S}]   # 290s gap
    cov = QP.coverage(q, start_ms=NOW - 300 * S, end_ms=NOW)
    assert cov["coverage_available"] is False and cov["max_gap_ms"] > QP.MAX_COVERAGE_GAP_MS


def test_continuous_coverage_ok():
    q = [{"bid": 4180, "ask": 4180.1, "ts_ms": NOW - 20 * S},
         {"bid": 4180.5, "ask": 4180.6, "ts_ms": NOW - 10 * S},
         {"bid": 4181, "ask": 4181.1, "ts_ms": NOW - 2 * S}]
    cov = QP.coverage(q, start_ms=NOW - 25 * S, end_ms=NOW)
    assert cov["coverage_available"] is True and cov["points"] == 3


def test_zone_touch_traverse_consume_stored_quotes():
    q = [{"bid": 4110, "ask": 4110.1, "ts_ms": NOW - 40 * S},   # below
         {"bid": 4117, "ask": 4117.1, "ts_ms": NOW - 25 * S},   # inside 4116-4118
         {"bid": 4120, "ask": 4120.1, "ts_ms": NOW - 5 * S}]    # above
    za = QP.zone_analysis(q, direction="BUY", entry_low=4116, entry_high=4118,
                          start_ms=NOW - 45 * S, end_ms=NOW)
    assert za["zone_touched"] is True and za["zone_traversed"] is True and za["entry_passed"] is True


def test_zone_analysis_blocks_without_coverage():
    za = QP.zone_analysis([{"bid": 4117, "ask": 4117.1, "ts_ms": NOW}], direction="BUY",
                          entry_low=4116, entry_high=4118, start_ms=NOW - 300 * S, end_ms=NOW)
    assert za["blocker"] == "QUOTE_PATH_UNVERIFIED" and za["zone_touched"] is None


# ---- 4-6 scope acceptance (read-only observer may use SCOPE_TRADE) ----
def test_scope_trade_accepted_only_for_readonly():
    from ctrader_a1 import scope_validator as SV
    assert SV.returned_scope_is_view_only("SCOPE_VIEW") is True
    assert SV.returned_scope_is_view_only("SCOPE_TRADE") is False   # strict view-only rejects it
    # the observer's read-only admissibility: view-only OR (allow_trade_scope and SCOPE_TRADE)
    def admit(scope, allow_trade):
        return SV.returned_scope_is_view_only(scope) or (allow_trade and scope == "SCOPE_TRADE")
    assert admit("SCOPE_TRADE", True) is True and admit("SCOPE_TRADE", False) is False
    assert admit("SCOPE_UNKNOWN", True) is False


# ---- 19-21 no trading / locks ----
def test_no_trading_constructor_in_quote_modules():
    for m in ("quote_health.py", "quote_path.py"):
        src = open(os.path.join(_DE, m), encoding="utf-8").read()
        for bad in ("ProtoOA", "send_new_order", "send_management", "SerializeToString"):
            assert bad not in src
    # spot_reader may build ONLY read-only spot subscribe/unsubscribe — never an order/amend/close/cancel
    sr = open(os.path.join(_Q, "spot_reader.py"), encoding="utf-8").read()
    for bad in ("ProtoOANewOrderReq", "ProtoOAAmendPositionSLTPReq", "ProtoOAClosePositionReq",
                "ProtoOACancelOrderReq"):
        assert bad not in sr
    assert "ProtoOASubscribeSpotsReq" in sr                 # the read-only subscription IS present


def test_locks_all_false():
    assert CFG.ORDER_SENDING_ENABLED is False and CFG.ORDER_MANAGEMENT_ENABLED is False
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc
