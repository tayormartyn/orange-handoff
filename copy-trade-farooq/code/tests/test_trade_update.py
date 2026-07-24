"""TRADE_UPDATE management-proposal tests — parsing, position matching, breakeven VWAP, volume
normalization, composite plans, dry-run + audit. ALL trading mocked; NO position modified/closed."""
from __future__ import annotations
import glob
import os
import sqlite3
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DE = os.path.join(_ROOT, "campaign_extractor", "demo_executor")
for p in (_ROOT, _DE):
    if p not in sys.path:
        sys.path.insert(0, p)

import config as CFG
import update_parser
import position_matcher as PM
import management_planner as MP
import update_plans as UP
from audit_db import AuditDB
from models import BrokerPosition, Quote, AccountSnapshot

NOW = 1_800_000_000_000
UNITS_PER_LOT = 10000
MINU, STEPU = 100, 100


def acct(**o):
    d = dict(account_id=4257941, is_live=False, balance=10000.0, currency="GBP", trade_scope="trade",
             environment="DEMO")
    d.update(o)
    return AccountSnapshot(**d)


def pos(position_id=1, label="sig-1", direction="SELL", volume_units=300, price=4119.44,
        stop_loss=4140.0, take_profit=None, open_time_ms=NOW):
    return BrokerPosition(position_id, label, "XAUUSD", direction, volume_units, price, stop_loss,
                          take_profit, open_time_ms)


def quote(bid=4111.85, ask=4111.96, ts_ms=NOW):
    return Quote(bid, ask, ts_ms)


def _run(fn):
    tmp = tempfile.mkdtemp(prefix="tu_")
    try:
        return fn(tmp)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


# ---- parsing ----
def test_parse_composite_breakeven_plus_partial():
    p = update_parser.parse_update("Take TP1 and move SL to breakeven")
    assert p["is_composite"] and p["primary"] == "COMPOSITE_MANAGEMENT_PLAN"
    kinds = {i["intent"] for i in p["intents"]}
    assert "MOVE_SL_TO_BREAKEVEN" in kinds and "PARTIAL_CLOSE" in kinds


def test_parse_ambiguous():
    assert update_parser.parse_update("gm team lets go")["primary"] == "AMBIGUOUS_UPDATE"


def test_parse_literal_lot_captured():
    assert update_parser.parse_update("take 1 lot out")["provider_literal_lots"] == 1.0


# ---- position matching ----
def test_symbol_only_matching_rejected():
    m = PM.match_position(signal_id="sig-1", account_id=4257941, symbol="XAUUSD", direction="BUY",
                          positions=[pos(label="other", direction="SELL")], now_ms=NOW)
    assert m.status in ("NO_MATCH", "AMBIGUOUS") and m.matched is None


def test_confirmed_match_by_label():
    m = PM.match_position(signal_id="sig-1", account_id=4257941, symbol="XAUUSD", direction="SELL",
                          positions=[pos(label="order-sig-1-x")], now_ms=NOW)
    assert m.status == "CONFIRMED" and m.matched is not None


def test_ambiguous_multiple_weak_blocked():
    ps = [pos(1, label="none", direction="SELL"), pos(2, label="none", direction="SELL")]
    m = PM.match_position(signal_id="sig-1", account_id=4257941, symbol="XAUUSD", direction="SELL",
                          positions=ps, now_ms=NOW)
    assert m.status == "AMBIGUOUS" and m.matched is None


def test_hedged_multileg_deterministic():
    ps = [pos(1, label="sig-1", price=4119.0), pos(2, label="sig-1", price=4123.0)]
    m = PM.match_position(signal_id="sig-1", account_id=4257941, symbol="XAUUSD", direction="SELL",
                          positions=ps, now_ms=NOW)
    assert m.status == "MULTI_LEG" and {c.position_id for c in m.candidates} == {1, 2}


def test_netted_close_worst_ambiguous():
    sel = PM.close_worst_leg_selection([pos(1)], "SELL", "NETTED")
    assert sel["status"] == "AMBIGUOUS" and sel["reason"] == "SINGLE_VWAP_OR_NETTED_ACCOUNT"


def test_sell_and_buy_worst_ordering():
    legs = [pos(1, price=4119.0), pos(2, price=4123.0)]
    assert PM.order_legs_worst_first(legs, "SELL")[0].price == 4119.0    # SELL lower = worse
    assert PM.order_legs_worst_first(legs, "BUY")[0].price == 4123.0     # BUY higher = worse


def test_account_type_detection():
    assert PM.detect_account_type("HEDGED") == "HEDGED" and PM.detect_account_type("NETTED") == "NETTED"


# ---- breakeven (VWAP) ----
def test_breakeven_uses_broker_vwap_not_signal_entry():
    a = MP.breakeven_proposal(pos(price=4119.44), quote=quote(), symbol_digits=2, point=0.01,
                              min_stop_distance_points=10)
    assert a.detail["proposed_stop"] == 4119.44 and a.detail["actual_vwap_entry"] == 4119.44
    assert a.detail["label"] == "ENTRY-PRICE BREAKEVEN" and a.detail["no_silent_buffer"] is True
    assert a.detail["proposed_stop"] != 4116.0                          # signal zone low not used


# ---- partial close / volume normalization ----
def test_provider_one_lot_not_blindly_applied():
    a = MP.partial_close_proposal(pos(volume_units=300), min_volume_units=MINU, step_volume_units=STEPU,
                                  units_per_lot=UNITS_PER_LOT, quote=quote(), provider_literal_lots=1.0,
                                  provider_wording="take 1 lot out")
    assert not a.ok and a.reason == "PROVIDER_LITERAL_UNMAPPED"
    assert a.detail["PROVIDER_LITERAL_VOLUME"] == "1.00 LOT" and a.detail["mapping"] == "UNMAPPED_TO_OUR_POSITION"
    lots = {c["close_lots"] for c in a.detail["operator_choices"]}
    assert lots == {0.01, 0.02, 0.03}                                   # close 0.01/0.02/0.03 only, no auto choice


def test_partial_close_step_and_remaining_valid():
    a = MP.partial_close_proposal(pos(volume_units=300), min_volume_units=MINU, step_volume_units=STEPU,
                                  units_per_lot=UNITS_PER_LOT, quote=quote(), requested_fraction=0.6667)
    assert a.ok and a.detail["proposed_close_units"] == 200 and a.detail["remaining_units"] == 100


def test_partial_close_cannot_exceed_open():
    a = MP.partial_close_proposal(pos(volume_units=300), min_volume_units=MINU, step_volume_units=STEPU,
                                  units_per_lot=UNITS_PER_LOT, quote=quote(), requested_fraction=1.5)
    assert not a.ok and a.reason == "CLOSE_EXCEEDS_OPEN"


def test_partial_close_remaining_below_min_rejected():
    # closing 100 of 150 leaves 50 (< min 100) -> rejected
    a = MP.partial_close_proposal(pos(volume_units=150), min_volume_units=MINU, step_volume_units=STEPU,
                                  units_per_lot=UNITS_PER_LOT, quote=quote(), requested_fraction=0.6667)
    assert not a.ok and a.reason in ("REMAINING_BELOW_MIN_VOLUME", "NOT_STEP_VALID")


# ---- composite ----
def test_composite_displays_every_action():
    be = MP.breakeven_proposal(pos(), quote=quote(), symbol_digits=2, point=0.01, min_stop_distance_points=10)
    pc = MP.partial_close_proposal(pos(), min_volume_units=MINU, step_volume_units=STEPU,
                                   units_per_lot=UNITS_PER_LOT, quote=quote(), requested_fraction=0.3333)
    plan = MP.composite_plan([be, pc])
    assert len(plan["actions"]) == 2 and "SEQUENTIAL" in plan["execution_note"]


def test_composite_action_one_failure_blocks_continuation():
    bad = MP.partial_close_proposal(pos(volume_units=300), min_volume_units=MINU, step_volume_units=STEPU,
                                    units_per_lot=UNITS_PER_LOT, quote=quote(), requested_fraction=1.5)
    good = MP.breakeven_proposal(pos(), quote=quote(), symbol_digits=2, point=0.01, min_stop_distance_points=10)
    plan = MP.composite_plan([bad, good])
    assert plan["all_actions_valid"] is False and "STOP" in plan["execution_note"]


# ---- orchestrator: gates / dry-run / audit ----
def _plan(tmp, **over):
    adb = AuditDB(os.path.join(tmp, "a.db"))
    kw = dict(signal_id="sig-1", source_class="TRADE_UPDATE", confirmed=True, provider_verified=True,
              update_text="move SL to breakeven", update_ts_ms=NOW, account=acct(), account_type="HEDGED",
              symbol_digits=2, point=0.01, min_stop_distance_points=10, positions=[pos(label="sig-1")],
              quote=quote(), now_ms=NOW, units_per_lot=UNITS_PER_LOT, min_volume_units=MINU,
              step_volume_units=STEPU, audit=adb)
    kw.update(over)
    return UP.build_update_plan(**kw), adb


def test_trade_result_cannot_modify():
    _run(lambda tmp: (lambda r: (_ for _ in ()).throw(AssertionError()) if r[0]["valid"] else None)(
        _plan(tmp, source_class="TRADE_RESULT")) or
        (lambda r: (isinstance(r[0]["card"], dict) and r[0]["card"]["reason"] == "TRADE_RESULT_CANNOT_MODIFY_POSITION"))(_plan(tmp, source_class="TRADE_RESULT")))


def test_ocr_unconfirmed_cannot_modify():
    def f(tmp):
        r, _ = _plan(tmp, confirmed=False)
        assert not r["valid"] and r["card"]["reason"] == "NOT_HUMAN_CONFIRMED"
    _run(f)


def test_stale_quote_and_update_rejected():
    def f(tmp):
        assert _plan(tmp, quote=quote(ts_ms=NOW - 999999))[0]["card"]["reason"] == "STALE_QUOTE"
        assert _plan(tmp, update_ts_ms=NOW - CFG.SIGNAL_STALE_SECONDS * 1000 - 5000)[0]["card"]["reason"] == "STALE_UPDATE"
    _run(f)


def test_ambiguous_match_blocks_plan():
    def f(tmp):
        r, _ = _plan(tmp, positions=[pos(1, label="x", direction="SELL"), pos(2, label="y", direction="SELL")])
        assert not r["valid"] and "POSITION_MATCH_AMBIGUOUS" in r["card"]["reason"]
    _run(f)


def test_valid_dry_run_and_audit_events():
    def f(tmp):
        r, adb = _plan(tmp)
        assert r["valid"] and r["status"] == "MANAGEMENT_PLAN_VALIDATED"
        assert UP.arm_plan(r["plan_id"], adb)["armed"] is True
        res = UP.dry_run_approve(r["plan_id"], now_ms=NOW, audit=adb)
        assert res["result"] == "UPDATE_PLAN_DRY_RUN_APPROVED" and res["broker_action_sent"] is False
        evs = [e["event_type"] for e in adb.events_for(r["plan_id"])]
        for want in ("UPDATE_RECEIVED", "MANAGEMENT_PLAN_VALIDATED", "MANAGEMENT_PLAN_ARMED",
                     "UPDATE_PLAN_DRY_RUN_APPROVED"):
            assert want in evs
    _run(f)


def test_plan_id_idempotent():
    a = UP.make_plan_id("sig-1", 1, 4257941, "u1")
    b = UP.make_plan_id("sig-1", 1, 4257941, "u1")
    assert a == b and a.startswith("mgmtplan-")


# ---- safety ----
def test_update_cannot_open_position_no_order_tokens():
    # forbid the actual ENABLING code forms (constructors / *Req classes / calls), not doc mentions
    for fn in ("update_plans.py", "management_planner.py", "position_matcher.py", "update_parser.py"):
        src = open(os.path.join(_DE, fn), encoding="utf-8").read()
        for bad in ("ProtoOANewOrderReq", "NewOrderReq(", "ProtoOAAmendPositionSLTPReq",
                    "ProtoOAClosePositionReq", "sendorder", "open_position("):
            assert bad not in src


def test_execution_locks_false_and_sending_disabled():
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc
    assert CFG.ORDER_SENDING_ENABLED is False


def test_audit_rejects_future_mgmt_events():
    def f(tmp):
        adb = AuditDB(os.path.join(tmp, "a.db"))
        try:
            adb.record("PARTIAL_CLOSE_REQUESTED", "mgmtplan-x", {}); assert False   # future event not enabled
        except ValueError:
            pass
    _run(f)
