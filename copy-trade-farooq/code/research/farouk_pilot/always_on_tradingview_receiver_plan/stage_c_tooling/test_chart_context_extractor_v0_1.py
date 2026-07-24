"""Unit tests for CHART CONTEXT EXTRACTOR v0.1 — OFFLINE, SYNTHETIC OHLC ONLY.

No real data, no I/O. Run: python test_chart_context_extractor_v0_1.py
"""

import unittest

from chart_context_extractor_v0_1 import (
    extract_context, load_ohlc, EXTRACTOR_VERSION,
)


def row(ts, o, h, l, c):
    return {"timestamp_utc": ts, "open": o, "high": h, "low": l, "close": c,
            "source": "SYNTHETIC", "timeframe": "1m"}


def flat_series(n=150, base=4000.0, rng=1.0):
    """n calm 1m candles starting 02:00Z (gives >=20 candles before the 03:00Z window)."""
    rows = []
    for m in range(n):
        hh, mm = divmod(m, 60)  # minutes past 02:00Z
        ts = f"2026-07-09T{2+hh:02d}:{mm:02d}:00.000Z"
        rows.append(row(ts, base, base + rng * 0.5, base - rng * 0.5, base))
    return rows


def inject(rows, *new_rows):
    """Replace any flat candle at the same timestamp with the injected candle."""
    ts_new = {r["timestamp_utc"] for r in new_rows}
    kept = [r for r in rows if r["timestamp_utc"] not in ts_new]
    return kept + list(new_rows)


ANCHOR = "2026-07-09T04:00:00.000Z"  # 120 min into the flat series; window 03:00-04:30Z


class TestChartContext(unittest.TestCase):

    def _assert_safe(self, rec):
        self.assertEqual(rec["extractor_version"], EXTRACTOR_VERSION)
        self.assertTrue(rec["candidate_only"])
        self.assertFalse(rec["execution_allowed"])
        self.assertFalse(rec["broker_execution_allowed"])
        self.assertFalse(rec["qst_allowed"])
        self.assertFalse(rec["order_intent"])
        self.assertFalse(rec["risk_sizing_allowed"])
        forbidden = {"order", "broker_route", "lot", "lot_size", "position_size",
                     "account_id", "risk_sizing_value", "pnl", "permit", "lease"}
        self.assertEqual(forbidden & set(rec.keys()), set())

    def test_session_proxy_with_unconfirmed_warning(self):
        rec = extract_context(load_ohlc(flat_series()), ANCHOR)
        self._assert_safe(rec)
        self.assertEqual(rec["session_context"], "ASIA_UTC_PROXY")  # 04:00Z bucket
        self.assertEqual(rec["session_warning"], "TIMEZONE_POLICY_UNCONFIRMED")
        self.assertTrue(any("TIMEZONE_POLICY_UNCONFIRMED" in m or "session_context confirmed" in m
                            for m in rec["missing_evidence"]))

    def test_displacement_detected_on_expansion(self):
        # inject a big-range candle just before the anchor (03:58Z), range 18 vs ~1
        rows = inject(flat_series(), row("2026-07-09T03:58:00.000Z", 4000, 4012, 3994, 4010))
        rec = extract_context(load_ohlc(rows), ANCHOR)
        self._assert_safe(rec)
        self.assertTrue(rec["displacement_candidate"])
        self.assertIsNotNone(rec["displacement_measure"])
        self.assertIn("NEEDS_HUMAN_REVIEW", rec["displacement_measure"]["note"])

    def test_no_displacement_on_normal_candles(self):
        rec = extract_context(load_ohlc(flat_series()), ANCHOR)
        self.assertFalse(rec["displacement_candidate"])

    def test_bullish_fvg_proxy(self):
        # 3-candle bullish gap near anchor (c1.high < c3.low), then price stays elevated
        # so no reverse imbalance forms at the anchor.
        rows = inject(flat_series(),
                      row("2026-07-09T03:57:00.000Z", 4000, 4001, 3999, 4001),   # c1 high 4001
                      row("2026-07-09T03:58:00.000Z", 4001, 4010, 4001, 4009),   # c2 big
                      row("2026-07-09T03:59:00.000Z", 4009, 4011, 4005, 4010),   # c3 low 4005 > 4001
                      row("2026-07-09T04:00:00.000Z", 4010, 4011, 4009, 4010),   # stay elevated
                      row("2026-07-09T04:01:00.000Z", 4010, 4011, 4009, 4010))
        rec = extract_context(load_ohlc(rows), ANCHOR)
        self._assert_safe(rec)
        self.assertTrue(rec["fvg_candidate"])
        self.assertEqual(rec["fvg_direction"], "bullish")
        self.assertIn("NEEDS_HUMAN_REVIEW", rec["fvg_bounds"]["note"])

    def test_bearish_fvg_proxy(self):
        # 3-candle bearish gap (c1.low > c3.high), then price stays low (no reverse gap)
        rows = inject(flat_series(),
                      row("2026-07-09T03:57:00.000Z", 4000, 4001, 3999, 3999),
                      row("2026-07-09T03:58:00.000Z", 3999, 3999, 3990, 3991),
                      row("2026-07-09T03:59:00.000Z", 3991, 3997, 3989, 3990),   # c3 high 3997 < c1 low 3999
                      row("2026-07-09T04:00:00.000Z", 3990, 3991, 3989, 3990),   # stay low
                      row("2026-07-09T04:01:00.000Z", 3990, 3991, 3989, 3990))
        rec = extract_context(load_ohlc(rows), ANCHOR)
        self.assertTrue(rec["fvg_candidate"])
        self.assertEqual(rec["fvg_direction"], "bearish")

    def test_missing_htf_warning(self):
        rec = extract_context(load_ohlc(flat_series()), ANCHOR)
        self.assertFalse(rec["htf_bias_available"])
        self.assertEqual(rec["htf_bias_warning"], "MISSING_HTF_DATA")
        self.assertTrue(any("MISSING_HTF_DATA" in m for m in rec["missing_evidence"]))

    def test_order_block_not_claimed(self):
        rec = extract_context(load_ohlc(flat_series()), ANCHOR)
        self.assertFalse(rec["order_block_candidate"])
        self.assertEqual(rec["order_block_warning"], "MISSING_ORDER_BLOCK_DETECTOR")

    def test_malformed_ohlc_returns_warning_not_fake(self):
        rec = extract_context(load_ohlc([]), ANCHOR)
        self._assert_safe(rec)
        self.assertEqual(rec["context_confidence"], "NONE")
        self.assertIsNone(rec["local_swing_high"])
        self.assertTrue(any("not fabricated" in w.lower() for w in rec["warnings"]))

    def test_unparseable_anchor_returns_warning(self):
        rec = extract_context(load_ohlc(flat_series()), "not-a-time")
        self.assertEqual(rec["context_confidence"], "NONE")
        self.assertTrue(any("unparseable anchor" in w.lower() for w in rec["warnings"]))

    def test_all_safety_flags_false(self):
        rec = extract_context(load_ohlc(flat_series()), ANCHOR)
        self._assert_safe(rec)


if __name__ == "__main__":
    unittest.main(verbosity=2)
