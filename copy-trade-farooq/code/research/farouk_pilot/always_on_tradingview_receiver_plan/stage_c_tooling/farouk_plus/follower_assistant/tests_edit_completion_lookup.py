"""Exhaustive tests for the D-106 look-ahead OUTCOME-LOOKUP (live_wire._gold_outcome_evidence_ts)
+ its guard integration. Getting this wrong IS the backdating hole, so it is over-tested.
Run: python tests_edit_completion_lookup.py
"""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live_wire                                                 # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "parser_replay"))
from edit_completion_guard import edit_completion_is_prospective as G   # noqa: E402

TMP = tempfile.mkdtemp(prefix="lookup_test_")
FWD = os.path.join(TMP, "forward.jsonl")
live_wire.FWD_LEDGER = FWD

_p = _f = 0
def ck(n, c):
    global _p, _f
    print(("  ok  " if c else "FAIL  ") + n); _p += bool(c); _f += (not c)
def write(recs):
    with open(FWD, "w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")

POST = "2026-07-22T14:03:48+00:00"    # original post of the quarantined entry (msg 46011)
EDIT = "2026-07-22T14:04:00+00:00"    # completing-edit time
ep = live_wire._to_epoch
def prospective(ts_list):
    return G(original_post_ts=ep(POST), edit_completion_ts=ep(EDIT),
             outcome_evidence_ts=[ep(t) for t in ts_list])

# 1. the ENTRY's OWN 'missing stop' review (same message_id) MUST NOT be counted as outcome evidence
write([
    {"record_type": "XAU_F_INTERPRETATION_REVIEW", "message_id": 46011,
     "timestamp_utc": "2026-07-22T14:03:49+00:00", "why": "wire review: missing stop"},
])
ts = live_wire._gold_outcome_evidence_ts(exclude_message_id=46011)
ck("entry's OWN 'missing stop' review is NOT counted", "2026-07-22T14:03:49+00:00" not in ts)
ck("...so a lone self-review leaves the edit PROSPECTIVE", prospective(ts) is True)

# 2. a MANAGEMENT review just INSIDE the window (different msg) IS counted -> BLOCKED
write([
    {"record_type": "XAU_F_INTERPRETATION_REVIEW", "message_id": 46011,
     "timestamp_utc": "2026-07-22T14:03:49+00:00", "why": "wire review: missing stop"},
    {"record_type": "XAU_F_INTERPRETATION_REVIEW", "message_id": 46013,
     "timestamp_utc": "2026-07-22T14:03:55+00:00", "why": "management instruction with no open campaign"},
])
ts = live_wire._gold_outcome_evidence_ts(exclude_message_id=46011)
ck("in-window MANAGEMENT review IS counted", "2026-07-22T14:03:55+00:00" in ts)
ck("management just-inside-window -> BLOCKED", prospective(ts) is False)

# 3. management JUST AFTER the edit completes -> NOT counted in-window -> PROSPECTIVE
write([
    {"record_type": "XAU_F_INTERPRETATION_REVIEW", "message_id": 46013,
     "timestamp_utc": "2026-07-22T14:04:01+00:00", "why": "management instruction with no open campaign"},
])
ts = live_wire._gold_outcome_evidence_ts(exclude_message_id=46011)
ck("management just-AFTER-edit -> PROSPECTIVE (F008-would-have-worked)", prospective(ts) is True)

# 4. boundary: management EXACTLY at edit-completion -> BLOCKED (half-open window (post, edit])
write([
    {"record_type": "XAU_F_ORPHAN_MANAGEMENT", "message_id": 46013, "timestamp_utc": EDIT, "why": "TP1"},
])
ts = live_wire._gold_outcome_evidence_ts(exclude_message_id=46011)
ck("boundary: outcome EXACTLY at edit-completion -> BLOCKED", prospective(ts) is False)

# 5. terminal outcome + orphan-management are recognised outcome classes
write([
    {"record_type": "XAU_F_TERMINAL_OUTCOME", "setup_id": "X", "timestamp_utc": "2026-07-22T14:03:59+00:00"},
    {"record_type": "XAU_F_ORPHAN_MANAGEMENT", "message_id": 9, "timestamp_utc": "2026-07-22T14:03:58+00:00"},
])
ts = live_wire._gold_outcome_evidence_ts(exclude_message_id=46011)
ck("terminal + orphan-management both counted", len(ts) == 2 and prospective(ts) is False)

# 6. a NON-outcome record (a plain campaign setup / commentary) is NOT counted
write([
    {"record_type": "XAU_F_SETUP", "setup_id": "XAU-Fxxx", "timestamp_utc": "2026-07-22T14:03:55+00:00"},
    {"record_type": "XAU_F_INTERPRETATION_REVIEW", "message_id": 5,
     "timestamp_utc": "2026-07-22T14:03:55+00:00", "why": "wire review: missing stop"},   # parse review, not mgmt
])
ts = live_wire._gold_outcome_evidence_ts(exclude_message_id=46011)
ck("non-outcome setup + a parse-review are NOT counted", ts == [] and prospective(ts) is True)

# 7. malformed ledger line -> skipped, never crashes
with open(FWD, "a", encoding="utf-8") as fh:
    fh.write("NOT JSON AT ALL\n")
ts = live_wire._gold_outcome_evidence_ts(exclude_message_id=46011)
ck("malformed ledger line skipped (no crash)", isinstance(ts, list))

# 8. missing ledger -> empty (fail-safe)
live_wire.FWD_LEDGER = os.path.join(TMP, "does_not_exist.jsonl")
ck("absent ledger -> empty list", live_wire._gold_outcome_evidence_ts() == [])

print(f"\n{_p} passed, {_f} failed")
sys.exit(1 if _f else 0)
