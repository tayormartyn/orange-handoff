"""Unit tests for FAROUK METHODOLOGY SCORER v0.1 — OFFLINE ONLY.

Synthetic candidates. No I/O. Run: python test_farouk_methodology_scorer_v0_1.py
"""

import unittest

from farouk_methodology_scorer_v0_1 import score_candidate, ALLOWED_LABELS, SCORER_VERSION

TRADE_READY_FORBIDDEN = {"buy", "sell", "enter", "execute", "trade_ready", "actionable"}
FORBIDDEN_KEYS = {"order", "order_intent_value", "broker_route", "route", "lot", "lot_size",
                  "position_size", "account_id", "account", "risk", "risk_sizing_value",
                  "sl", "tp", "pnl", "permit", "lease"}


def seq(*types):
    bias = {"SWEEP_LOW": "LONG_HINT", "SWEEP_HIGH": "SHORT_HINT", "CHOCH_UP": "LONG_HINT",
            "CHOCH_DOWN": "SHORT_HINT", "A_LONG": "LONG", "A_SHORT": "SHORT",
            "A_PLUS": "LONG", "BPR_TAPPED": None, "BULLISH_ENGULFING": "LONG_HINT"}
    return [{"event_type": t, "direction": bias.get(t)} for t in types]


class TestScorer(unittest.TestCase):

    def _assert_safe(self, rec):
        self.assertEqual(rec["scorer_version"], SCORER_VERSION)
        self.assertIn(rec["score_label"], ALLOWED_LABELS)
        self.assertTrue(rec["candidate_only"])
        self.assertFalse(rec["execution_allowed"])
        self.assertFalse(rec["broker_execution_allowed"])
        self.assertFalse(rec["qst_allowed"])
        self.assertFalse(rec["order_intent"])
        self.assertFalse(rec["risk_sizing_allowed"])
        self.assertEqual(FORBIDDEN_KEYS & set(rec.keys()), set())
        # no label ever means trade-ready
        self.assertNotIn(rec["score_label"].lower(), TRADE_READY_FORBIDDEN)

    def test_aligned_choch_a_favourable_but_missing_context_stays_shadow_only(self):
        c = {"candidate_id": "ALIGNED_CHOCH_TO_A-0000", "candidate_type": "ALIGNED_CHOCH_TO_A",
             "direction_hint": "LONG"}
        rec = score_candidate(c, sequence=seq("CHOCH_UP", "A_LONG"),
                              outcome_stats={"outcome_label": "FAVOURABLE"}, context={})
        self._assert_safe(rec)
        # never the top label when FVG/OB/session/displacement are missing
        self.assertNotEqual(rec["score_label"], "METHODOLOGY_ALIGNED_SHADOW")
        self.assertIn(rec["score_label"],
                      ("WATCH", "SHADOW_CANDIDATE_LOW", "SHADOW_CANDIDATE_MEDIUM"))
        # missing evidence must be explicit
        joined = " ".join(rec["missing_evidence"]).lower()
        self.assertIn("fvg", joined)
        self.assertIn("order_block", joined)
        self.assertTrue(any("displacement" in m.lower() for m in rec["missing_evidence"]))

    def test_contradictory_cluster_reject_or_context(self):
        c = {"candidate_id": "CC-0", "candidate_type": "CONTRADICTORY_CLUSTER",
             "direction_hint": "NONE_AMBIGUOUS"}
        rec = score_candidate(c, sequence=seq("A_LONG", "A_SHORT", "BULLISH_ENGULFING"))
        self._assert_safe(rec)
        self.assertIn(rec["score_label"], ("REJECT", "CONTEXT_ONLY"))
        self.assertTrue(rec["disqualifiers"])

    def test_a_signal_alone_not_high(self):
        c = {"candidate_id": "A-0", "candidate_type": "A_SIGNAL", "direction_hint": "LONG"}
        rec = score_candidate(c, sequence=seq("A_LONG"))
        self._assert_safe(rec)
        self.assertEqual(rec["score_label"], "CONTEXT_ONLY")

    def test_sweep_alone_not_high(self):
        c = {"candidate_id": "S-0", "candidate_type": "LIQUIDITY_SWEEP", "direction_hint": "LONG"}
        rec = score_candidate(c, sequence=seq("SWEEP_LOW"))
        self._assert_safe(rec)
        self.assertEqual(rec["score_label"], "CONTEXT_ONLY")

    def test_a_plus_without_context_not_trade_ready(self):
        c = {"candidate_id": "AP-0", "candidate_type": "A_PLUS", "direction_hint": "LONG"}
        rec = score_candidate(c, sequence=seq("A_PLUS"), context={"alert_grade": "A+"})
        self._assert_safe(rec)
        self.assertNotEqual(rec["score_label"], "METHODOLOGY_ALIGNED_SHADOW")
        # lone graded alert with no confluence is context-only, never trade-ready
        self.assertEqual(rec["score_label"], "CONTEXT_ONLY")

    def test_missing_evidence_listed(self):
        c = {"candidate_id": "X", "candidate_type": "ALIGNED_CHOCH_TO_A", "direction_hint": "LONG"}
        rec = score_candidate(c, sequence=seq("CHOCH_UP", "A_LONG"), context={})
        self.assertTrue(rec["missing_evidence"])

    def test_top_label_reachable_but_still_not_execution(self):
        # even a fully-evidenced, favourable candidate is only METHODOLOGY_ALIGNED_SHADOW
        # (observation ceiling) and carries NO execution permission.
        c = {"candidate_id": "FULL", "candidate_type": "STRONG_OB_REVERSAL", "direction_hint": "LONG"}
        ctx = {"session_context": "LONDON", "displacement": True, "fvg": True,
               "order_block": True, "telegram_confirmation": True, "alert_grade": "A+"}
        rec = score_candidate(c, sequence=seq("SWEEP_LOW", "CHOCH_UP", "A_PLUS"),
                              outcome_stats={"outcome_label": "FAVOURABLE"}, context=ctx)
        self._assert_safe(rec)
        self.assertEqual(rec["score_label"], "METHODOLOGY_ALIGNED_SHADOW")
        self.assertFalse(rec["execution_allowed"])  # ceiling is still observation-only

    def test_all_flags_false_across_labels(self):
        for s in (seq("A_LONG"), seq("CHOCH_UP", "A_LONG"), seq("A_LONG", "A_SHORT")):
            rec = score_candidate({"candidate_type": "X", "direction_hint": "LONG"}, sequence=s)
            self._assert_safe(rec)


if __name__ == "__main__":
    unittest.main(verbosity=2)
