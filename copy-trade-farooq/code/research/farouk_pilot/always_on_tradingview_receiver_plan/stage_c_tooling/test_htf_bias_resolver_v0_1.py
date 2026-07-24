"""Unit tests for HTF BIAS RESOLVER v0.1 — OFFLINE, SYNTHETIC OHLC ONLY.

No real data, no I/O. Run: python test_htf_bias_resolver_v0_1.py
"""

import unittest

from htf_bias_resolver_v0_1 import (
    resolve_htf_bias, aggregate, RESOLVER_VERSION,
)


def row(ts, o, h, l, c):
    return {"timestamp_utc": ts, "open": o, "high": h, "low": l, "close": c}


def series(n, base=4000.0, step=0.0):
    """n 1m candles from 00:00Z, close = base + step*i (rising if step>0)."""
    rows = []
    for i in range(n):
        hh, mm = divmod(i, 60)
        ts = f"2026-07-09T{hh:02d}:{mm:02d}:00.000Z"
        c = base + step * i
        rows.append(row(ts, c, c + 0.5, c - 0.5, c))
    return rows


class TestHtfBias(unittest.TestCase):

    def _assert_safe(self, rec):
        self.assertEqual(rec["resolver_version"], RESOLVER_VERSION)
        self.assertTrue(rec["candidate_only"])
        self.assertFalse(rec["execution_allowed"])
        self.assertFalse(rec["broker_execution_allowed"])
        self.assertFalse(rec["qst_allowed"])
        self.assertFalse(rec["order_intent"])
        self.assertFalse(rec["risk_sizing_allowed"])
        self.assertFalse(rec["confirmed_farouk_htf_bias"])

    def test_aggregate_1m_to_15m_and_1h(self):
        rows = series(60)  # 60 one-minute candles = 4x15m = 1x1h
        b15 = aggregate(rows, 15)
        b1h = aggregate(rows, 60)
        self.assertEqual(len(b15), 4)
        self.assertEqual(len(b1h), 1)
        # first 15m bucket open = first candle open; high = max of its 15 candles
        self.assertEqual(b15[0]["open"], rows[0]["open"])

    def test_insufficient_data(self):
        rec = resolve_htf_bias(series(30), anchor_time_utc="2026-07-09T00:29:00.000Z")
        self._assert_safe(rec)
        self.assertEqual(rec["htf_bias_proxy"], "NEUTRAL_OR_INSUFFICIENT_DATA")
        self.assertTrue(any("too short" in w for w in rec["warnings"]))

    def test_bullish_proxy_on_rising_data(self):
        # long rising series so 15m & 1h EMAs sit below the latest close
        rows = series(60 * 40, step=0.05)  # 40h of rising 1m data
        rec = resolve_htf_bias(rows, anchor_time_utc="2026-07-10T16:00:00.000Z")
        self._assert_safe(rec)
        self.assertEqual(rec["bias_15m_proxy"], "BULLISH_PROXY")
        self.assertEqual(rec["bias_1h_proxy"], "BULLISH_PROXY")
        self.assertEqual(rec["htf_bias_proxy"], "BULLISH_PROXY")

    def test_bearish_proxy_on_falling_data(self):
        rows = series(60 * 40, base=6000.0, step=-0.05)
        rec = resolve_htf_bias(rows, anchor_time_utc="2026-07-10T16:00:00.000Z")
        self._assert_safe(rec)
        self.assertEqual(rec["bias_15m_proxy"], "BEARISH_PROXY")
        self.assertEqual(rec["bias_1h_proxy"], "BEARISH_PROXY")
        self.assertEqual(rec["htf_bias_proxy"], "BEARISH_PROXY")

    def test_all_safety_flags_false(self):
        rec = resolve_htf_bias(series(60 * 30, step=0.02))
        self._assert_safe(rec)


if __name__ == "__main__":
    unittest.main(verbosity=2)
