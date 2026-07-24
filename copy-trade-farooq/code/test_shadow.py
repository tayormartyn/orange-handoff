"""
test_shadow.py — SHADOW MODE Phase 1b acceptance tests.

Covers the brief's acceptance list, all DETERMINISTIC and OFFLINE (synthetic ticks
injected into the replay; no Dukascopy/archive calls):
  * BUY enters ask / exits bid; SELL enters bid / exits ask
  * spread is taken from the tick, never double-counted
  * same input + config reproduces the same result
  * a missing quote = NO fill (never a guess)
  * coarse-bar stop+target = ambiguity bounds (pessimistic/optimistic)
  * post-re-entry boundary doesn't bleed into the parent
  * T-C scenarios are labelled RECONSTRUCTED_DELAY_SCENARIO
  * an unknown exit is never converted into a target hit
  * the no-chase deterioration formula is correct in both directions
  * gate thresholds are logged, not winner-selected
  * gold and BTC are kept separate; results are traceable

Run:  python test_shadow.py   (also pytest-compatible)
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import dukascopy_adapter as A
import shadow_config as cfg
import shadow_ledgers as LG
import shadow_nochase as NC
import shadow_replay as R

T0 = datetime(2026, 6, 25, 14, 0, 0, tzinfo=timezone.utc)
BOUND = datetime(2026, 6, 25, 18, 0, 0, tzinfo=timezone.utc)


def mk_tick(sec, bid, ask, ms=0):
    epoch_ms = int((T0 + timedelta(seconds=sec, milliseconds=ms)).timestamp() * 1000)
    return A.Tick(epoch_ms=epoch_ms,
                  dt=datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc),
                  bid=Decimal(str(bid)), ask=Decimal(str(ask)),
                  bid_raw=int(Decimal(str(bid)) * 1000), ask_raw=int(Decimal(str(ask)) * 1000),
                  bid_vol=1.0, ask_vol=1.0)


def inject(ticks):
    """Make the replay use these synthetic ticks; clear memo so each test is fresh."""
    R.clear_memo()
    R.ticks_in_range = lambda start, end, instrument=A.INSTRUMENT: (ticks, [("h", "sha", "TICKS")])


_real_ticks_in_range = R.ticks_in_range


def restore():
    R.ticks_in_range = _real_ticks_in_range
    R.clear_memo()


# ----------------------------------------------------------------------------
# 1. BUY enters on ASK, exits target on BID
# ----------------------------------------------------------------------------
def test_buy_enters_ask_exits_bid():
    # LONG ref entry 100, stop 95, target 110. Spread 0.4 (bid=ask-0.4).
    ticks = [mk_tick(0, 99.8, 100.2), mk_tick(10, 109.8, 110.2)]  # later: bid 109.8 >= 110? no
    ticks = [mk_tick(0, 99.8, 100.2), mk_tick(10, 110.0, 110.4)]  # bid 110.0 >= target 110 -> hit
    inject(ticks)
    try:
        res = R.simulate("LONG", "100", "95", ["110"], T0, BOUND,
                         entry_mode="market_on_acting", use_bidask=True, slippage="0")
        assert res["entry_price"] == "100.2", res["entry_price"]   # bought at ASK
        assert res["exit_kind"] == "target" and res["exit_price"] == "110"  # exit at target on bid
    finally:
        restore()


# ----------------------------------------------------------------------------
# 2. SELL enters on BID, exits target on ASK
# ----------------------------------------------------------------------------
def test_sell_enters_bid_exits_ask():
    # SHORT ref entry 100, stop 105, target 90.
    ticks = [mk_tick(0, 99.8, 100.2), mk_tick(10, 89.6, 90.0)]   # ask 90.0 <= target 90 -> hit
    inject(ticks)
    try:
        res = R.simulate("SHORT", "100", "105", ["90"], T0, BOUND,
                         entry_mode="market_on_acting", use_bidask=True, slippage="0")
        assert res["entry_price"] == "99.8", res["entry_price"]    # sold at BID
        assert res["exit_kind"] == "target" and res["exit_price"] == "90"
    finally:
        restore()


# ----------------------------------------------------------------------------
# 3. spread taken from tick, not double-counted
# ----------------------------------------------------------------------------
def test_spread_not_double_counted():
    # With slippage 0, a LONG entry must equal exactly the ASK (spread once), not ask+spread.
    ticks = [mk_tick(0, 99.5, 100.5), mk_tick(10, 110.0, 111.0)]
    inject(ticks)
    try:
        res = R.simulate("LONG", "100", "95", ["110"], T0, BOUND,
                         entry_mode="market_on_acting", use_bidask=True, slippage="0")
        assert Decimal(res["entry_price"]) == Decimal("100.5")   # exactly the ask, spread once
        # add slippage 0.20 -> entry worsens by exactly 0.20 (no second spread)
        R.clear_memo()
        res2 = R.simulate("LONG", "100", "95", ["110"], T0, BOUND,
                          entry_mode="market_on_acting", use_bidask=True, slippage="0.20")
        assert Decimal(res2["entry_price"]) == Decimal("100.70"), res2["entry_price"]
    finally:
        restore()


# ----------------------------------------------------------------------------
# 4. reproducibility — same input + config -> identical result
# ----------------------------------------------------------------------------
def test_reproducible():
    ticks = [mk_tick(0, 99.8, 100.2), mk_tick(10, 110.0, 110.4)]
    inject(ticks)
    try:
        a = R.simulate("LONG", "100", "95", ["110"], T0, BOUND,
                       entry_mode="market_on_acting", use_bidask=True, slippage="0.30")
        R.clear_memo()
        b = R.simulate("LONG", "100", "95", ["110"], T0, BOUND,
                       entry_mode="market_on_acting", use_bidask=True, slippage="0.30")
        assert a == b
        assert cfg.config_hash() == cfg.config_hash()   # config is stable
    finally:
        restore()


# ----------------------------------------------------------------------------
# 5. missing quote = NO fill (never guessed)
# ----------------------------------------------------------------------------
def test_missing_quote_no_fill():
    # First tick is 30s after the intended entry (> 5s gap limit) -> NO_EXECUTABLE_QUOTE
    ticks = [mk_tick(30, 99.8, 100.2), mk_tick(40, 110.0, 110.4)]
    inject(ticks)
    try:
        res = R.simulate("LONG", "100", "95", ["110"], T0, BOUND,
                         entry_mode="market_on_acting", use_bidask=True, slippage="0",
                         gap_limit_ms=5000)
        assert res["path_status"] == R.NO_EXECUTABLE_QUOTE
        assert res["entry_price"] is None and res["r"] is None
    finally:
        restore()


# ----------------------------------------------------------------------------
# 6. coarse-bar stop + target = ambiguity bounds (pessimistic <= optimistic)
# ----------------------------------------------------------------------------
def test_ambiguity_bounds():
    lo, hi = R.ambiguity_bounds("LONG", "100", "95", "110", slippage="0")
    assert lo == Decimal("-1") and hi == Decimal("2"), (lo, hi)   # stop -1R, target +2R
    # pessimistic primary picks the low bound
    assert cfg.PRIMARY_PATH_BOUND == "pessimistic"
    lo2, hi2 = R.ambiguity_bounds("SHORT", "100", "105", "90", slippage="0")
    assert lo2 == Decimal("-1") and hi2 == Decimal("2"), (lo2, hi2)


# ----------------------------------------------------------------------------
# 7. post-re-entry boundary doesn't bleed into the parent
# ----------------------------------------------------------------------------
def test_boundary_caps_replay():
    # Target only reached AFTER the boundary -> within window it's open, not a win.
    # Boundary at 5s; target tick at 100s. Replay must stop at boundary.
    early_boundary = T0 + timedelta(seconds=5)
    ticks = [mk_tick(0, 99.8, 100.2), mk_tick(100, 110.0, 110.4)]
    # ticks_in_range is what enforces the window; emulate it honestly here:
    R.clear_memo()
    R.ticks_in_range = lambda s, e, instrument=A.INSTRUMENT: (
        [t for t in ticks if s.timestamp() * 1000 <= t.epoch_ms <= e.timestamp() * 1000],
        [("h", "sha", "TICKS")])
    try:
        res = R.simulate("LONG", "100", "95", ["110"], T0, early_boundary,
                         entry_mode="market_on_acting", use_bidask=True, slippage="0")
        assert res["exit_kind"] != "target", "target after boundary must not count"
        assert res["path_status"] in (R.OPEN_AT_BOUNDARY,), res["path_status"]
    finally:
        restore()


# ----------------------------------------------------------------------------
# 8. T-C scenarios labelled RECONSTRUCTED_DELAY_SCENARIO
# ----------------------------------------------------------------------------
def test_tc_labelled_reconstructed():
    sig = _fake_sig(category="target_hit", targets=["110"])
    ticks = [mk_tick(0, 99.8, 100.2), mk_tick(10, 110.0, 110.4)]
    inject(ticks)
    try:
        c = LG.ledger_C(sig, 0, Decimal("0.30"))
        assert c["provenance"] == cfg.RECONSTRUCTED_DELAY_SCENARIO
        assert c["timestamp_grade"] == "T-C"
    finally:
        restore()


# ----------------------------------------------------------------------------
# 9. unknown exit not converted into a target hit
# ----------------------------------------------------------------------------
def test_unknown_not_target_hit():
    # profit_confirmed_r_unknown routes to MANAGED (stop-protected mgmt exit), never
    # a fixed target — even if a target level was reached on the path.
    sig = _fake_sig(category="profit_confirmed_r_unknown", targets=["110"],
                    mgmt_time=T0 + timedelta(seconds=20))
    ticks = [mk_tick(0, 99.8, 100.2), mk_tick(10, 110.0, 110.4), mk_tick(20, 105.0, 105.4)]
    inject(ticks)
    try:
        method, _ = LG.exit_plan(sig)
        assert method == LG.MANAGED
        c = LG.ledger_C(sig, 0, Decimal("0.30"))
        assert (c.get("detail") or {}).get("exit_kind") != "target"
    finally:
        restore()


# ----------------------------------------------------------------------------
# 10. no-chase deterioration formula, both directions
# ----------------------------------------------------------------------------
def test_nochase_formula_both_directions():
    # LONG: worse entry = HIGHER price -> positive deterioration
    d = NC.deterioration_r(1, "101", "100", "5")     # (101-100)/5 = +0.2
    assert d == Decimal("0.2"), d
    # SHORT: worse entry = LOWER price -> positive deterioration
    d2 = NC.deterioration_r(-1, "99", "100", "5")    # -1*(99-100)/5 = +0.2
    assert d2 == Decimal("0.2"), d2
    # better entry -> negative deterioration, adverse clamps to 0
    d3 = NC.deterioration_r(1, "99.5", "100", "5")   # -0.1
    assert d3 == Decimal("-0.1") and NC.adverse_r(d3) == Decimal("0")


# ----------------------------------------------------------------------------
# 11. gate thresholds logged, not winner-selected
# ----------------------------------------------------------------------------
def test_nochase_thresholds_logged_not_selected():
    sig = _fake_sig(category="target_hit", targets=["110"])
    ticks = [mk_tick(0, 100.6, 101.0), mk_tick(10, 110.0, 110.4)]  # worse entry (chased)
    inject(ticks)
    try:
        c = LG.ledger_C(sig, 0, Decimal("0.30"))
        nc = NC.evaluate(sig, c)
        # all candidate thresholds present as challengers; none marked "selected"
        assert set(nc["would_reject_by_threshold"].keys()) == {
            str(t) for t in cfg.NOCHASE_CANDIDATE_THRESHOLDS_R}
        assert "selected" not in nc and nc["rule_selection_date"] == cfg.RULE_SELECTION_DATE
        assert nc["counterfactual_r_if_taken"] == c["r_value"]   # rejected still replayed
    finally:
        restore()


# ----------------------------------------------------------------------------
# 12. gold priced / BTC deferred separately
# ----------------------------------------------------------------------------
def test_gold_btc_separate():
    import shadow_inputs as SI
    btc = _fake_sig(category="target_hit", targets=[], asset="BTCUSD")
    btc["instrument"] = SI.VALIDATED_INSTRUMENTS.get("BTCUSD")  # None
    b = LG.ledger_B(btc)
    assert b["path_status"] == "NO_VALIDATED_FEED" and b["r_value"] is None


# ----------------------------------------------------------------------------
# 13. traceability — priced results name their price source hours
# ----------------------------------------------------------------------------
def test_traceability_hours_used():
    sig = _fake_sig(category="target_hit", targets=["110"])
    ticks = [mk_tick(0, 99.8, 100.2), mk_tick(10, 110.0, 110.4)]
    inject(ticks)
    try:
        c = LG.ledger_C(sig, 0, Decimal("0.30"))
        assert (c.get("detail") or {}).get("hours_used")   # non-empty source trace
        assert c["outcome_category"] == "target_hit"
    finally:
        restore()


# ----------------------------------------------------------------------------
# helper
# ----------------------------------------------------------------------------
def _fake_sig(category, targets, mgmt_time=None, asset="XAUUSD"):
    return {
        "signal_id": "test-sig", "asset": asset, "instrument": asset if asset == "XAUUSD" else "XAUUSD",
        "direction": "LONG", "entry_low": "100", "entry_high": "100", "ref_entry": "100",
        "stop": "95", "targets": targets, "posted_at": T0, "boundary": BOUND,
        "mgmt_time": mgmt_time or (T0 + timedelta(seconds=30)),
        "category": category, "provider_r": "0.20", "provider_r_is_known": True,
    }


def _run():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = failed = 0
    print("=" * 64)
    print("  SHADOW MODE — PHASE 1b ACCEPTANCE TESTS")
    print("=" * 64)
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {fn.__name__}: {e}")
            failed += 1
        except Exception as e:  # noqa: BLE001
            import traceback
            print(f"  ERROR {fn.__name__}: {type(e).__name__}: {e}")
            traceback.print_exc()
            failed += 1
    print("-" * 64)
    print(f"  {passed} passed, {failed} failed, {len(tests)} total")
    return failed == 0


if __name__ == "__main__":
    raise SystemExit(0 if _run() else 1)
