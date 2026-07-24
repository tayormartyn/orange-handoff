"""
test_price_foundation.py — SHADOW MODE Phase 1a acceptance tests.

Covers exactly the acceptance criteria in the brief:
  * correct before/after tick return
  * no interpolation (and no stale-price forward-fill)
  * market-closed vs data-missing
  * anomaly detection
  * hash reproducibility (+ immutability)
  * instrument / scaling validation
  * secondary cross-check (available + unavailable paths)
  * the T-C "never exact-executable" rule and the price-grade thresholds

All DETERMINISTIC and OFFLINE: every network read is replaced by synthetic .bi5
bodies or injected sources. No Dukascopy/OANDA calls. Run:
    python test_price_foundation.py        (also pytest-compatible)
"""

import lzma
import os
import shutil
import struct
import tempfile
from datetime import datetime, timezone
from decimal import Decimal

import dukascopy_adapter as A
import gold_calendar as cal
import price_cache as PC
import quote_lookup as QL
import secondary_source as SS


# ----------------------------------------------------------------------------
# Synthetic .bi5 helpers (faithful to Dukascopy: LZMA-ALONE, 20B BE records)
# ----------------------------------------------------------------------------
def make_bi5(records):
    """records: list of (ms, ask_pts, bid_pts, ask_vol, bid_vol) -> compressed body."""
    raw = b"".join(struct.pack(A.RECORD_FMT, *r) for r in records)
    return lzma.compress(raw, format=lzma.FORMAT_ALONE)


def gold_records(base_ask=4000_000, spread_pts=600, step_ms=200, n=10, start_ms=0):
    """A clean run of gold ticks: ask ~4000.000, ~$0.60 spread, every `step_ms`."""
    out = []
    for i in range(n):
        ask = base_ask + i * 10           # drift up 0.010 each tick
        bid = ask - spread_pts
        out.append((start_ms + i * step_ms, ask, bid, 1.5, 1.5))
    return out


def fake_opener(body, status=200):
    """An opener(req, timeout) returning a urllib-like response yielding `body`."""
    class _Resp:
        def __init__(self, b, s):
            self._b, self.status = b, s
        def read(self):
            return self._b
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
    return lambda req, timeout: _Resp(body, status)


THU = datetime(2026, 6, 25, 14, tzinfo=timezone.utc)   # an OPEN active hour
SAT = datetime(2026, 6, 20, 12, tzinfo=timezone.utc)   # a CLOSED hour


def _hour_result(when, records, status="TICKS"):
    """Build a HourResult directly (used to inject into quote_lookup.cache_get)."""
    body = make_bi5(records) if records else b""
    ticks = A.decode_ticks(body, when) if records else []
    anomalies = A.validate_instrument(ticks) + A.detect_anomalies(ticks, when)
    return A.HourResult(A.INSTRUMENT, A._floor_hour(when), status, ticks=ticks,
                        raw_bytes=body, anomalies=anomalies, http_status=200)


# ----------------------------------------------------------------------------
# 1. correct before/after tick return
# ----------------------------------------------------------------------------
def test_before_after_tick_return():
    recs = gold_records(n=10, step_ms=1000, start_ms=0)  # ticks at 14:00:00, :01, ... :09
    hour = _hour_result(THU, recs)
    when = datetime(2026, 6, 25, 14, 0, 4, 500000, tzinfo=timezone.utc)  # 14:00:04.5
    r = QL.lookup(when, timestamp_grade=QL.T_B, cache_get=lambda w: hour)
    assert r.market_status == QL.OPEN_WITH_TICKS, r.market_status
    # before = tick at :04.000, after = tick at :05.000
    assert r.before.dt.second == 4 and r.after.dt.second == 5, (r.before.dt, r.after.dt)
    assert r.before_gap_ms == 500 and r.after_gap_ms == 500, (r.before_gap_ms, r.after_gap_ms)
    assert r.quote_gap_ms == 1000, r.quote_gap_ms
    # before/after are the ACTUAL ticks, with real bid/ask (not synthesized)
    assert r.before.ask == Decimal("4000.040") and r.after.ask == Decimal("4000.050")


# ----------------------------------------------------------------------------
# 2. no interpolation / no forward-fill
# ----------------------------------------------------------------------------
def test_no_interpolation_returns_real_ticks_only():
    recs = gold_records(n=5, step_ms=1000)
    hour = _hour_result(THU, recs)
    when = datetime(2026, 6, 25, 14, 0, 2, 500000, tzinfo=timezone.utc)
    r = QL.lookup(when, timestamp_grade=QL.T_B, cache_get=lambda w: hour)
    # The result exposes two REAL ticks; there is no single "price" field at all.
    assert not hasattr(r, "price")
    mids = {(r.before.bid + r.before.ask) / 2, (r.after.bid + r.after.ask) / 2}
    assert len(mids) == 2  # two distinct real quotes, nothing averaged into one


def test_no_forward_fill_when_only_one_side():
    # `when` AFTER the last tick of the hour, and the next hour is EMPTY (closed/gap):
    # we must NOT carry the last tick forward. One-sided -> P-U.
    recs = gold_records(n=3, step_ms=1000, start_ms=0)  # last tick at 14:00:02
    this_hour = _hour_result(THU, recs)
    empty_next = A.HourResult(A.INSTRUMENT, A._floor_hour(THU), "EMPTY",
                              ticks=[], raw_bytes=b"", http_status=200)
    def cg(w):
        return this_hour if A._floor_hour(w) == A._floor_hour(THU) else empty_next
    when = datetime(2026, 6, 25, 14, 30, 0, tzinfo=timezone.utc)  # long after last tick
    r = QL.lookup(when, timestamp_grade=QL.T_B, cache_get=cg)
    assert r.after is None
    assert r.price_grade == QL.P_U, r.price_grade
    assert not r.exact_executable


# ----------------------------------------------------------------------------
# 3. market-closed vs data-missing
# ----------------------------------------------------------------------------
def test_market_closed_vs_data_missing():
    empty = A.HourResult(A.INSTRUMENT, A._floor_hour(SAT), "EMPTY", ticks=[],
                         raw_bytes=b"", http_status=200)
    # Saturday + empty feed -> MARKET_CLOSED (expected)
    r_closed = QL.lookup(SAT.replace(hour=12), timestamp_grade=QL.T_C,
                         cache_get=lambda w: empty)
    assert r_closed.market_status == QL.MARKET_CLOSED, r_closed.market_status
    # Open Thursday hour + empty feed -> DATA_MISSING (a problem, explained)
    empty_thu = A.HourResult(A.INSTRUMENT, A._floor_hour(THU), "EMPTY", ticks=[],
                             raw_bytes=b"", http_status=200)
    r_missing = QL.lookup(THU.replace(hour=14), timestamp_grade=QL.T_C,
                          cache_get=lambda w: empty_thu)
    assert r_missing.market_status == QL.DATA_MISSING, r_missing.market_status


def test_calendar_breaks_weekends_holidays():
    # Saturday closed
    assert not cal.session_status(SAT).is_open
    # Daily settlement break (Thu 17:30 ET = 21:30 UTC EDT)
    assert cal.session_status(datetime(2026, 6, 25, 21, 30, tzinfo=timezone.utc)).status == cal.DAILY_BREAK
    # Christmas full close
    assert not cal.session_status(datetime(2026, 12, 25, 15, tzinfo=timezone.utc)).is_open
    # Memorial Day = OPEN but thin (gold trades thin on US holidays, not closed)
    md = cal.session_status(datetime(2026, 5, 25, 13, 50, tzinfo=timezone.utc))
    assert md.is_open and md.thin_liquidity and md.holiday == "Memorial Day"
    # Sunday reopen after 18:00 ET (22:00 UTC EDT)
    assert cal.session_status(datetime(2026, 6, 21, 23, tzinfo=timezone.utc)).is_open


# ----------------------------------------------------------------------------
# 4. anomaly detection
# ----------------------------------------------------------------------------
def test_anomaly_detection():
    recs = [
        (0,    4000_000, 4000_600, 1, 1),   # ASK<BID (ask 4000.000 < bid 4000.600)
        (100,  4001_000, 4000_400, 1, 1),   # ok
        (100,  4001_000, 4000_400, 1, 1),   # DUPLICATE timestamp
        (50,   4001_000, 4000_400, 1, 1),   # out-of-order (ms 50 after 100, pre-sort)
        (200,  4500_000, 4499_400, 1, 1),   # PRICE JUMP (~+499)
    ]
    ticks = A.decode_ticks(make_bi5(recs), THU)
    anoms = A.detect_anomalies(ticks, THU)
    blob = " | ".join(anoms)
    assert "ASK<BID" in blob, blob
    assert "DUPLICATE" in blob, blob
    assert "JUMP" in blob, blob
    # zero/negative price
    z = A.decode_ticks(make_bi5([(0, 0, 0, 1, 1)]), THU)
    assert any("ZERO/NEG" in a for a in A.detect_anomalies(z, THU))


def test_truncated_stream_rejected():
    body = make_bi5(gold_records(n=3))
    raw = lzma.decompress(body)
    truncated = lzma.compress(raw[:-3], format=lzma.FORMAT_ALONE)  # not a 20B multiple
    try:
        A.decode_ticks(truncated, THU)
        assert False, "expected ValueError for truncated stream"
    except ValueError as e:
        assert "truncated" in str(e), e


# ----------------------------------------------------------------------------
# 5. hash reproducibility + immutability
# ----------------------------------------------------------------------------
def test_hash_reproducibility_and_immutability():
    tmp = tempfile.mkdtemp(prefix="pcache_")
    old_dir = PC.CACHE_DIR
    PC.CACHE_DIR = tmp
    try:
        body = make_bi5(gold_records(n=20))
        # MISS -> fetch (fake) + store
        r1 = PC.get_hour(THU, opener=fake_opener(body))
        assert r1.status == "TICKS" and len(r1.ticks) == 20
        # reproducible: re-decode cached raw == stored ticks, hash matches
        ok, probs = PC.verify_cached(A._floor_hour(THU))
        assert ok, probs
        # HIT -> identical normalised ticks
        r2 = PC.get_hour(THU)
        assert PC._ticks_blob(r1.ticks) == PC._ticks_blob(r2.ticks)
        # immutability: refresh with DIFFERENT bytes -> HashChangedError, no overwrite
        tampered = make_bi5(gold_records(n=21))
        raised = False
        try:
            PC.get_hour(THU, refresh=True, opener=fake_opener(tampered))
        except PC.HashChangedError:
            raised = True
        assert raised, "expected HashChangedError on changed upstream bytes"
        ok2, _ = PC.verify_cached(A._floor_hour(THU))
        assert ok2, "cache must remain intact after a rejected change"
    finally:
        PC.CACHE_DIR = old_dir
        shutil.rmtree(tmp, ignore_errors=True)


# ----------------------------------------------------------------------------
# 6. instrument / scaling validation
# ----------------------------------------------------------------------------
def test_instrument_validation_catches_bad_scale_and_swap():
    # Wrong scale: points that map to ~$40,000 (10x too big) -> SCALING flag
    bad_scale = A.decode_ticks(make_bi5([(0, 40000_000, 39999_400, 1, 1)]), THU)
    assert any("SCALING" in a or "INSTRUMENT" in a for a in A.validate_instrument(bad_scale))
    # Field swap: bid systematically above ask -> negative median spread -> FIELD-SWAP
    swapped = A.decode_ticks(make_bi5([(0, 4000_000, 4001_000, 1, 1),
                                       (1, 4000_000, 4001_000, 1, 1)]), THU)
    assert any("FIELD-SWAP" in a for a in A.validate_instrument(swapped))
    # A clean gold hour validates with no instrument anomalies
    good = A.decode_ticks(make_bi5(gold_records(n=10)), THU)
    assert A.validate_instrument(good) == []


# ----------------------------------------------------------------------------
# 7. secondary cross-check (available + unavailable)
# ----------------------------------------------------------------------------
def test_secondary_unavailable_is_honest_not_fatal():
    src = SS.NullSource("no creds in test")
    cc = SS.cross_check(Decimal("4000"), THU, src)
    assert cc["status"] == "unavailable"


def test_secondary_agrees_and_diverges():
    class FakeSrc(SS.SecondarySource):
        name = "fake"
        def __init__(self, mid): self._mid = mid
        def is_available(self): return True, "fake configured"
        def mid_at(self, when): return Decimal(self._mid), {"time": when.isoformat()}
    agree = SS.cross_check(Decimal("4000.50"), THU, FakeSrc("4000.30"))
    assert agree["status"] == "agrees", agree
    diverge = SS.cross_check(Decimal("4000.50"), THU, FakeSrc("4050.00"))
    assert diverge["status"] == "diverges", diverge


# ----------------------------------------------------------------------------
# 8. the T-C rule + price-grade thresholds (core honesty guarantees)
# ----------------------------------------------------------------------------
def test_tc_can_never_be_exact_executable():
    recs = gold_records(n=10, step_ms=200)  # dense -> P-A
    hour = _hour_result(THU, recs)
    when = datetime(2026, 6, 25, 14, 0, 1, tzinfo=timezone.utc)
    tc = QL.lookup(when, timestamp_grade=QL.T_C, cache_get=lambda w: hour)
    tb = QL.lookup(when, timestamp_grade=QL.T_B, cache_get=lambda w: hour)
    assert tc.price_grade == QL.P_A and tb.price_grade == QL.P_A
    assert tc.exact_executable is False     # T-C can NEVER be exact-executable
    assert tb.exact_executable is True      # receipt-grade + P-A can be


def test_price_grade_thresholds():
    from datetime import timedelta
    def gap_grade(gap_ms):
        recs = [(0, 4000_000, 4000_600, 1, 1), (gap_ms, 4000_100, 4000_700, 1, 1)]
        hour = _hour_result(THU, recs)
        when = THU.replace(hour=14) + timedelta(milliseconds=gap_ms / 2)  # between the two ticks
        return QL.lookup(when, timestamp_grade=QL.T_B, cache_get=lambda w: hour).price_grade
    assert gap_grade(800) == QL.P_A     # <=1s
    assert gap_grade(3000) == QL.P_B    # <=5s
    assert gap_grade(9000) == QL.P_C    # >5s


# ----------------------------------------------------------------------------
# Minimal runner (mirrors test_archive.py)
# ----------------------------------------------------------------------------
def _run():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = failed = 0
    print("=" * 64)
    print("  SHADOW MODE — PHASE 1a PRICE-FOUNDATION ACCEPTANCE TESTS")
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
