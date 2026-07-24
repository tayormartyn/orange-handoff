"""Unit tests for SHADOW CANDIDATE DETECTOR v0.1 — OFFLINE ONLY.

Synthetic classified-event fixtures exercise each candidate type + the safety
invariants. No I/O. Run: python test_shadow_candidate_detector_v0_1.py
"""

import unittest

from shadow_candidate_detector_v0_1 import detect, summary_counts, DETECTOR_VERSION


def ev(t, event_type, direction=None, instrument="XAUUSD", timeframe="3",
       raw=None):
    return {
        "received_at_utc": t,
        "raw_text": raw or f"Farouks Playbook: {event_type}",
        "event_family": None,
        "event_type": event_type,
        "direction": direction,
        "instrument": instrument,
        "timeframe": timeframe,
        "confidence": 0.9,
    }


def types(result, ct):
    return [c for c in result["candidates"] if c["candidate_type"] == ct]


class TestShadowDetector(unittest.TestCase):

    def _assert_safe(self, rec):
        self.assertEqual(rec["detector_version"], DETECTOR_VERSION)
        self.assertTrue(rec["candidate_only"])
        self.assertFalse(rec["execution_allowed"])
        self.assertFalse(rec["broker_execution_allowed"])
        self.assertFalse(rec["qst_allowed"])
        self.assertFalse(rec["order_intent"])
        self.assertFalse(rec["risk_sizing_allowed"])
        self.assertIn(rec["confidence"], ("LOW", "MEDIUM"))  # never HIGH

    def test_choch_up_to_a_long_aligned(self):
        events = [ev("2026-07-09T04:00:00.000Z", "CHOCH_UP", "LONG_HINT"),
                  ev("2026-07-09T04:12:01.000Z", "A_LONG", "LONG")]
        r = detect(events)
        al = types(r, "ALIGNED_CHOCH_TO_A")
        self.assertEqual(len(al), 1)
        self.assertEqual(al[0]["direction_hint"], "LONG")
        self.assertEqual(al[0]["confidence"], "MEDIUM")  # same it/tf, no contradiction
        self._assert_safe(al[0])

    def test_choch_down_to_a_short_aligned(self):
        events = [ev("2026-07-09T05:00:00.000Z", "CHOCH_DOWN", "SHORT_HINT"),
                  ev("2026-07-09T05:10:00.000Z", "A_SHORT", "SHORT")]
        r = detect(events)
        al = types(r, "ALIGNED_CHOCH_TO_A")
        self.assertEqual(len(al), 1)
        self.assertEqual(al[0]["direction_hint"], "SHORT")
        self.assertEqual(al[0]["confidence"], "MEDIUM")
        self._assert_safe(al[0])

    def test_choch_up_to_a_short_not_aligned(self):
        # CHoCH_UP followed only by A_SHORT -> no aligned A_LONG -> no ALIGNED candidate
        events = [ev("2026-07-09T06:00:00.000Z", "CHOCH_UP", "LONG_HINT"),
                  ev("2026-07-09T06:05:00.000Z", "A_SHORT", "SHORT")]
        r = detect(events)
        self.assertEqual(len(types(r, "ALIGNED_CHOCH_TO_A")), 0)

    def test_aligned_but_contradicted_is_low(self):
        # CHoCH_UP -> A_SHORT (opposite) then A_LONG within window -> aligned type but LOW
        events = [ev("2026-07-09T07:00:00.000Z", "CHOCH_UP", "LONG_HINT"),
                  ev("2026-07-09T07:03:00.000Z", "A_SHORT", "SHORT"),
                  ev("2026-07-09T07:06:00.000Z", "A_LONG", "LONG")]
        r = detect(events)
        al = types(r, "ALIGNED_CHOCH_TO_A")
        self.assertEqual(len(al), 1)
        self.assertEqual(al[0]["confidence"], "LOW")
        self.assertTrue(al[0]["disqualifiers"])

    def test_sweep_low_to_choch_up_context(self):
        events = [ev("2026-07-09T08:00:00.000Z", "SWEEP_LOW", "LONG_HINT", timeframe=None),
                  ev("2026-07-09T08:20:00.000Z", "CHOCH_UP", "LONG_HINT")]
        r = detect(events)
        c = types(r, "SWEEP_TO_CHOCH_CONTEXT")
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0]["confidence"], "LOW")
        self._assert_safe(c[0])

    def test_sweep_high_to_choch_down_context(self):
        events = [ev("2026-07-09T09:00:00.000Z", "SWEEP_HIGH", "SHORT_HINT", timeframe=None),
                  ev("2026-07-09T09:25:00.000Z", "CHOCH_DOWN", "SHORT_HINT")]
        r = detect(events)
        c = types(r, "SWEEP_TO_CHOCH_CONTEXT")
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0]["confidence"], "LOW")

    def test_bpr_tapped_to_a_context(self):
        events = [ev("2026-07-09T10:00:00.000Z", "BPR_TAPPED", None),
                  ev("2026-07-09T10:10:00.000Z", "A_SHORT", "SHORT")]
        r = detect(events)
        c = types(r, "BPR_TO_A_CONTEXT")
        self.assertEqual(len(c), 1)
        self.assertEqual(c[0]["confidence"], "LOW")
        self._assert_safe(c[0])

    def test_contradictory_cluster_detected(self):
        events = [ev("2026-07-09T11:00:00.000Z", "A_LONG", "LONG"),
                  ev("2026-07-09T11:03:00.000Z", "A_SHORT", "SHORT"),
                  ev("2026-07-09T11:06:00.000Z", "BULLISH_ENGULFING", "LONG_HINT")]
        r = detect(events)
        self.assertGreaterEqual(len(r["disqualified"]), 1)
        d = r["disqualified"][0]
        self.assertEqual(d["candidate_type"], "CONTRADICTORY_CLUSTER")
        self.assertTrue(d["disqualifiers"])
        self._assert_safe(d)

    def test_a_signal_alone_no_candidate(self):
        events = [ev("2026-07-09T12:00:00.000Z", "A_LONG", "LONG")]
        r = detect(events)
        self.assertEqual(len(r["candidates"]), 0)
        self.assertEqual(len(r["disqualified"]), 0)

    def test_engulfing_to_a_not_trade_candidate(self):
        # Engulfing->A must NOT produce any candidate_type at all
        events = [ev("2026-07-09T13:00:00.000Z", "BEARISH_ENGULFING", "SHORT_HINT"),
                  ev("2026-07-09T13:02:00.000Z", "A_SHORT", "SHORT")]
        r = detect(events)
        cts = {c["candidate_type"] for c in r["candidates"]}
        self.assertNotIn("ENGULFING_TO_A", cts)
        self.assertEqual(len(r["candidates"]), 0)  # only a same-dir pair, no promoted candidate

    def test_all_safety_flags_false_everywhere(self):
        events = [ev("2026-07-09T04:00:00.000Z", "CHOCH_UP", "LONG_HINT"),
                  ev("2026-07-09T04:12:01.000Z", "A_LONG", "LONG"),
                  ev("2026-07-09T04:14:00.000Z", "A_SHORT", "SHORT")]
        r = detect(events)
        for rec in r["candidates"] + r["disqualified"]:
            self._assert_safe(rec)

    def test_summary_counts_shape(self):
        events = [ev("2026-07-09T04:00:00.000Z", "CHOCH_UP", "LONG_HINT"),
                  ev("2026-07-09T04:12:01.000Z", "A_LONG", "LONG")]
        s = summary_counts(detect(events))
        self.assertIn("by_candidate_type", s)
        self.assertEqual(s["candidates_total"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
