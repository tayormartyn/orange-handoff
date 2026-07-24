"""Quantity-base guard fix v0.1 + Constitution P14/P22 unfilled-leg semantics — focused tests.

Hermetic: interpreter/guards/engine run in-process on synthetic data; the F004 chronology check
re-derives from the REAL ledgers/bars READ-ONLY (nothing written). Run directly:
python tests_quantity_base_guard.py
"""
from __future__ import annotations

import io
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal as D
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
MT = os.path.join(HERE, "market_tracker")
SO = os.path.join(HERE, "scale_out")
for p in (HERE, MT, SO):
    sys.path.insert(0, p)
import interpreter                                                # noqa: E402
import guards                                                     # noqa: E402
import engine as EG                                               # noqa: E402
import run_fixtures                                               # noqa: E402
from scale_out_classifier import apply_scale_out                  # noqa: E402
from market_events import BarStream                               # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
PASS = 0


def ok(c, name):
    global PASS
    assert c, f"FAIL: {name}"
    PASS += 1
    print(f"  ok {PASS}: {name}")


HDR = "seascalperfarouk Posted in 🪙・gold-trades\n\n"
CONST = json.load(open(os.path.join(HERE, "follower_constitution_v0_1.json"), encoding="utf-8"))


def wire_shaped(instructions):
    """A minimal wire-shaped setup revision embedding the instruction (what assert_clean sees)."""
    return {"record_type": "XAU_F_SETUP", "setup_id": "XAU-TEST", "revision": 2,
            "management_timing_8c": {"instruction_events": [dict(i, message_id=1, timestamp_utc="t")
                                                            for i in instructions]},
            "review_only": True, "executable": False, "trade_ready": False,
            "observation_only": True}


def violates(rec):
    try:
        guards.assert_clean(rec, "test")
        return False
    except guards.GuardViolation:
        return True


print("== T1: 'close 90% leave 10%' accepted on current remaining filled quantity")
c = interpreter.classify(HDR + "`Whale` close 90% leave 10%")
ins = c["instructions"]
ok(c["kind"] == "MANAGEMENT" and ins[0]["instruction_type"] == "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE"
   and ins[0]["close_percentage"] == 90 and ins[0]["retain_percentage"] == 10, "T1 parse 90/10")
ok(ins[0]["quantity_base"] == "CURRENTLY_REMAINING_OPEN_FILLED_QUANTITY", "T1 deterministic base")
ok(not violates(wire_shaped(ins)), "T1 guard ACCEPTS the valid instruction (was the defect)")
so = apply_scale_out(Fraction(1, 2), 90)
ok(so["quantity_base"] == "CURRENTLY_REMAINING_OPEN_FILLED_QUANTITY"
   and Fraction(so["closed"]) == Fraction(9, 20) and Fraction(so["remaining_after"]) == Fraction(1, 20),
   "T1 math on CURRENT remaining (0.5 open -> close 0.45, retain 0.05)")

print("== T2: 'take 50% leave 50% running' accepted")
c = interpreter.classify(HDR + "`Whale` take 50% leave 50% running")
ins = c["instructions"]
ok(ins and ins[0]["instruction_type"] == "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE"
   and ins[0]["close_percentage"] == 50 and ins[0]["retain_percentage"] == 50
   and ins[0]["runner_requested"], "T2 parse 50/50 runner")
ok(not violates(wire_shaped(ins)), "T2 guard accepts")

print("== T3: 'close 90 leave 20' rejected fail-closed, no mutation")
c = interpreter.classify(HDR + "`Whale` close 90 leave 20")
ok(c["kind"] == "NEEDS_HUMAN_REVIEW" and "must be 100" in c["why"],
   "T3 non-reconciling percentages -> quarantine (interpreter fail-closed)")
bad = {"instruction_type": "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE", "close_percentage": 90,
       "retain_percentage": 20, "quantity_base": "CURRENTLY_REMAINING_OPEN_FILLED_QUANTITY"}
ok(violates(wire_shaped([bad])), "T3 guard ALSO rejects non-reconciling percentages (defense in depth)")

print("== T4: unsupported / missing / smuggled quantity bases rejected")
for base, why in (("ORIGINAL_CAMPAIGN_QUANTITY", "original-campaign base"),
                  ("ACCOUNT_QUANTITY", "account base"),
                  ("BROKER_POSITION", "broker base"),
                  ("2.5_LOTS_ABSOLUTE", "absolute lots"),
                  (None, "missing/None base"),
                  ("UNKNOWN_BASE_X", "unknown base")):
    r = {"instruction_type": "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE", "close_percentage": 90,
         "retain_percentage": 10, "quantity_base": base}
    ok(violates(wire_shaped([r])), f"T4 rejected: {why}")
r = {"instruction_type": "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE", "close_percentage": 90,
     "retain_percentage": 10}
ok(violates(wire_shaped([r])), "T4 rejected: quantity_base absent entirely")
ok(violates(wire_shaped([{"instruction_type": "OTHER", "order_quantity": 5}])),
   "T4 other 'quantity'-token keys remain forbidden")
ok(violates(wire_shaped([{"instruction_type": "OTHER", "account_quantity_base": "x"}])),
   "T4 near-miss key names remain forbidden")
for pcts in ((0, 100), (100, 0), (-10, 110), (60, 60), ("90", "10")):
    r = {"instruction_type": "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE", "close_percentage": pcts[0],
         "retain_percentage": pcts[1], "quantity_base": "CURRENTLY_REMAINING_OPEN_FILLED_QUANTITY"}
    ok(violates(wire_shaped([r])), f"T4 invalid percentages rejected: {pcts}")

SIG = 1784240000 - (1784240000 % 60)
BARS_NEAR_ONLY = [
    (SIG, D("4020"), D("4026"), D("4019"), D("4025.5")),          # near (4025) fills
    (SIG + 60, D("4025.5"), D("4026"), D("4024"), D("4025.0")),   # instruction bar
    (SIG + 120, D("4025"), D("4025.5"), D("4020"), D("4021.0")),
]


def run_engine(lane, events):
    camp = {"setup_id": "XAU-TEST-P14", "direction": "SHORT", "zone_low": D("4025"),
            "zone_high": D("4035"), "sl": "4075", "signal_ts": SIG, "attempt_number": 1,
            "events": events}
    return EG.FollowerEngine(camp, BARS_NEAR_ONLY, lane, CONST).run()


print("== T5: SL-to-entry with unfilled legs — RATIFIED constitution semantics (P14/Q3)")
res = run_engine("LANE_A", [{"ts": SIG + 60, "instruction_type": "SL_TO_ENTRY", "message_id": 2}])
states = {l["leg_id"].split("/")[-1]: l["state"] for l in res["legs"]}
ok(states["near"] != "CANCELLED", "T5 filled leg NOT cancelled by BE (per-leg break-even only)")
ok(states["mid"] == "CANCELLED" and states["far"] == "CANCELLED",
   "T5 LANE_A: unfilled legs CANCEL on SL_TO_ENTRY — the RATIFIED P14 DEFAULT (Q3), "
   "NOT the 'remain pending' expectation")
ok(any(t.get("rule") == "P14" or "P14_SL_TO_ENTRY_CANCEL" in str(t) for t in res["transitions"]),
   "T5 cancellation attributed to P14_SL_TO_ENTRY_CANCEL")
res_b = run_engine("LANE_B", [{"ts": SIG + 60, "instruction_type": "SL_TO_ENTRY", "message_id": 2}])
states_b = {l["leg_id"].split("/")[-1]: l["state"] for l in res_b["legs"]}
ok(states_b["mid"] != "CANCELLED" and states_b["far"] != "CANCELLED",
   "T5 LANE_B alternate: unfilled legs remain resting (keep) — documented alternate")

print("== T6: explicit 'cancel pending orders' cancels unfilled legs")
c = interpreter.classify(HDR + "`Whale` cancel pending orders")
tps = [i["instruction_type"] for i in c.get("instructions", [])]
ok("CANCEL" in tps, "T6 parses to explicit CANCEL")
res = run_engine("LANE_A", [{"ts": SIG + 60, "instruction_type": "CANCEL", "message_id": 3}])
states = {l["leg_id"].split("/")[-1]: l["state"] for l in res["legs"]}
ok(states["mid"] == "CANCELLED" and states["far"] == "CANCELLED",
   "T6 unfilled legs cancelled (P22 explicit cancellation)")

print("== T7: explicit risk-off wording ('cancel the limit orders') cancels unfilled legs")
c = interpreter.classify(HDR + "`Whale` cancel the limit orders, keep the running position")
tps = [i["instruction_type"] for i in c.get("instructions", [])]
ok("CANCEL_LIMITS" in tps, "T7 parses to CANCEL_LIMITS")
res = run_engine("LANE_A", [{"ts": SIG + 60, "instruction_type": "CANCEL_LIMITS", "message_id": 4}])
states = {l["leg_id"].split("/")[-1]: l["state"] for l in res["legs"]}
ok(states["mid"] == "CANCELLED" and states["far"] == "CANCELLED",
   "T7 constitutionally defined unfilled-leg cancellation")

print("== T8: exact F004 chronology — READ-ONLY re-derivation from real ledgers/bars")
FWD = os.path.join(HERE, "..", "forward_validation_ledger_v0_2.jsonl")
latest = None
for line in open(FWD, encoding="utf-8"):
    r = json.loads(line)
    if r.get("record_type") == "XAU_F_SETUP" and r.get("setup_id") == "XAU-F004-20260716":
        if latest is None or r.get("revision", 1) >= latest.get("revision", 1):
            latest = r
ok(latest is not None and latest["revision"] == 5, "T8 latest F004 revision = 5 (adjudicated)")
ev = [(e["instruction_type"], e.get("message_id")) for e in
      latest["management_timing_8c"]["instruction_events"]]
ok(ev == [("TP1_TAKE", 45808), ("CLOSE_WORST", 45810), ("HOLD_BEST", 45810),
          ("SL_TO_ENTRY", 45810), ("SL_TO_ENTRY", 45813), ("TAKE_PCT_OFF", 45816)],
   "T8 authentic instruction set — no CANCEL / CANCEL_LIMITS / FINAL_CLOSE present")
s = BarStream()
s.log_path = os.path.join(MT, "ingestion_log_v0_1.jsonl")
s.restore()
bars = s.ordered_tuples()
camp = run_fixtures.campaign_from_setup(latest)
res = EG.FollowerEngine(camp, bars, "LANE_A", CONST).run()
states = {l["leg_id"].split("/")[-1]: l["state"] for l in res["legs"]}
ok(states == {"near": "FILLED", "mid": "CANCELLED", "far": "CANCELLED"},
   f"T8 leg states re-derived: {states} (mid/far cancelled by ratified P14 on 45810 SL_TO_ENTRY)")
ok(res["campaign_state"] == "CLOSED", "T8 campaign CLOSED (BE scratch ended the runner)")
ok(str(res.get("realized_pips_per_unit")) == "15.18",
   f"T8 realized {res.get('realized_pips_per_unit')} pts/unit reproduces the tracker outcome")

print("== engine EPPC status (documented, unchanged this task)")
res = run_engine("LANE_A", [{"ts": SIG + 60, "instruction_type": "EXPLICIT_PERCENTAGE_PARTIAL_CLOSE",
                             "message_id": 5}])
ok(res["campaign_state"] == "PAUSED_NEEDS_HUMAN_REVIEW",
   "engine still P20-pauses on EXPLICIT_PERCENTAGE_PARTIAL_CLOSE (fail-closed; engine mapping "
   "is OUTSIDE this bounded fix and stays conservative)")

print(f"\nPASS {PASS} quantity-base guard + constitution checks")
