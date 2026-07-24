"""
test_signal_quality.py — tests for the signal-quality confidence filter.

Covers:
  * classify(): HIGH / NORMAL / LOW from the trader's own risk flags, the NORMAL
    default, mixed cues cancelling to NORMAL, and robust matching (hyphens,
    word boundaries).
  * the router tag: confidence rides on the RoutingDecision; by default a LOW
    signal is still ROUTED (info only); with SKIP_LOW_CONFIDENCE on it goes to
    REVIEW.
  * the logged column: confidence is written into paper_log.csv.
  * review.py / status.py: the BY CONFIDENCE breakdown counts HIGH/NORMAL/LOW.

PAPER mode only. Uses throwaway temp files; never touches the real paper_log.csv.

Run directly (no pytest needed):

    python test_signal_quality.py
"""

import csv
import os
import tempfile
from decimal import Decimal

import config
import signal_quality as sq
import module_router as router
import module_d_logger as logger
import module_c_risk as risk
import review
import status
from models import Signal


# ----------------------------------------------------------------------------
# classify()
# ----------------------------------------------------------------------------
def test_high_cues_tag_high():
    assert sq.classify("XAUUSD LONG — A+ setup, 100% confident").level == sq.HIGH
    assert sq.classify("clean setup, strong, high probability").level == sq.HIGH


def test_low_cues_tag_low():
    assert sq.classify("GBPJPY SHORT high-risk, low lot").level == sq.LOW
    assert sq.classify("against the trend, be careful, news coming").level == sq.LOW


def test_no_cues_default_normal():
    assert sq.classify("SOL LONG zone 131-134 SL 127 TP 138").level == sq.NORMAL
    assert sq.classify("").level == sq.NORMAL


def test_mixed_cues_cancel_to_normal():
    # one strong + one caution -> tie -> NORMAL (we don't guess)
    r = sq.classify("A+ setup but high-risk")
    assert r.level == sq.NORMAL, r.summary()
    assert r.high_hits and r.low_hits


def test_hyphen_and_word_boundary_matching():
    # hyphen vs space must not matter
    assert sq.classify("this is high risk").level == sq.LOW
    assert sq.classify("this is high-risk").level == sq.LOW
    # word boundary: "strong" must not fire inside "strongest"
    assert sq.classify("the strongest resistance is here").level == sq.NORMAL


def test_overlapping_cues_not_double_counted():
    # "a+ setup" present shouldn't also count "a+"; still HIGH, but counted once
    r = sq.classify("A+ setup")
    assert r.level == sq.HIGH
    assert "a+" not in [c.lower() for c in r.high_hits]


# ----------------------------------------------------------------------------
# Router tagging + the optional SKIP switch
# ----------------------------------------------------------------------------
def _sig(raw):
    return Signal(ticker="XAUUSD", pair="XAUUSD", direction="LONG", asset_class="METAL",
                  entry_low=Decimal("4000"), entry_high=Decimal("4010"),
                  stop_loss=Decimal("3980"), targets=[Decimal("4030")],
                  raw_text=raw, source="FAROUK")


def test_router_tags_confidence():
    assert router.route(_sig("A+ setup, strong")).confidence == sq.HIGH
    assert router.route(_sig("high-risk, low lot")).confidence == sq.LOW
    assert router.route(_sig("plain entry")).confidence == sq.NORMAL


def test_low_is_info_only_by_default():
    # Default config: SKIP_LOW_CONFIDENCE off -> LOW signals still ROUTE.
    assert config.SKIP_LOW_CONFIDENCE is False
    d = router.route(_sig("high-risk, low lot"))
    assert d.confidence == sq.LOW
    assert not d.needs_review, d.review_reasons


def test_skip_low_confidence_routes_low_to_review():
    original = config.SKIP_LOW_CONFIDENCE
    try:
        config.SKIP_LOW_CONFIDENCE = True
        d = router.route(_sig("high-risk, low lot"))
        assert d.confidence == sq.LOW
        assert d.needs_review
        assert any("SKIP_LOW_CONFIDENCE" in r for r in d.review_reasons)
        # A HIGH signal is unaffected by the switch.
        assert not router.route(_sig("A+ setup, strong")).needs_review
    finally:
        config.SKIP_LOW_CONFIDENCE = original


# ----------------------------------------------------------------------------
# The logged column (round-trip through the logger)
# ----------------------------------------------------------------------------
def test_confidence_is_logged():
    sig = _sig("XAUUSD LONG A+ setup, 100% confident")
    ticket = risk.size_signal(sig, Decimal(config.POT_SIZE))
    decision = router.route(sig, channel="Farouk Gold")
    # Use a path that does NOT exist yet, so the logger creates it WITH a header
    # (it only writes the header for a brand-new file).
    tmpdir = tempfile.mkdtemp(prefix="qtest_")
    path = os.path.join(tmpdir, "paper_log.csv")
    try:
        logger.log_ticket(ticket, path=path, routing=decision)
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert "confidence" in rows[0]
        assert rows[0]["confidence"] == sq.HIGH
    finally:
        os.remove(path)
        os.rmdir(tmpdir)


# ----------------------------------------------------------------------------
# review.py / status.py breakdown
# ----------------------------------------------------------------------------
def _write_log(path, specs):
    """specs: list of (confidence, realised_rr). Writes a minimal valid log."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=logger.FIELDNAMES)
        w.writeheader()
        for i, (conf, rr) in enumerate(specs):
            row = {k: "" for k in logger.FIELDNAMES}
            row.update(
                timestamp=f"2026-06-{i+1:02d}T12:00:00+00:00",
                ticker="XAUUSD", asset_class="METAL", direction="LONG",
                source="FAROUK", confidence=conf,
                entry="4000", sl_price="3980", dollar_risk="140",
                realised_rr=rr, outcome="WIN" if Decimal(rr) > 0 else "LOSS",
            )
            w.writerow(row)


def test_review_breaks_down_by_confidence():
    fd, path = tempfile.mkstemp(suffix=".csv", prefix="qtest_")
    os.close(fd)
    try:
        # HIGH wins (+2R), LOW loses (-1R), NORMAL flat-ish (+0.5R)
        _write_log(path, [("HIGH", "2"), ("HIGH", "2"),
                          ("LOW", "-1"), ("LOW", "-1"),
                          ("NORMAL", "0.5")])
        report = review.build_report(path)
        assert "BY CONFIDENCE" in report
        # All three levels appear as their own block.
        for lvl in ("HIGH", "NORMAL", "LOW"):
            assert lvl in report
        # The plain-English HIGH-vs-LOW read should fire and favour HIGH.
        assert "HIGH is beating LOW" in report
    finally:
        os.remove(path)


def test_status_breaks_down_by_confidence():
    fd, path = tempfile.mkstemp(suffix=".csv", prefix="qtest_")
    os.close(fd)
    try:
        _write_log(path, [("HIGH", "2"), ("LOW", "-1"), ("NORMAL", "1")])
        dash = status.build_dashboard(path)
        assert "BY CONFIDENCE" in dash
        assert "HIGH" in dash and "LOW" in dash
    finally:
        os.remove(path)


def test_old_rows_without_confidence_count_as_normal():
    """A row with no confidence cell (pre-filter log) must read as NORMAL, not crash."""
    fd, path = tempfile.mkstemp(suffix=".csv", prefix="qtest_")
    os.close(fd)
    try:
        # Header WITHOUT the confidence column (older log shape).
        fields = [c for c in logger.FIELDNAMES if c != "confidence"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            row = {k: "" for k in fields}
            row.update(timestamp="2026-06-01T12:00:00+00:00", ticker="XAUUSD",
                       asset_class="METAL", direction="LONG", source="FAROUK",
                       entry="4000", sl_price="3980", dollar_risk="140",
                       realised_rr="2", outcome="WIN")
            w.writerow(row)
        closed, _missed, _bad = review.load_closed_trades(path)
        assert closed[0]["confidence"] == "NORMAL"
    finally:
        os.remove(path)


# ----------------------------------------------------------------------------
# Minimal runner (works without pytest)
# ----------------------------------------------------------------------------
def _run():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = failed = 0
    print("=" * 64)
    print("  SIGNAL-QUALITY FILTER TESTS")
    print("=" * 64)
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
        except Exception as e:                       # noqa: BLE001
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print("-" * 64)
    print(f"  {passed} passed, {failed} failed, {len(tests)} total")
    print("=" * 64)
    return failed == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if _run() else 1)
