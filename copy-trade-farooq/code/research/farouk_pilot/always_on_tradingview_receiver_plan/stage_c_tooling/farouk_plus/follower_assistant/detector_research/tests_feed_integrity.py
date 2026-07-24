"""Phase 6 — TradingView / 1m FEED-INTEGRITY HARNESS (RESEARCH-ONLY).

Actively injects each named feed defect and asserts the causal aggregation stays correct/deterministic:
missing bars, duplicates, out-of-order, reconnect, restart consistency, cursor consistency, late
corrections, timestamp normalization, incomplete 5m groups. Maintains:
  TRADINGVIEW_PRICE_SEMANTICS_UNVERIFIED / BROKER_EXECUTION_EQUIVALENCE_UNPROVEN
"""
from __future__ import annotations

import io
import os
import sys
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import detector_features as F                                     # noqa: E402

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


def clean_5m():
    # two complete 5m buckets (0-299, 300-599) + one open bucket (600-)
    m1 = []
    for t in range(0, 900, 60):
        m1.append(bar(t, 10, 11, 9, 10))
    return m1


def test_incomplete_5m_dropped():
    out = F.resample_1m(clean_5m(), 300)
    ok("only COMPLETED 5m buckets returned (open bucket dropped)", [b[0] for b in out] == [0, 300])


def test_missing_bars():
    m1 = [bar(0, 10, 12, 9, 11), bar(120, 11, 13, 10, 12), bar(240, 12, 14, 11, 13),   # bucket 0 missing 60,180
          bar(300, 13, 15, 12, 14), bar(360, 14, 16, 13, 15), bar(660, 1, 1, 1, 1)]     # bucket 300 partial + open
    out = F.resample_1m(m1, 300)
    ok("missing 1m bars: bucket still aggregates, no crash", [b[0] for b in out] == [0, 300])
    ok("missing bars: high/low from present members", out[0][2] == D("14") and out[0][3] == D("9"))


def test_duplicate_bars():
    m1 = [bar(0, 10, 11, 9, 10), bar(60, 11, 12, 10, 11), bar(60, 11, 20, 5, 15),      # duplicate ts=60 (correction)
          bar(300, 1, 1, 1, 1)]
    out = F.resample_1m(m1, 300)
    ok("duplicate ts merged (high=max across dupes)", out[0][2] == D("20"))
    ok("duplicate ts merged (low=min across dupes)", out[0][3] == D("5"))


def test_out_of_order_invariance():
    ordered = [bar(t, 10, 11 + (t // 60), 9 - (t // 60), 10) for t in range(0, 300, 60)] + [bar(300, 1, 1, 1, 1)]
    shuffled = [ordered[i] for i in (3, 0, 4, 2, 1, 5)]
    a = F.resample_1m(ordered, 300)
    b = F.resample_1m(shuffled, 300)
    ok("out-of-order input -> identical aggregate (H/L order-independent)",
       a[0][2] == b[0][2] and a[0][3] == b[0][3])


def test_late_correction_close():
    # a late correction for the LAST 1m of a bucket must set the bucket close (max-ts wins)
    m1 = [bar(0, 10, 11, 9, 10), bar(240, 12, 13, 11, 12), bar(300, 1, 1, 1, 1)]
    base = F.resample_1m(m1, 300)
    m1c = [bar(0, 10, 11, 9, 10), bar(240, 12, 13, 11, 99), bar(300, 1, 1, 1, 1)]  # corrected close 99
    corr = F.resample_1m(m1c, 300)
    ok("late correction updates bucket close", base[0][4] == D("12") and corr[0][4] == D("99"))


def test_reconnect_gap():
    # a reconnect leaves a multi-bucket gap; buckets each side must still be correct + completed-only
    m1 = [bar(0, 10, 11, 9, 10), bar(60, 10, 12, 9, 11),                 # bucket 0
          bar(1800, 20, 22, 19, 21), bar(1860, 21, 23, 20, 22),          # bucket 1800 after gap
          bar(2100, 1, 1, 1, 1)]                                         # open bucket
    out = F.resample_1m(m1, 300)
    ok("reconnect gap: only completed buckets, correct boundaries", [b[0] for b in out] == [0, 1800])


def test_restart_determinism():
    m1 = clean_5m()
    ok("restart determinism: identical input -> identical resample", F.resample_1m(m1, 300) == F.resample_1m(m1, 300))
    ts = 500
    ok("cursor/causal determinism: causal set stable across calls",
       F.completed_before(F.resample_1m(m1, 300), ts, 300) == F.completed_before(F.resample_1m(m1, 300), ts, 300))


def test_timestamp_normalization():
    # off-boundary 1m timestamps must floor into the correct UTC bucket
    m1 = [bar(0, 10, 11, 9, 10), bar(299, 10, 11, 9, 10), bar(300, 1, 1, 1, 1), bar(599, 1, 2, 0, 1), bar(600, 5, 5, 5, 5)]
    out = F.resample_1m(m1, 300)
    ok("UTC floor buckets (0 and 300)", [b[0] for b in out] == [0, 300])


def test_completed_before_cutoff():
    bars5 = F.resample_1m(clean_5m(), 300)   # buckets 0, 300
    # at decision ts=350, the 300 bucket (closes 600) is NOT yet complete -> excluded
    ok("5m bar available only after its close <= decision_ts", F.completed_before(bars5, 350, 300) == [b for b in bars5 if b[0] + 300 <= 350])
    ok("only the 0 bucket qualifies at ts=350", [b[0] for b in F.completed_before(bars5, 350, 300)] == [0])


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    for fn in [test_incomplete_5m_dropped, test_missing_bars, test_duplicate_bars,
               test_out_of_order_invariance, test_late_correction_close, test_reconnect_gap,
               test_restart_determinism, test_timestamp_normalization, test_completed_before_cutoff]:
        fn()
    print(f"\n{PASS} passed, {FAIL} failed")
    print("TRADINGVIEW_PRICE_SEMANTICS_UNVERIFIED | BROKER_EXECUTION_EQUIVALENCE_UNPROVEN")
    sys.exit(1 if FAIL else 0)
