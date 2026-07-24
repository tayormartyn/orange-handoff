"""Guard-FIRST tests for the LIVE_EDIT completion look-ahead guard (the safety heart, D-106).
The BACKDATING case is proven before any happy-path wiring exists.
Run: python parser_replay/tests_edit_completion_guard.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edit_completion_guard import edit_completion_is_prospective as G   # noqa: E402

_p = _f = 0
def ck(n, c):
    global _p, _f
    print(("  ok  " if c else "FAIL  ") + n); _p += bool(c); _f += (not c)

# F008 real timestamps (epoch): post 14:03:48, edit 14:04:00, TP1 14:06:18.
POST = 1784729028      # 2026-07-22T14:03:48Z
EDIT = 1784729040      # 2026-07-22T14:04:00Z  (+12s)
TP1  = 1784729178      # 2026-07-22T14:06:18Z  (after the edit)

# --- THE BACKDATING GUARD (safety-critical) - proven FIRST ---
ck("BACKDATING BLOCKED: outcome BEFORE a slow edit -> NOT prospective",
   G(original_post_ts=POST, edit_completion_ts=TP1 + 200, outcome_evidence_ts=[TP1]) is False)
ck("BACKDATING BLOCKED: outcome EXACTLY at edit-completion -> NOT prospective (boundary)",
   G(original_post_ts=POST, edit_completion_ts=TP1, outcome_evidence_ts=[TP1]) is False)
ck("BACKDATING BLOCKED: one of several outcomes lands in the window -> NOT prospective",
   G(original_post_ts=POST, edit_completion_ts=TP1 + 500, outcome_evidence_ts=[TP1 + 1000, TP1, TP1 + 2000]) is False)

# --- THE F008-WOULD-HAVE-WORKED case: edit before any outcome ---
ck("F008 case: fast edit, NO outcome yet -> prospective",
   G(original_post_ts=POST, edit_completion_ts=EDIT, outcome_evidence_ts=[]) is True)
ck("F008 case: outcome lands AFTER the edit completed -> still prospective",
   G(original_post_ts=POST, edit_completion_ts=EDIT, outcome_evidence_ts=[TP1]) is True)

# --- unrelated prior-trade outcome (before the post) does NOT block ---
ck("outcome BEFORE the post (prior trade) -> does not block",
   G(original_post_ts=POST, edit_completion_ts=EDIT, outcome_evidence_ts=[POST - 500]) is True)

# --- fail-closed on malformed input ---
ck("edit before post -> fail closed (False)",
   G(original_post_ts=EDIT, edit_completion_ts=POST, outcome_evidence_ts=[]) is False)
ck("unparseable outcome ts -> fail closed (False)",
   G(original_post_ts=POST, edit_completion_ts=EDIT, outcome_evidence_ts=["oops"]) is False)
ck("None timestamps -> fail closed (False)",
   G(original_post_ts=None, edit_completion_ts=EDIT, outcome_evidence_ts=[]) is False)

print(f"\n{_p} passed, {_f} failed")
sys.exit(1 if _f else 0)
