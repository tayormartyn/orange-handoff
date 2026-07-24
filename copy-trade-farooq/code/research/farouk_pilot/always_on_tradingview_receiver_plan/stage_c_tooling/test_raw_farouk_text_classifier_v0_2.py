"""Unit tests for RAW FAROUK TEXT CLASSIFIER v0.2 — OFFLINE ONLY.

Re-runs the full v0.1 test coverage against v0.2 (behaviour preserved) and adds the
sweep instrument-only extraction cases. No I/O, no network.
Run: python test_raw_farouk_text_classifier_v0_2.py
"""

import unittest

from raw_farouk_text_classifier_v0_2 import (
    classify_raw_farouk_text,
    PARSE_VERSION,
)

P = "Farouks Playbook: "  # real captured prefix


class TestClassifierV02(unittest.TestCase):

    def _assert_safe(self, out, raw):
        self.assertEqual(out["raw_text"], raw)  # verbatim source of truth
        self.assertEqual(out["parse_version"], PARSE_VERSION)
        self.assertEqual(PARSE_VERSION, "raw_farouk_text_classifier_v0_2")
        self.assertTrue(out["candidate_only"])
        self.assertFalse(out["execution_allowed"])
        self.assertFalse(out["broker_execution_allowed"])
        self.assertFalse(out["qst_allowed"])
        forbidden = {
            "order", "order_intent", "broker_route", "route", "lot", "lot_size",
            "position_size", "account_id", "account", "risk", "risk_sizing",
            "permit", "lease", "sl", "tp", "stop_loss", "take_profit",
        }
        self.assertEqual(forbidden & set(out.keys()), set())

    # ---------- preserved v0.1 behaviour ----------
    def test_a_long(self):
        raw = P + "A LONG on XAUUSD 3"
        out = classify_raw_farouk_text(raw)
        self._assert_safe(out, raw)
        self.assertEqual(out["event_family"], "A_SIGNAL")
        self.assertEqual(out["event_type"], "A_LONG")
        self.assertEqual(out["direction"], "LONG")
        self.assertEqual(out["instrument"], "XAUUSD")
        self.assertEqual(out["timeframe"], "3")

    def test_a_short(self):
        raw = P + "A SHORT on XAUUSD 3"
        out = classify_raw_farouk_text(raw)
        self._assert_safe(out, raw)
        self.assertEqual(out["event_family"], "A_SIGNAL")
        self.assertEqual(out["event_type"], "A_SHORT")
        self.assertEqual(out["direction"], "SHORT")
        self.assertEqual(out["instrument"], "XAUUSD")
        self.assertEqual(out["timeframe"], "3")

    def test_choch_up(self):
        raw = P + "CHoCH UP on XAUUSD 3"
        out = classify_raw_farouk_text(raw)
        self._assert_safe(out, raw)
        self.assertEqual(out["event_family"], "STRUCTURE")
        self.assertEqual(out["event_type"], "CHOCH_UP")
        self.assertEqual(out["direction"], "LONG_HINT")

    def test_choch_down(self):
        raw = P + "CHoCH DOWN on XAUUSD 3"
        out = classify_raw_farouk_text(raw)
        self._assert_safe(out, raw)
        self.assertEqual(out["event_family"], "STRUCTURE")
        self.assertEqual(out["event_type"], "CHOCH_DOWN")
        self.assertEqual(out["direction"], "SHORT_HINT")

    def test_bullish_engulfing(self):
        raw = P + "Bullish Engulfing on XAUUSD 3"
        out = classify_raw_farouk_text(raw)
        self._assert_safe(out, raw)
        self.assertEqual(out["event_family"], "ENGULFING")
        self.assertEqual(out["event_type"], "BULLISH_ENGULFING")
        self.assertEqual(out["direction"], "LONG_HINT")

    def test_bearish_engulfing(self):
        raw = P + "Bearish Engulfing on XAUUSD 3"
        out = classify_raw_farouk_text(raw)
        self._assert_safe(out, raw)
        self.assertEqual(out["event_family"], "ENGULFING")
        self.assertEqual(out["event_type"], "BEARISH_ENGULFING")
        self.assertEqual(out["direction"], "SHORT_HINT")

    def test_bpr_tapped(self):
        raw = P + "BPR tapped on XAUUSD 3"
        out = classify_raw_farouk_text(raw)
        self._assert_safe(out, raw)
        self.assertEqual(out["event_family"], "BPR")
        self.assertEqual(out["event_type"], "BPR_TAPPED")
        self.assertIsNone(out["direction"])

    def test_bpr_formed(self):
        raw = P + "BPR formed on XAUUSD 3"
        out = classify_raw_farouk_text(raw)
        self._assert_safe(out, raw)
        self.assertEqual(out["event_family"], "BPR")
        self.assertEqual(out["event_type"], "BPR_FORMED")

    def test_a_plus_or_better(self):
        raw = P + "A+ or better on XAUUSD 3"
        out = classify_raw_farouk_text(raw)
        self._assert_safe(out, raw)
        self.assertEqual(out["event_family"], "A_PLUS")
        self.assertEqual(out["event_type"], "A_PLUS_OR_BETTER")
        self.assertTrue(out["is_trade_signal_candidate"])

    def test_a_triple_plus(self):
        raw = P + "A+++ on XAUUSD 3"
        out = classify_raw_farouk_text(raw)
        self._assert_safe(out, raw)
        self.assertEqual(out["event_family"], "A_TRIPLE_PLUS")
        self.assertEqual(out["event_type"], "A_TRIPLE_PLUS")

    def test_unknown(self):
        raw = "Totally unrelated message with no known family"
        out = classify_raw_farouk_text(raw)
        self._assert_safe(out, raw)
        self.assertEqual(out["event_family"], "UNKNOWN")
        self.assertIsNone(out["event_type"])
        self.assertEqual(out["confidence"], 0.0)

    def test_malformed_no_instrument(self):
        raw = "A LONG"
        out = classify_raw_farouk_text(raw)
        self._assert_safe(out, raw)
        self.assertEqual(out["event_family"], "A_SIGNAL")
        self.assertEqual(out["direction"], "LONG")
        self.assertIsNone(out["instrument"])
        self.assertIsNone(out["timeframe"])

    def test_a_plus_not_confused_with_a_long(self):
        raw = P + "A+ LONG on XAUUSD 3"
        out = classify_raw_farouk_text(raw)
        self._assert_safe(out, raw)
        self.assertEqual(out["event_family"], "A_PLUS")
        self.assertEqual(out["direction"], "LONG")

    def test_passthrough_fields(self):
        raw = P + "A SHORT on XAUUSD 3"
        out = classify_raw_farouk_text(
            raw, received_at_utc="2026-07-09T09:09:01Z",
            r2_object_key="events/2026/07/09/abc.jsonl")
        self.assertEqual(out["received_at_utc"], "2026-07-09T09:09:01Z")
        self.assertEqual(out["r2_object_key"], "events/2026/07/09/abc.jsonl")

    # ---------- NEW in v0.2: sweep instrument-only extraction ----------
    def test_sweep_low_bullish_instrument_only(self):
        raw = P + "Sweep low (bullish) on XAUUSD"
        out = classify_raw_farouk_text(raw)
        self._assert_safe(out, raw)
        self.assertEqual(out["event_family"], "LIQUIDITY_SWEEP")
        self.assertEqual(out["event_type"], "SWEEP_LOW")
        self.assertEqual(out["direction"], "LONG_HINT")
        self.assertEqual(out["instrument"], "XAUUSD")
        self.assertIsNone(out["timeframe"])
        self.assertIn("TIMEFRAME_MISSING", out["warnings"])

    def test_sweep_high_bearish_instrument_only(self):
        raw = P + "Sweep high (bearish) on XAUUSD"
        out = classify_raw_farouk_text(raw)
        self._assert_safe(out, raw)
        self.assertEqual(out["event_family"], "LIQUIDITY_SWEEP")
        self.assertEqual(out["event_type"], "SWEEP_HIGH")
        self.assertEqual(out["direction"], "SHORT_HINT")
        self.assertEqual(out["instrument"], "XAUUSD")
        self.assertIsNone(out["timeframe"])
        self.assertIn("TIMEFRAME_MISSING", out["warnings"])

    def test_sweep_low_plain_instrument_only(self):
        raw = P + "Sweep low on XAUUSD"
        out = classify_raw_farouk_text(raw)
        self._assert_safe(out, raw)
        self.assertEqual(out["event_type"], "SWEEP_LOW")
        self.assertEqual(out["instrument"], "XAUUSD")
        self.assertIsNone(out["timeframe"])
        self.assertIn("TIMEFRAME_MISSING", out["warnings"])

    def test_sweep_high_plain_instrument_only(self):
        raw = P + "Sweep high on XAUUSD"
        out = classify_raw_farouk_text(raw)
        self._assert_safe(out, raw)
        self.assertEqual(out["event_type"], "SWEEP_HIGH")
        self.assertEqual(out["instrument"], "XAUUSD")
        self.assertIsNone(out["timeframe"])
        self.assertIn("TIMEFRAME_MISSING", out["warnings"])

    def test_sweep_with_timeframe_still_works(self):
        # if a sweep ever DOES carry a TF, the full-pair path must win (no warning)
        raw = P + "Sweep low on XAUUSD 3"
        out = classify_raw_farouk_text(raw)
        self._assert_safe(out, raw)
        self.assertEqual(out["instrument"], "XAUUSD")
        self.assertEqual(out["timeframe"], "3")
        self.assertNotIn("TIMEFRAME_MISSING", out["warnings"])

    def test_sweep_execution_flags_false(self):
        for raw in [P + "Sweep low (bullish) on XAUUSD",
                    P + "Sweep high (bearish) on XAUUSD"]:
            out = classify_raw_farouk_text(raw)
            self.assertFalse(out["execution_allowed"])
            self.assertFalse(out["broker_execution_allowed"])
            self.assertFalse(out["qst_allowed"])
            self.assertTrue(out["candidate_only"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
