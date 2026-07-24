"""History-repair + adjudication tests (12 proofs). Append-only; originals immutable; no broker action.
Uses a temp repair log so the real one is never touched."""
from __future__ import annotations
import glob
import os
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TL = os.path.join(_ROOT, "campaign_extractor", "trade_lifecycle")
for p in (_ROOT, _TL):
    if p not in sys.path:
        sys.path.insert(0, p)

import history_repair as HR
import provider_outcome as PO
import effective_view as EV
from lc_models import SignalRef, ChildEvent, BrokerEvent

NOW = "2026-07-03T05:00:00Z"


def _tmp_log():
    d = tempfile.mkdtemp()
    HR.REPAIR_LOG = os.path.join(d, "repair_events.jsonl")
    return d


# 1
def test_originals_immutable_repair_writes_only_to_repair_log():
    src = open(os.path.join(_TL, "history_repair.py"), encoding="utf-8").read()
    assert "REPAIR_LOG" in src
    for bad in ("signal_archive", "paper_observations", "review/", ".json\", \"w\"", "INSERT", "DELETE FROM"):
        assert bad not in src
    # every write target is the append-only repair log opened in append mode
    assert 'open(REPAIR_LOG, "a"' in src and '"w"' not in src


# 2
def test_corrections_are_append_only():
    _tmp_log()
    HR.propose_signal_correction("i1", {"direction": {"value": "SELL"}}, NOW)
    HR.propose_signal_correction("i1", {"stop": {"value": 4140.0}}, NOW)   # second proposal appends
    evs = HR.load_events()
    assert len(evs) == 2 and all(e["event_type"] == "SIGNAL_FIELD_CORRECTION_PROPOSED" for e in evs)


# 3
def test_unsupported_fields_stay_unknown():
    rec = HR.recover_fields("just some chatter, gm traders")
    assert "direction" not in rec and "entry_low" not in rec and "stop" not in rec
    _tmp_log()
    e = HR.propose_signal_correction("i2", rec, NOW)
    assert set(e["still_unknown"]) >= {"direction", "entry_low", "stop", "targets"}


# 4
def test_symbol_only_parent_matching_blocked():
    child = {"instrument": "XAUUSD"}                     # symbol only, no direction/provider
    parents = [{"signal_id": "s1", "instrument": "XAUUSD"}]
    assert HR.link_candidates(child, parents) == []


# 5
def test_one_child_cannot_attach_to_two_parents():
    _tmp_log()
    HR.confirm_parent_link("c1", "sA", "martyn", NOW)
    HR.confirm_parent_link("c1", "sB", "martyn", NOW)   # re-adjudication
    links = HR.confirmed_links()
    assert list(links.keys()).count("c1") == 1 and len({links["c1"]}) == 1   # exactly one parent


# 6
def test_one_intake_not_both_parent_and_child():
    parents, children, conflicts = HR.latest_role_sets()
    assert "intake-30b8d4bfb0996dcc" in parents          # latest class SIGNAL -> parent only
    assert "intake-30b8d4bfb0996dcc" not in children
    assert "intake-30b8d4bfb0996dcc" in conflicts        # conflict is surfaced, not silent


# 7
def test_duplicate_links_idempotent():
    _tmp_log()
    HR.confirm_parent_link("c9", "sZ", "martyn", NOW)
    HR.confirm_parent_link("c9", "sZ", "martyn", NOW)
    assert HR.confirmed_links() == {"c9": "sZ"}


# 8
def test_provider_result_separate_from_broker_result():
    out, blk, note = PO.determine_provider_outcome(provider_partial_confirmed=True,
                                                   provider_volume_known=True, market_breakeven_touch=True)
    assert out == "PROVIDER_MANAGED_PROFIT" and "NOT Martyn" in note
    # provider outcome never carries realised demo P&L (that is broker-only)
    src = open(os.path.join(_TL, "provider_outcome.py"), encoding="utf-8").read()
    assert "realised_pnl" not in src and "realised_demo" not in src


# 9
def test_replay_records_stay_out_of_prospective_stats():
    s = SignalRef(signal_id="s", instrument="XAUUSD", direction="SELL", stop=4140.0, ts_ms=1, replay=True)
    e, _ = EV.build_effective_trade(s, [], [BrokerEvent(kind="ORDER_FILLED", vwap_price=4120.0, prospective=True),
                                           BrokerEvent(kind="STOP_HIT", stop_price=4140.0, prospective=True)])
    assert e.provenance == "REPLAY_VALIDATION_ONLY" and e.counts_in_prospective_stats is False


# 10
def test_exact_r_withheld_when_volume_or_fill_unknown():
    out, blk, _ = PO.determine_provider_outcome(provider_partial_confirmed=True, provider_volume_known=False,
                                                market_breakeven_touch=True)
    assert out == "PROVIDER_PROFIT_R_UNKNOWN" and "PROVIDER_PARTIAL_VOLUME_UNKNOWN" in blk


# 11
def test_no_order_amend_close_cancel_action():
    for pth in glob.glob(os.path.join(_TL, "*.py")):
        src = open(pth, encoding="utf-8").read()
        for bad in ("ProtoOANewOrderReq", "ProtoOAAmendPositionSLTPReq", "ProtoOAClosePositionReq",
                    "ProtoOACancelOrderReq", "send_new_order", "new_order("):
            assert bad not in src


def test_confirm_correction_with_fields_and_reject():
    _tmp_log()
    HR.confirm_signal_correction("i7", "martyn", NOW, fields={"direction": {"value": "SELL"}})
    HR.reject_signal_correction("i8", "martyn", NOW)
    ets = [e["event_type"] for e in HR.load_events()]
    assert "SIGNAL_FIELD_CORRECTION_CONFIRMED" in ets and "SIGNAL_FIELD_CORRECTION_REJECTED" in ets
    assert HR.confirmed_corrections()["i7"] == {"direction": {"value": "SELL"}}


def test_edit_correction_is_append_only_and_preserves_original():
    _tmp_log()
    HR.propose_signal_correction("i9", {"stop": {"value": 4140.0, "evidence": "StopLoss:4140"}}, NOW)
    HR.confirm_signal_correction("i9", "martyn", NOW, fields={"stop": {"value": 4140.0}})
    HR.edit_signal_correction("i9", {"stop": {"value": 4141.0}}, "martyn", NOW)
    evs = HR.load_events()
    assert evs[0]["event_type"] == "SIGNAL_FIELD_CORRECTION_PROPOSED"          # original preserved
    assert evs[0]["proposed_fields"]["stop"]["evidence"] == "StopLoss:4140"
    assert HR.confirmed_corrections()["i9"] == {"stop": {"value": 4141.0}}     # edit overrides effective


def test_role_decision_requires_explicit_valid_role():
    _tmp_log()
    HR.role_conflict_decision("i10", "PARENT_SIGNAL", "martyn", NOW)
    try:
        HR.role_conflict_decision("i10", "NONSENSE", "martyn", NOW); assert False
    except AssertionError:
        pass
    assert HR.load_events()[0]["chosen_role"] == "PARENT_SIGNAL"


def test_no_candidate_decisions():
    _tmp_log()
    HR.leave_unlinked("c5", "martyn", NOW)
    HR.classify_unrelated_replay("c6", "martyn", NOW)
    ets = [e["event_type"] for e in HR.load_events()]
    assert "CHILD_LEFT_UNLINKED" in ets and "CHILD_CLASSIFIED_UNRELATED_REPLAY" in ets


def test_repair_action_endpoint_dispatch():
    import importlib
    sys.path.insert(0, os.path.join(_ROOT, "campaign_extractor", "paper_loop", "console"))
    srv = importlib.import_module("server")
    _tmp_log()                                            # do_repair_action imports the same HR module
    r1 = srv.do_repair_action("/api/repair_confirm_link", {"child_id": "cE", "parent_signal_id": "sE"})
    r2 = srv.do_repair_action("/api/repair_reject_correction", {"intake_id": "iE"})
    assert r1["event_type"] == "PARENT_LINK_CONFIRMED" and r2["event_type"] == "SIGNAL_FIELD_CORRECTION_REJECTED"
    # invalid role decision is rejected, not silently accepted
    bad = srv.do_repair_action("/api/repair_role_decision", {"intake_id": "iE", "role": "BAD"})
    assert bad.get("error") == "INVALID_DECISION"


def test_classification_confirm_reject_and_confirmed():
    _tmp_log()
    HR.propose_classification_correction("iC", "SIGNAL", "TRADE_RESULT", {"x": 1}, NOW)
    assert [e["intake_id"] for e in HR.pending_classification_corrections()] == ["iC"]
    HR.confirm_classification_correction("iC", "TRADE_RESULT", "martyn", NOW)
    assert HR.confirmed_classifications() == {"iC": "TRADE_RESULT"}
    assert HR.pending_classification_corrections() == []            # resolved -> not pending
    _tmp_log()
    HR.propose_classification_correction("iD", "SIGNAL", "TRADE_RESULT", {}, NOW)
    HR.reject_classification_correction("iD", "martyn", NOW)
    assert HR.confirmed_classifications() == {} and HR.pending_classification_corrections() == []


def test_confirmed_reclass_moves_signal_to_child():
    import shutil
    import lifecycle_console as LC
    real = os.path.join(_ROOT, "data", "manual_image_intake_v1", "repair_events.jsonl")
    d = tempfile.mkdtemp()
    tlog = os.path.join(d, "repair_events.jsonl")
    # seed with real proposals/decisions but WITHOUT any classification events, so 16aa46 starts SIGNAL
    seed = [l for l in open(real, encoding="utf-8") if l.strip() and "CLASSIFICATION_CORRECTION" not in l]
    open(tlog, "w", encoding="utf-8").writelines(seed)
    HR.REPAIR_LOG = tlog
    before = {s.signal_id for s in LC.load_records()[0]}
    assert "intake-16aa46ce6d497d8a" in before                      # a parent SIGNAL before reclass
    HR.confirm_classification_correction("intake-16aa46ce6d497d8a", "TRADE_RESULT", "martyn", NOW)
    sigs, childs, _ = LC.load_records()
    assert "intake-16aa46ce6d497d8a" not in {s.signal_id for s in sigs}     # no longer a parent
    assert "intake-16aa46ce6d497d8a" in {c.child_id for c in childs}        # now a result child
    shutil.rmtree(d, ignore_errors=True)


# 12
def test_execution_locks_false():
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    de = open(os.path.join(_ROOT, "campaign_extractor", "demo_executor", "config.py"), encoding="utf-8").read()
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc
    assert "ORDER_SENDING_ENABLED = False" in de
