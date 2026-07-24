"""Unit tests for ORDER BLOCK PROXY DETECTOR v0.1 — OFFLINE, SYNTHETIC OHLC ONLY.

No real data, no I/O. Run: python test_order_block_proxy_detector_v0_1.py
"""

import unittest

from order_block_proxy_detector_v0_1 import detect_order_block_proxy, DETECTOR_VERSION


def row(ts, o, h, l, c):
    return {"timestamp_utc": ts, "open": o, "high": h, "low": l, "close": c}


def flat(n=180, base=4000.0):
    """n calm 1m candles from 00:00Z (continuous lead-in up to 02:59Z for ATR baseline)."""
    rows = []
    for i in range(n):
        hh, mm = divmod(i, 60)
        rows.append(row(f"2026-07-09T{hh:02d}:{mm:02d}:00.000Z", base, base + 0.5, base - 0.5, base))
    return rows


def at_min(m):
    """Timestamp m minutes past 02:00Z (OB/anchor candles live at 03:00Z+)."""
    hh, mm = divmod(m, 60)
    return f"2026-07-09T{2+hh:02d}:{mm:02d}:00.000Z"


ANCHOR = at_min(75)  # 03:15Z; flat() fills 00:00-02:59Z, OB action at 03:00Z+


class TestOBProxy(unittest.TestCase):

    def _assert_safe(self, rec):
        self.assertEqual(rec["detector_version"], DETECTOR_VERSION)
        self.assertTrue(rec["requires_human_review"])
        self.assertTrue(rec["candidate_only"])
        self.assertFalse(rec["execution_allowed"])
        self.assertFalse(rec["broker_execution_allowed"])
        self.assertFalse(rec["qst_allowed"])
        self.assertFalse(rec["order_intent"])
        self.assertFalse(rec["risk_sizing_allowed"])
        self.assertEqual(rec["confidence"], "LOW")  # never above LOW
        forbidden = {"entry", "stop_loss", "take_profit", "sl", "tp", "lot", "lot_size",
                     "position_size", "order", "broker_route", "account_id", "risk_sizing_value"}
        self.assertEqual(forbidden & set(rec.keys()), set())

    def test_bullish_ob_proxy_detected(self):
        rows = flat()
        # OB (bearish) at 03:00Z (min60), then bullish displacement at 03:01Z, then rise
        rows.append(row(at_min(60), 4000, 4000.5, 3999.0, 3999.2))   # bearish OB candle
        rows.append(row(at_min(61), 3999.2, 4010.0, 3999.0, 4009.5))  # bullish displacement (range 11)
        rows.append(row(at_min(62), 4009.5, 4011.0, 4009.0, 4010.5))  # continue up (no re-entry)
        rows.append(row(at_min(63), 4010.5, 4012.0, 4010.0, 4011.5))
        rec = detect_order_block_proxy(rows, ANCHOR, "LONG")
        self._assert_safe(rec)
        self.assertTrue(rec["order_block_proxy_found"])
        self.assertEqual(rec["proxy_direction"], "BULLISH_OB_PROXY")
        self.assertTrue(rec["displacement_after_candidate"])
        self.assertIsNotNone(rec["candidate_zone_high"])
        self.assertFalse(rec["mitigation_touched"])  # never re-entered

    def test_bearish_ob_proxy_detected(self):
        rows = flat()
        rows.append(row(at_min(60), 4000, 4001.0, 3999.5, 4000.8))   # bullish OB candle
        rows.append(row(at_min(61), 4000.8, 4001.0, 3990.0, 3990.5))  # bearish displacement (range 11)
        rows.append(row(at_min(62), 3990.5, 3991.0, 3989.0, 3989.5))  # continue down
        rows.append(row(at_min(63), 3989.5, 3990.0, 3988.0, 3988.5))
        rec = detect_order_block_proxy(rows, ANCHOR, "SHORT")
        self._assert_safe(rec)
        self.assertTrue(rec["order_block_proxy_found"])
        self.assertEqual(rec["proxy_direction"], "BEARISH_OB_PROXY")

    def test_no_ob_proxy_without_displacement(self):
        rows = flat()  # all calm, no displacement
        rec = detect_order_block_proxy(rows, ANCHOR, "LONG")
        self._assert_safe(rec)
        self.assertFalse(rec["order_block_proxy_found"])
        self.assertTrue(any("displacement" in m for m in rec["missing_evidence"]))

    def test_malformed_ohlc_returns_warning(self):
        rec = detect_order_block_proxy([], ANCHOR, "LONG")
        self._assert_safe(rec)
        self.assertFalse(rec["order_block_proxy_found"])
        self.assertTrue(any("not fabricated" in w.lower() for w in rec["warnings"]))

    def test_zone_bounds_descriptive_only(self):
        rows = flat()
        rows.append(row(at_min(60), 4000, 4000.5, 3999.0, 3999.2))
        rows.append(row(at_min(61), 3999.2, 4010.0, 3999.0, 4009.5))
        rows.append(row(at_min(62), 4009.5, 4011.0, 4009.0, 4010.5))
        rec = detect_order_block_proxy(rows, ANCHOR, "LONG")
        # zone present but no entry/SL/TP fields exist
        self.assertIsNotNone(rec["candidate_zone_high"])
        self.assertIn("descriptive", rec["note"])
        for k in ("entry", "stop_loss", "take_profit", "sl", "tp"):
            self.assertNotIn(k, rec)

    def test_requires_human_review_and_flags(self):
        rec = detect_order_block_proxy(flat(), ANCHOR, "SHORT")
        self._assert_safe(rec)
        self.assertTrue(rec["requires_human_review"])

    def test_non_directional_hint(self):
        rec = detect_order_block_proxy(flat(), ANCHOR, None)
        self._assert_safe(rec)
        self.assertFalse(rec["order_block_proxy_found"])
        self.assertTrue(any("directional" in m for m in rec["missing_evidence"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
