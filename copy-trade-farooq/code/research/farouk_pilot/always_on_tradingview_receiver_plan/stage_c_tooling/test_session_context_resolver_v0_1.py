"""Unit tests for SESSION CONTEXT RESOLVER v0.1 — OFFLINE ONLY.

No I/O. Run: python test_session_context_resolver_v0_1.py
"""

import unittest
import copy

from session_context_resolver_v0_1 import (
    resolve_session, DEFAULT_SESSION_POLICY, RESOLVER_VERSION,
)

# a hypothetical CONFIRMED policy (only for testing the confirmed path)
CONFIRMED_POLICY = copy.deepcopy(DEFAULT_SESSION_POLICY)
CONFIRMED_POLICY["confirmed"] = True
CONFIRMED_POLICY["dst_handled"] = True


class TestSessionResolver(unittest.TestCase):

    def _assert_safe(self, rec):
        self.assertEqual(rec["resolver_version"], RESOLVER_VERSION)
        self.assertTrue(rec["candidate_only"])
        self.assertFalse(rec["execution_allowed"])
        self.assertFalse(rec["broker_execution_allowed"])
        self.assertFalse(rec["qst_allowed"])
        self.assertFalse(rec["order_intent"])
        self.assertFalse(rec["risk_sizing_allowed"])

    def test_inside_asia_window_confirmed_policy(self):
        rec = resolve_session("2026-07-09T04:12:00Z", policy=CONFIRMED_POLICY)
        self._assert_safe(rec)
        self.assertEqual(rec["session_label"], "ASIA_UTC_PROXY")
        self.assertEqual(rec["session_window"], "00.0-08.0 UTC")
        # Asia clock window is NOT in the corpus -> confidence NONE even when policy "confirmed"
        self.assertEqual(rec["session_confidence"], "NONE")

    def test_outside_asia_maps_to_correct_session(self):
        rec = resolve_session("2026-07-09T14:00:00Z", policy=CONFIRMED_POLICY)
        self._assert_safe(rec)
        self.assertEqual(rec["session_label"], "NEW_YORK_UTC_PROXY")

    def test_unconfirmed_policy_returns_session_unconfirmed(self):
        rec = resolve_session("2026-07-09T04:12:00Z")  # default policy = unconfirmed
        self._assert_safe(rec)
        self.assertEqual(rec["session_confidence"], "UNCONFIRMED")
        self.assertTrue(any("SESSION_UNCONFIRMED" in w for w in rec["warnings"]))

    def test_unparseable_timestamp(self):
        rec = resolve_session("nope")
        self._assert_safe(rec)
        self.assertEqual(rec["session_label"], "SESSION_UNRESOLVED")

    def test_all_safety_flags_false(self):
        for ts in ("2026-07-09T00:03:00Z", "2026-07-09T10:00:00Z", "2026-07-09T22:00:00Z"):
            self._assert_safe(resolve_session(ts))


if __name__ == "__main__":
    unittest.main(verbosity=2)
