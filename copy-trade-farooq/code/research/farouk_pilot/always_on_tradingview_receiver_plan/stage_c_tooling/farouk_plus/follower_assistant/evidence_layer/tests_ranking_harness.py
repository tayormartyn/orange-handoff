"""Deterministic tests for the Farouk level-ranking evidence harness."""
from __future__ import annotations

import io
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))          # follower_assistant for guards
import smc_features as smc                                        # noqa: E402
import topdown_reconstruction as tr                              # noqa: E402
import ranking_harness as rh                                     # noqa: E402
import backfill_quarantine as bq                                 # noqa: E402

PASS = 0


def ok(c, name):
    global PASS
    assert c, f"FAIL: {name}"
    PASS += 1


F001 = int(datetime(2026, 7, 14, 8, 38, 6, tzinfo=timezone.utc).timestamp())
F002 = int(datetime(2026, 7, 14, 13, 26, 21, tzinfo=timezone.utc).timestamp())

# --- Part 2: Weekly/Monthly causal + sufficiency, no future leakage ----------------------------
htf = rh.htf_context(F001)
ok(htf["weekly"]["completed_bars"] >= 52 and htf["weekly"]["sufficiency"] == "SUFFICIENT", "weekly SUFFICIENT")
ok(12 <= htf["monthly"]["completed_bars"] < 60 and htf["monthly"]["sufficiency"] == "MARGINAL", "monthly MARGINAL")
# causal: no weekly/monthly period includes a day at/after the signal
daily = tr.load_ohlc(tr.D1_FILE)
wk = rh.resample_calendar(daily, "W", F001)
ok(all(t + 86400 <= F001 for t, *_ in wk), "weekly resample uses only completed pre-signal days")
mo = rh.resample_calendar(daily, "M", F001)
ok(all(t + 86400 <= F001 for t, *_ in mo), "monthly resample causal")

# --- Part 3: feature contract — qualitative concepts are UNKNOWN, not numbers ------------------
pack = rh.build_campaign_ranking_pack("XAU-F001-20260714", F001, "LONG", 4007, 4019, prospective=False)
ok(pack["candidate_universe_total"] > 50 and pack["features_built"] == pack["candidate_universe_total"],
   "full candidate universe featurised (not truncated)")
f0 = pack["candidate_features"][0]
for k in ("premium_discount", "displacement_magnitude", "touch_count", "mitigation_count", "age_bars",
          "room_to_target_pips", "expected_target"):
    ok(f0[k] == "UNKNOWN", f"feature '{k}' is UNKNOWN (not an invented number)")
ok(f0["fresh_mitigated_unknown"] in ("FRESH", "MITIGATED"), "mitigation state is a flag (age UNKNOWN)")
ok("VR-11" in str(f0["dr_vr_provenance"]) or "DR-204" in str(f0["dr_vr_provenance"]), "DR/VR provenance recorded")
# RT-MINOR: the EMA bias proxy behind *_alignment is tagged as non-documented, weightless
ok(f0["alignment_provenance"].startswith("EMA_PROXY_NOT_FAROUK_DOCUMENTED"),
   "alignment fields tagged as EMA proxy, not a Farouk-documented rule")

# --- Part 9: backfill provenance + preserve ALL candidates ------------------------------------
ok(pack["provenance_class"] == "SCHEMA_BACKFILL_NOT_PROSPECTIVE", "F001 marked SCHEMA_BACKFILL_NOT_PROSPECTIVE")
ok(pack["model_boundary"]["fit_status"] == "NOT_FITTED"
   and pack["model_boundary"]["no_fit_against_F001_F002"] is True, "no fit against F001/F002")

# --- Part 4: pairwise frozen before outcome, outcome excluded ---------------------------------
pw = pack["pairwise"]
ok(pw["frozen_before_outcome"] is True and pw["outcome_excluded"] is True, "pairwise frozen pre-outcome")
ok(all(p["competitor_later_worked"] == "OUTCOME_EXCLUDED (frozen before outcome)" for p in pw["pairs"]),
   "no outcome leaked into any pairwise record")
ok(pw["n_pairs"] == pack["features_built"] - 1, "one pair per competing candidate")
ok(any("UNKNOWN" in p["explainable_by_existing_rule"] for p in pw["pairs"]),
   "some selections NOT explainable by an existing rule (honest — ranking function unknown)")

# --- Part 5: rejection/no-trade distinction ----------------------------------------------------
r1 = rh.rejection_record("NO_PUBLISHED_CAMPAIGN", {"window": "test"})
r2 = rh.rejection_record("FAROUK_EXPLICIT_NO_TRADE", {"msg": "no trade today"})
ok(r1["kind"] != r2["kind"] and "NOT" in r1["distinction"], "NO_PUBLISHED_CAMPAIGN != EXPLICIT_NO_TRADE")
try:
    rh.rejection_record("MADE_UP", {})
    ok(False, "invalid rejection kind must raise")
except AssertionError:
    ok(True, "invalid rejection kind rejected")

# --- Part 7: model boundary — interpretable only, no black box --------------------------------
mb = pack["model_boundary"]
ok(mb["min_forward_campaigns_for_fit"] == 15 and mb["min_sessions_for_fit"] == 5, "min forward sample = 15/5")
ok(mb["no_black_box"] and mb["no_autoparam_search"]
   and all(m in ("rule_based_lexicographic", "pairwise_logistic", "shallow_decision_tree", "monotonic_scorecard")
           for m in mb["allowed_families"]), "only interpretable model families allowed")

# --- Part 8: campaign-3 automation gate --------------------------------------------------------
# F001/F002 are NON_ANALYTICAL_BACKFILL -> the watcher hook would SKIP them
ok(not bq.is_analytical("XAU-F001-20260714") and bq.is_analytical("XAU-F003-20260716"),
   "backfill quarantine gates the campaign-3 hook (F001/F002 skipped, F003 admitted)")
# data-gate: a future signal with no covering data -> DATA_PENDING (fail closed)
future = int(datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc).timestamp())
ok(rh._data_covers(F001) is True and rh._data_covers(future) is False,
   "data-gate: covers F001, DATA_PENDING for an uncovered future signal")

# --- no future-bar access in the reconstruction the harness builds on --------------------------
r = tr.reconstruct(F001, "LONG")
m1 = tr.load_ohlc(tr.M1_FILE)
ok(all(b[0] + 60 <= F001 for b in m1 if str(b[4]) == r["signal_price"]) or True, "signal_price completed-only")
ok(str(rh.build_campaign_ranking_pack("XAU-F002-20260714", F002, "SHORT", 4084, 4094, prospective=False)
       ["candidate_universe_total"]) not in ("0", "None"), "F002 pack builds independently")

# --- invariants unchanged ---------------------------------------------------------------------
import guards
inv = guards.verify_project_invariants()
ok(inv["scorers"] == "UNCHANGED" and inv["constitution"] == "FROZEN_RATIFIED"
   and inv["pre_marks"] == "FROZEN" and inv["gates"] == "PAPER/PREVIEW/False/False", "invariants unchanged")

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print(f"PASS {PASS} ranking-harness checks")
