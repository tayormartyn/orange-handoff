"""Unit tests for OUTCOME MATCHER v0.1 — OFFLINE, SYNTHETIC OHLC ONLY.

No real price data, no I/O. Run: python test_outcome_matcher_v0_1.py
"""

import unittest

from outcome_matcher_v0_1 import match_one, match_all, MATCHER_VERSION, _load_ohlc


def candle(t, o, h, low, c):
    return {"timestamp_utc": t, "open": o, "high": h, "low": low, "close": c,
            "source": "SYNTHETIC", "timeframe": "1m"}


def cand(ctype, anchor, hint):
    return {"candidate_id": f"{ctype}-0000", "candidate_type": ctype,
            "window_start_utc": anchor, "window_end_utc": anchor, "direction_hint": hint}


# A 1-minute synthetic series starting 04:12:00Z. entry candle close = 4000.0
# Prices then rise to a high of 4010 and dip to a low of 3995 within 15m.
BASE = "2026-07-09T04:12:00.000Z"


def series_up():
    rows = [candle("2026-07-09T04:12:00.000Z", 4000, 4001, 3999.5, 4000.0)]
    # minutes 1..120 after anchor
    highs = {5: 4004, 10: 4010, 20: 4012, 40: 4015, 70: 4020, 118: 4030}
    lows = {3: 3995, 25: 3990}
    for m in range(1, 121):
        hh, mm = divmod(12 + m, 60)
        ts = f"2026-07-09T{4+hh:02d}:{mm:02d}:00.000Z"
        h = highs.get(m, 4002)
        low = lows.get(m, 3999)
        rows.append(candle(ts, 4000, h, low, 4001 + (m * 0.05)))
    return rows


class TestOutcomeMatcher(unittest.TestCase):

    def _assert_safe(self, rec):
        self.assertEqual(rec["matcher_version"], MATCHER_VERSION)
        self.assertTrue(rec["candidate_only"])
        self.assertFalse(rec["execution_allowed"])
        self.assertFalse(rec["broker_execution_allowed"])
        self.assertFalse(rec["qst_allowed"])
        self.assertFalse(rec["order_intent"])
        self.assertFalse(rec["risk_sizing_allowed"])
        forbidden = {"lot", "lot_size", "position_size", "account_id", "account",
                     "risk", "risk_sizing", "broker_route", "route", "order",
                     "order_id", "permit", "lease", "sl", "tp", "pnl"}
        self.assertEqual(forbidden & set(rec.keys()), set())

    def test_long_favourable_high_adverse_low(self):
        rows = series_up()
        rec = match_one(cand("ALIGNED_CHOCH_TO_A", BASE, "LONG"), _load_ohlc(rows))
        self._assert_safe(rec)
        self.assertEqual(rec["entry_reference_price"], 4000.0)
        # within 15m: high reaches 4010 -> fav = +10; low 3995 -> adverse = -5
        self.assertAlmostEqual(rec["max_favourable_excursion_15m"], 10.0, places=3)
        self.assertAlmostEqual(rec["max_adverse_excursion_15m"], -5.0, places=3)
        # favourable must be positive, adverse must be <= 0 for LONG
        self.assertGreater(rec["max_favourable_excursion_15m"], 0)
        self.assertLessEqual(rec["max_adverse_excursion_15m"], 0)

    def test_short_favourable_low_adverse_high(self):
        rows = series_up()  # price mostly rises -> bad for a short
        rec = match_one(cand("ALIGNED_CHOCH_TO_A", BASE, "SHORT"), _load_ohlc(rows))
        self._assert_safe(rec)
        # SHORT: favourable = entry - low = 4000 - 3995 = +5 ; adverse = entry - high = 4000 - 4010 = -10
        self.assertAlmostEqual(rec["max_favourable_excursion_15m"], 5.0, places=3)
        self.assertAlmostEqual(rec["max_adverse_excursion_15m"], -10.0, places=3)

    def test_missing_window_returns_warning_not_fake(self):
        rec = match_one(cand("ALIGNED_CHOCH_TO_A", BASE, "LONG"), _load_ohlc([]))
        self._assert_safe(rec)
        self.assertEqual(rec["data_quality"], "NO_DATA")
        self.assertIsNone(rec["entry_reference_price"])
        self.assertIsNone(rec["max_favourable_excursion_15m"])
        self.assertTrue(any("not fabricated" in w.lower() or "no ohlc" in w.lower()
                            for w in rec["warnings"]))

    def test_anchor_chooses_first_candle_at_or_after(self):
        # anchor 04:11:30Z, first candle 04:12:00Z -> entry uses that candle's close
        rows = series_up()
        rec = match_one(cand("X", "2026-07-09T04:11:30.000Z", "LONG"), _load_ohlc(rows))
        self.assertEqual(rec["entry_reference_price"], 4000.0)

    def test_anchor_after_all_data_no_fake(self):
        rows = series_up()
        rec = match_one(cand("X", "2026-07-09T23:00:00.000Z", "LONG"), _load_ohlc(rows))
        self.assertEqual(rec["data_quality"], "NO_DATA")
        self.assertIsNone(rec["entry_reference_price"])
        self.assertTrue(any("outside available" in w.lower() for w in rec["warnings"]))

    def test_partial_coverage_flagged(self):
        # only 20 minutes of data -> 15m FULL-ish but 30/60/120 partial
        rows = series_up()[:21]  # anchor candle + 20 minutes
        rec = match_one(cand("X", BASE, "LONG"), _load_ohlc(rows))
        self.assertIn(rec["data_quality"], ("PARTIAL",))
        self.assertIsNotNone(rec["max_favourable_excursion_15m"])
        self.assertIsNone(rec["final_close_delta_120m"])

    def test_all_safety_flags_false_and_no_order_fields(self):
        rows = series_up()
        for hint in ("LONG", "SHORT"):
            rec = match_one(cand("ALIGNED_CHOCH_TO_A", BASE, hint), _load_ohlc(rows))
            self._assert_safe(rec)

    def test_match_all_shape(self):
        rows = series_up()
        cands = [cand("ALIGNED_CHOCH_TO_A", BASE, "LONG"),
                 cand("BPR_TO_A_CONTEXT", BASE, "SHORT")]
        res = match_all(cands, rows)
        self.assertEqual(len(res), 2)
        for r in res:
            self._assert_safe(r)


if __name__ == "__main__":
    unittest.main(verbosity=2)
