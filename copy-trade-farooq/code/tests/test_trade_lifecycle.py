"""Trade-lifecycle engine tests (15 proofs). Pure/derived; no broker action; originals immutable."""
from __future__ import annotations
import glob
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TL = os.path.join(_ROOT, "campaign_extractor", "trade_lifecycle")
for p in (_ROOT, _TL):
    if p not in sys.path:
        sys.path.insert(0, p)

import linker
import effective_view as EV
from lc_models import SignalRef, ChildEvent, BrokerEvent


def sig(sid="sigA", replay=True, **o):
    d = dict(signal_id=sid, instrument="XAUUSD", direction="BUY", provider="farouk",
             entry_low=4116.0, entry_high=4118.0, stop=4110.0, targets=(4130.0,), confirmed=True,
             ts_ms=1000, replay=replay)
    d.update(o)
    return SignalRef(**d)


def upd(cid="u1", parent="sigA", kind="TAKE_PROFIT", **o):
    d = dict(child_id=cid, child_class="TRADE_UPDATE", instrument="XAUUSD", direction="BUY",
             provider="farouk", ts_ms=2000, explicit_parent_signal_id=parent, instruction_kind=kind)
    d.update(o)
    return ChildEvent(**d)


def brk(kind, **o):
    return BrokerEvent(kind=kind, **o)


def eff(signal, children=(), broker=(), **o):
    return EV.build_effective_trade(signal, list(children), list(broker), **o)


# 1
def test_update_never_creates_second_signal():
    e, seq = eff(sig(), [upd()])
    assert e.signal_id == "sigA" and e.linked_updates == ["u1"]
    assert sum(1 for s in seq if s["state"] == "SIGNAL_CAPTURED") == 1   # exactly one signal


# 2
def test_linked_update_advances_correct_parent_only():
    a, _ = eff(sig("sigA"), [upd(parent="sigA")])
    b, _ = eff(sig("sigB"), [upd(parent="sigA")])          # same update, confirmed-linked to sigA
    assert a.linked_updates == ["u1"] and b.linked_updates == []
    # u1 belongs to sigA -> it must NOT appear as a blocker on sigB (not sigB's concern)
    assert not any("u1" in x for x in b.blockers)


# 3
def test_symbol_only_matching_blocked():
    child = ChildEvent(child_id="c", child_class="TRADE_UPDATE", instrument="XAUUSD")  # symbol only
    lr = linker.link_child(child, [sig()])
    assert lr.status == "UNLINKED" and lr.reason == "SYMBOL_ALONE_OR_NO_MATCH"


# 4
def test_partial_plus_breakeven_stop_is_managed_profit():
    e, _ = eff(sig(), [upd()], [brk("ORDER_FILLED", vwap_price=4117.0),
                                brk("PARTIAL_CLOSE", closed_volume_raw=600, realised_pnl=30.0),
                                brk("SL_AMENDED", stop_price=4117.0),
                                brk("STOP_HIT", stop_price=4117.0)])
    assert e.outcome == "CLOSED_MANAGED_PROFIT" and e.state == "CLOSED_MANAGED_PROFIT"


# 5
def test_breakeven_stop_without_partial_is_breakeven():
    e, _ = eff(sig(), [], [brk("ORDER_FILLED", vwap_price=4117.0),
                           brk("SL_AMENDED", stop_price=4117.0),
                           brk("STOP_HIT", stop_price=4117.0)])
    assert e.outcome == "CLOSED_BREAKEVEN" and e.r_multiple == 0.0


# 6
def test_original_stop_before_profit_is_loss():
    e, _ = eff(sig(), [], [brk("ORDER_FILLED", vwap_price=4117.0), brk("STOP_HIT", stop_price=4110.0)])
    assert e.outcome == "CLOSED_LOSS" and e.r_multiple == -1.0


# 7
def test_provider_instruction_alone_is_not_broker_execution():
    e, _ = eff(sig(), [upd(kind="TAKE_PROFIT")])           # no broker events
    assert e.outcome == "PROVIDER_INSTRUCTION_ONLY" and e.state == "NO_BROKER_EXECUTION"
    assert e.provider_instructions and e.broker_events == []


# 8
def test_price_touch_alone_not_a_broker_fill():
    e, _ = eff(sig(), [], [], quote_path=[{"bid": 4130.0, "ask": 4130.2, "ts_ms": 3000}],
              levels={"target": 4130.0})
    assert e.market_path and "PRICE_TOUCHED_TARGET" in e.market_path[0]["kind"]
    assert e.outcome != "CLOSED_WIN" and e.state == "NO_BROKER_EXECUTION"


# 9
def test_unknown_partial_volume_prevents_exact_r():
    e, _ = eff(sig(), [], [brk("ORDER_FILLED", vwap_price=4117.0),
                           brk("PARTIAL_CLOSE", closed_volume_raw=None),
                           brk("SL_AMENDED", stop_price=4117.0), brk("STOP_HIT", stop_price=4117.0)])
    assert e.outcome == "CLOSED_PROFIT_R_UNKNOWN" and e.r_multiple is None
    assert any("PARTIAL_CLOSE_VOLUME_UNKNOWN" in b for b in e.blockers)


# 10
def test_unfilled_order_not_a_loss():
    e, _ = eff(sig(), [], [brk("ORDER_PLACED")])
    assert e.outcome == "MISSED_NOT_ENTERED" and e.state == "MISSED_NOT_ENTERED"


# 11
def test_replay_stays_out_of_prospective_stats():
    r, _ = eff(sig(replay=True), [], [brk("ORDER_FILLED", vwap_price=4117.0, prospective=True),
                                      brk("STOP_HIT", stop_price=4110.0, prospective=True)])
    assert r.provenance == "REPLAY_VALIDATION_ONLY" and r.counts_in_prospective_stats is False
    p, _ = eff(sig(replay=False), [], [brk("ORDER_FILLED", vwap_price=4117.0, prospective=True),
                                       brk("STOP_HIT", stop_price=4110.0, prospective=True)])
    assert p.provenance == "PROSPECTIVE_DEMO_EXECUTION" and p.counts_in_prospective_stats is True


# 12
def test_duplicate_updates_idempotent():
    e, _ = eff(sig(), [upd("u1"), upd("u1"), upd("u1")])   # same id thrice
    assert e.linked_updates == ["u1"]


# 13
def test_originals_immutable_no_original_store_writes():
    # no module writes any store; the pure engine does no I/O at all, the read-only adapter may READ
    # sidecars but never opens in write/append mode.
    ENGINE = {"lc_models.py", "linker.py", "evidence.py", "outcome_rules.py", "state_machine.py",
              "effective_view.py", "timeline_api.py", "provider_outcome.py"}
    # history_repair.py is the designated APPEND-ONLY writer (to a separate repair log, never an
    # original) — its immutability is proven in test_history_repair.py, so it is exempt here.
    for pth in glob.glob(os.path.join(_TL, "*.py")):
        name = os.path.basename(pth)
        if name == "history_repair.py":
            continue
        src = open(pth, encoding="utf-8").read()
        for bad in ("INSERT INTO", "DELETE FROM", "sqlite3", ', "w"', ", 'w'", ', "a"', ", 'a'"):
            assert bad not in src, (name, bad)           # no writes in engine/adapter
        if name in ENGINE:
            assert "open(" not in src, (name, "pure engine must do no I/O")


# 14
def test_no_broker_order_amend_close_constructor():
    for pth in glob.glob(os.path.join(_TL, "*.py")):
        src = open(pth, encoding="utf-8").read()
        for bad in ("ProtoOANewOrderReq", "ProtoOAAmendPositionSLTPReq", "ProtoOAClosePositionReq",
                    "ProtoOACancelOrderReq", "send_new_order", "new_order("):
            assert bad not in src


# 15
def test_execution_locks_false():
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    de = open(os.path.join(_ROOT, "campaign_extractor", "demo_executor", "config.py"), encoding="utf-8").read()
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc
    assert "ORDER_SENDING_ENABLED = False" in de
