"""Focused read-only tests for gold_backlog_audit_report.py — reconciliation + exclusion + safety."""
from __future__ import annotations
import hashlib
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

import gold_backlog_audit_report as A

_REP = None
_EXC = None


def _report():
    global _REP, _EXC
    if _REP is None:
        _REP, _EXC = A.compute()
    return _REP, _EXC


def test_denominators_exact():
    rep, _ = _report()
    ev = rep["expected_vs_actual"]
    assert ev["total"]["actual"] == 406
    assert ev["gold"]["actual"] == 296
    assert ev["farouk_gold"]["actual"] == 240
    assert ev["quantified"]["actual"] == 123
    assert ev["r_known_all"]["actual"] == 78
    assert ev["r_known_gold"]["actual"] == 69
    assert all(v["match"] for v in ev.values())


def test_waterfall_296_reconciles():
    rep, _ = _report()
    wf = rep["6_coverage_waterfall"]
    assert wf["archive_296_only"]["sum"] == 296 and wf["archive_296_only"]["equals_296"]
    assert wf["reconcile_universe"]["equals_universe"]
    comp = wf["quantified_123_composition"]
    assert comp["within_296_archive"] + comp["recovered_market_calls_outside_296"] == 123


def test_farouk_subset_of_gold():
    rep, _ = _report()
    inv = rep["1_dataset_inventory"]
    assert inv["farouk_gold_denominator"] <= inv["gold_denominator"]


def test_r_known_gold_not_exceed_quantified():
    rep, _ = _report()
    assert (rep["3_r_coverage_and_performance"]["r_known_denominator_gold"]
            <= rep["6_coverage_waterfall"]["categories"]["quantified_independent_signal"])


def test_binary_totals_reconcile():
    rep, _ = _report()
    b = rep["2_outcome_distributions"]["all_406"]["binary_rollup"]
    bg = rep["2_outcome_distributions"]["gold_296"]["binary_rollup"]
    assert sum(b.values()) == 406 and sum(bg.values()) == 296


def test_every_r_stat_states_denominator():
    rep, _ = _report()
    r = rep["3_r_coverage_and_performance"]
    for key in ("all_instruments_r_known", "gold_r_known_raw", "gold_r_known_cleaned"):
        assert "denominator_note" in r[key] and r[key]["denominator_note"]


def test_cleaned_gold_aggregate():
    rep, _ = _report()
    c = rep["3_r_coverage_and_performance"]["gold_r_known_cleaned"]
    assert c["n"] == 66 and abs(c["mean"] - 0.2788) < 0.01     # reused gold_clean_report._agg


def test_coverage_categories_separate():
    rep, _ = _report()
    cov = rep["8_coverage_breakdown"]
    # outcome_evidence present is NOT tick-path coverage; the two counts must be distinct fields
    assert cov["outcome_evidence_present_signals"] == 356
    assert cov["dukascopy_tickpath_evidence_signals"] == 27
    assert cov["q4a_anchor_coverage_signals"] == 0


def test_exclusions_do_not_leak():
    rep, _ = _report()
    ex = rep["7_performance_exclusions"]
    assert ex["btc_present_in_signal_denominator"] is False
    assert ex["test_or_synthetic_rows_in_archive"] == 0
    assert ex["leak_detected"] is False


def test_btc_trade_result_absent_from_signals():
    rep, exc = _report()
    # the excluded BTC key must never appear as a signal denominator member
    assert rep["7_performance_exclusions"]["btc_trade_result_key"] == "review-img-a605d64b16150b20"
    assert any(e["kind"] == "NON_SIGNAL_EXCLUDED" for e in exc)


def test_validate_passes():
    rep, _ = _report()
    checks = A.validate(rep)
    assert all(c["pass"] for c in checks) and len(checks) >= 8


def test_execution_locks_and_no_exec_code():
    cfg = open(os.path.join(_ROOT, "config.py"), encoding="utf-8").read()
    cc = open(os.path.join(_ROOT, "ctrader_config.py"), encoding="utf-8").read()
    assert "EXECUTION_ENABLED = False" in cfg and "CTRADER_EXECUTION_ENABLED = False" in cc
    src = open(os.path.join(_ROOT, "gold_backlog_audit_report.py"), encoding="utf-8").read()
    for bad in ("send_order", "place_order", "execute_trade", "amend_order", "cancel_order",
                "close_position", "new_order", "sendProtoOA"):
        assert bad not in src


def test_protected_hashes_unchanged_across_compute():
    before = {p: (hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None)
              for p in A.PROTECTED}
    A.compute()
    after = {p: (hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None)
             for p in A.PROTECTED}
    assert before == after
