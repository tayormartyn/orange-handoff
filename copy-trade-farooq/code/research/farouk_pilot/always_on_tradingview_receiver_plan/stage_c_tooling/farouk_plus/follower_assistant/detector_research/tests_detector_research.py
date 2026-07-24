"""Deterministic tests for the documented detector-research layer (RESEARCH-ONLY).

Covers: causal completed-bars-only resampling (no forming-candle leakage), 1m->3m/5m alignment,
FVG/BPR/OB/sweep/failed-close definitions, detector predicates, grade-system separation, Constitution
v0.1 immutability, no outcome-driven policy selection, comparator single-fill equivalence, and the
absence of any sizing/execution field in the research artefacts.
"""
from __future__ import annotations

import io
import json
import os
import sys
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import detector_features as F                                    # noqa: E402
import detectors as DET                                          # noqa: E402

PASS = 0
FAIL = 0


def ok(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {name}")


def bar(ts, o, h, l, c):
    return (ts, D(str(o)), D(str(h)), D(str(l)), D(str(c)))


# ---- 1) resample drops the final (open) bar = completed-only -----------------------------------
def test_resample_completed_only():
    m1 = [bar(0, 1, 2, 0, 1), bar(60, 1, 3, 1, 2), bar(120, 2, 4, 2, 3),   # bucket 0 (0-300)
          bar(300, 3, 5, 3, 4)]                                            # bucket 300 (open)
    out = F.resample_1m(m1, 300)
    ok("resample drops open bucket", len(out) == 1 and out[0][0] == 0)
    ok("resample high/low aggregated", out[0][2] == D("4") and out[0][3] == D("0"))


def test_completed_before_no_leak():
    bars5 = [(0, D(1), D(1), D(1), D(1)), (300, D(1), D(1), D(1), D(1))]
    # a 5m bar starting at 300 is only complete at 600; at ts=590 it must be excluded
    got = F.completed_before(bars5, 590, 300)
    ok("completed_before excludes forming bar", all(b[0] + 300 <= 590 for b in got) and len(got) == 1)


# ---- 2) FVG / BPR / OB / sweep / failed-close definitions ---------------------------------------
def test_fvg_def():
    bars = [bar(0, 10, 11, 9, 10), bar(1, 11, 13, 11, 12), bar(2, 13, 15, 13, 14)]  # b1.high 11 < b3.low 13
    fs = F.fvgs(bars)
    ok("bullish FVG detected", any(f["kind"] == "BULLISH_FVG" for f in fs))
    ok("FVG gap bounds", fs[0]["low"] == D("11") and fs[0]["high"] == D("13"))


def test_sweep_and_failed_close():
    ok("sweep high wick+closeback", F.sweep(D("100"), bar(0, 99, 105, 98, 99), "high"))
    ok("no sweep if closes above", not F.sweep(D("100"), bar(0, 99, 105, 98, 103), "high"))
    ok("failed_close above level", F.failed_close(bar(0, 99, 105, 98, 100), D("100"), "high"))
    ok("failed_close false on body close through", not F.failed_close(bar(0, 99, 105, 98, 103), D("100"), "high"))


def test_ob_and_bpr_unknown_preserved():
    bars = [bar(0, 5, 5, 5, 5), bar(1, 10, 10, 8, 8),   # bearish candle c0
            bar(2, 8, 12, 8, 11), bar(3, 11, 14, 11, 13), bar(4, 13, 16, 13, 15)]  # 3 up
    obs = F.order_blocks(bars)
    ok("bullish OB found", any(o["kind"] == "BULLISH_OB" for o in obs))
    ok("OB displacement threshold UNKNOWN", all(o["displacement_threshold"] == "UNKNOWN" for o in obs))


# ---- 3) detector predicates: bearish FVG mirror NOT emitted; asia fakeout structural ------------
def test_fvg_detector_bullish_only():
    price = os.path.join(HERE, "..", "..", "..", "price_data",
                         "XAUUSD_1M_PEPPERSTONE_2026-07-08_to_2026-07-15_CANONICAL.csv")
    m1 = DET._load(price)
    fvg = DET.detect_fvg_continuation_5m(m1)
    ok("all FVG matches LONG (no invented bearish mirror)", all(m["direction"] == "LONG" for m in fvg))
    ok("FVG matches carry UNKNOWN displacement", all(m["displacement_threshold"] == "UNKNOWN" for m in fvg))
    ok("FVG bearish mirror explicitly UNKNOWN", all("UNKNOWN" in m["bearish_mirror"] for m in fvg))


def test_asia_fakeout_structural():
    price = os.path.join(HERE, "..", "..", "..", "price_data",
                         "XAUUSD_1M_PEPPERSTONE_2026-07-08_to_2026-07-15_CANONICAL.csv")
    m1 = DET._load(price)
    asia = DET.detect_asia_fakeout(m1)
    ok("asia matches carry window UNKNOWN-tz", all("UNKNOWN" in m["asia_window"] for m in asia))


def test_first_ll_hh_strictly_after():
    """F1 fix: prove the confirmation primitive requires the extreme STRICTLY AFTER the fakeout bar
    (non-tautological: a lower-low BEFORE must not confirm; one AFTER must, and its ts must be > fakeout)."""
    fk = 1000
    ref_low = D("100")
    bars = [bar(500, 101, 101, 99, 100),    # lower-low BEFORE the fakeout -> must be ignored
            bar(1000, 100, 101, 97, 100),   # fakeout bar itself qualifies on price but ts==after -> excluded (strict >)
            bar(1500, 100, 100, 98, 99)]    # genuine lower-low AFTER -> must confirm
    got = F.first_lower_low(bars, ref_low, fk)
    ok("first_lower_low ignores pre-fakeout low", got == 1500)
    ok("first_lower_low is strictly after fakeout", got > fk)
    # no lower-low after -> None (unconfirmed)
    bars_none = [bar(500, 101, 101, 90, 95), bar(1500, 100, 101, 100, 100)]
    ok("no post-fakeout LL -> None", F.first_lower_low(bars_none, ref_low, fk) is None)
    # bullish mirror: higher-high strictly after
    ref_high = D("100")
    up = [bar(500, 99, 105, 99, 100), bar(1500, 100, 106, 100, 105)]
    ok("first_higher_high ignores pre low, takes post", F.first_higher_high(up, ref_high, fk) == 1500)
    ok("first_higher_high strictly after", F.first_higher_high(up, ref_high, fk) > fk)


# ---- 4) grade systems kept separate in the spec ------------------------------------------------
def test_grades_separate_in_spec():
    spec = json.load(open(os.path.join(HERE, "FAROUK_DOCUMENTED_DETECTOR_SPEC_v0_1.json"), encoding="utf-8"))
    gs = spec["grade_systems_separate"]
    ok("indicator equivalence UNKNOWN", "UNKNOWN" in gs["tradingview_indicator_grade"])
    ok("relationship UNKNOWN / not merged", "UNKNOWN" in gs["relationship"])
    ok("global unknowns present", len(spec["global_unknowns"]) >= 8)


# ---- 5) Constitution v0.1 immutability (proposal must NOT touch it) -----------------------------
def test_constitution_v0_1_untouched():
    import hashlib
    cpath = os.path.join(os.path.dirname(HERE), "follower_constitution_v0_1.json")
    h = hashlib.sha256(open(cpath, "rb").read()).hexdigest()
    ok("constitution sha unchanged", h == "7bce618f29d1d44a48bef085d539b05a289393ebe33fe4d304632016777defde")
    prop = json.load(open(os.path.join(HERE, "CONSTITUTION_v0_2_REVISION_PROPOSAL.json"), encoding="utf-8"))
    ok("proposal is DRAFT_NOT_RATIFIED", "DRAFT_NOT_RATIFIED" in prop["status"])
    ok("proposal references v0.1 sha", prop["constitution_v0_1_sha256_referenced"].startswith("7bce618f"))


# ---- 6) comparator: single-fill => B mechanically equals A; C UNKNOWN; no execution fields ------
def test_comparator_single_fill_equivalence():
    import whaleroom_comparator as WC
    price = os.path.join(HERE, "..", "..", "..", "price_data",
                         "XAUUSD_1M_PEPPERSTONE_2026-07-08_to_2026-07-15_CANONICAL.csv")
    m1 = WC._load_1m(price)
    for cid in ("XAU-F001-20260714", "XAU-F002-20260714"):
        card = WC._card(cid)
        # recompute the average from the FILLED legs and assert single-fill => avg == the one fill
        filled = [l for l in card["theoretical_legs"] if l["state"] == "FILLED"]
        ok(f"{cid} exactly one filled leg", len(filled) == 1)
        rep = WC.replay(card, m1)
        ok(f"{cid} avg == single fill", rep["campaign_average_entry"] == filled[0]["fill_price"])
        # the whole point: with average==fill, +50-from-average == +50-from-leg -> B's realized
        # equals A's realized as a DATA fact (both read the same frozen lanes here)
        a = rep["policies"]["A_CURRENT_STRICT_ORANGE"]["realized_pips_per_unit"]
        b = rep["policies"]["B_DOCUMENTED_WHALEROOM_AVERAGE_BE"]
        ok(f"{cid} single-fill collapses avg-BE to per-leg", "MECHANICALLY IDENTICAL" in b["equivalence_to_A"])
        ok(f"{cid} C UNKNOWN (no posted TP)", rep["policies"]["C_DOCUMENTED_CONSERVATIVE_TP"]["result"] == "UNKNOWN")
        # 700-pip claim must map to an UNREALIZED runner MFE, never a realized policy figure
        d = rep["policies"]["D_DOCUMENTED_ADVANCED_TP"]
        ok(f"{cid} D runner MFE is unrealized-labelled", "UNREALIZED" in d["runner_note"])
        ok(f"{cid} realized A is modest (<< runner MFE)", D(str(a)) < D("100"))


# ---- 7) no outcome-driven policy selection: no policy is labelled 'best'/'chosen' ---------------
def test_no_outcome_driven_selection():
    pol = json.load(open(os.path.join(HERE, "DOCUMENTED_WHALEROOM_FOLLOWER_POLICY_v0_1.json"), encoding="utf-8"))
    blob = json.dumps(pol).lower()
    for banned in ("most_profitable", "best_policy", "chosen_policy", "recommended_policy"):
        ok(f"no outcome-selection token '{banned}'", banned not in blob)


# ---- 8) NO sizing/execution/broker field leaked into any research artefact ----------------------
def test_no_execution_fields():
    forbidden = ["lot_size", "position_size", "order_id", "broker_account", "qst", "ctrader_order",
                 "leverage", "margin_required", "api_key", "webhook_url"]
    for fn in ("FAROUK_DOCUMENTED_DETECTOR_SPEC_v0_1.json", "DOCUMENTED_WHALEROOM_FOLLOWER_POLICY_v0_1.json",
               "whaleroom_comparator_result_v0_1.json", "mode_evidence_register_v0_1.json",
               "CONTRADICTION_UNKNOWN_REGISTER_v0_1.json", "CONSTITUTION_v0_2_REVISION_PROPOSAL.json"):
        blob = open(os.path.join(HERE, fn), encoding="utf-8").read().lower()
        for tok in forbidden:
            ok(f"{fn} free of '{tok}'", tok not in blob)
        ok(f"{fn} marked review_only", '"review_only": true' in blob or '"review_only":true' in blob)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    for fn in [test_resample_completed_only, test_completed_before_no_leak, test_fvg_def,
               test_sweep_and_failed_close, test_ob_and_bpr_unknown_preserved,
               test_fvg_detector_bullish_only, test_asia_fakeout_structural,
               test_first_ll_hh_strictly_after,
               test_grades_separate_in_spec, test_constitution_v0_1_untouched,
               test_comparator_single_fill_equivalence, test_no_outcome_driven_selection,
               test_no_execution_fields]:
        fn()
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)
