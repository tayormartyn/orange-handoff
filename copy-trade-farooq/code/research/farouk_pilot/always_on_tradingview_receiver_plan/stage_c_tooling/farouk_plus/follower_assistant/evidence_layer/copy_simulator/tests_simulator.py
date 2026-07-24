"""Brokerless copy-simulator tests (RESEARCH-ONLY). Active tests per the work-order Phase-12 list."""
from __future__ import annotations

import io
import json
import os
import sys
from decimal import Decimal as D
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
FA = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, FA)
import copy_execution_simulator as S                             # noqa: E402
import reconciliation as RC                                      # noqa: E402
import copy_fidelity_metrics as M                                # noqa: E402

PASS = 0
FAIL = 0


def ok(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {name}")


DEC = 1_000_000


def prop(direction="LONG", zl="4007", zh="4019", sl="3985", receipt=None):
    return {"campaign_id": "XAU-SIM", "direction": direction, "zone_low": zl, "zone_high": zh,
            "sl": sl, "decision_ts": DEC, "receipt_ts": receipt if receipt is not None else DEC,
            "source_message_hash": "abc", "proposal_version": "v0"}


def b(ts, o, h, l, c):
    return (ts, D(str(o)), D(str(h)), D(str(l)), D(str(c)))


# ---- Constitution v0.1 fidelity ---------------------------------------------------------------
def test_constitution_fidelity():
    con = json.load(open(os.path.join(FA, "follower_constitution_v0_1.json"), encoding="utf-8"))
    prof = S.PROFILES["LANE_A_CONSTITUTION_V0_1"]
    ok("Lane A per-leg BE", prof["be_basis"] == "PER_LEG")
    ok("Lane A cancel unfilled at risk-off", prof["unfilled_riskoff"] == "CANCEL")
    ok("Lane A vague take-some = 25%", prof["vague_take_some"] == Fraction(1, 4))
    blob = json.dumps(con)
    ok("constitution documents 3 near/mid/far legs", "near/mid/far" in blob)
    ok("constitution documents 0.25 take-some", "0.25" in blob)
    ok("simulator pins constitution sha", S.CONSTITUTION_SHA.startswith("7bce618f"))


def test_three_leg_creation():
    r = S.simulate(prop(), [b(DEC + 60, 4018, 4020, 4006, 4015)], [])
    ok("three legs created", len(r["legs"]) == 3)
    ok("legs are near/mid/far", [l["leg"] for l in r["legs"]] == ["near", "mid", "far"])


def test_per_leg_be():
    bars = [b(DEC + 60, 4018, 4019, 4012, 4015), b(DEC + 120, 4013, 4014, 4007, 4010)]
    r = S.simulate(prop(), bars, [{"type": "SL_TO_ENTRY", "ts": DEC + 180}])
    filled = [l for l in r["legs"] if l["state"] == "FILLED"]
    ok("BE set per-leg to each fill price", all(l["be_price"] == l["fill_price"] for l in filled) and filled)


def test_vague_take_some_25():
    bars = [b(DEC + 60, 4018, 4019, 4017, 4018)]
    r = S.simulate(prop(), bars, [{"type": "TAKE_SOME", "ts": DEC + 120}])
    near = [l for l in r["legs"] if l["leg"] == "near"][0]
    ok("25% closed on vague take-some", near["open_size"] == str(Fraction(1, 3) * Fraction(3, 4)))


def test_cancel_unfilled_legs():
    bars = [b(DEC + 60, 4018, 4019, 4017, 4018)]                 # only near fills
    r = S.simulate(prop(), bars, [{"type": "RISK_OFF", "ts": DEC + 120}])
    states = {l["leg"]: l["state"] for l in r["legs"]}
    ok("unfilled legs cancelled at risk-off", states["mid"] == "CANCELLED" and states["far"] == "CANCELLED")
    ok("filled leg retained", states["near"] == "FILLED")


# ---- operational: duplicate / delayed / stale / zone-touched-before-receipt --------------------
def test_duplicate_message_idempotent():
    ins = [{"type": "SL_TO_ENTRY", "ts": DEC + 180}, {"type": "SL_TO_ENTRY", "ts": DEC + 180}]  # dup
    bars = [b(DEC + 60, 4018, 4019, 4017, 4018)]                 # only near fills -> exactly 1 BE mod
    r = S.simulate(prop(), bars, ins)
    filled = [l for l in r["legs"] if l["state"] == "FILLED"]
    mods = [e for e in r["events"] if e["record_type"] == "SIMULATED_MODIFY" and e["detail"] == "BE_PER_LEG"]
    ok("duplicate instruction -> BE applied once per filled leg, not doubled", len(mods) == len(filled) == 1)


def test_delayed_and_zone_touched_before_receipt():
    # receipt 300s after decision; zone touched during the delay
    bars = [b(DEC + 60, 4015, 4019, 4008, 4012), b(DEC + 360, 4020, 4021, 4019, 4020)]
    r = S.simulate(prop(receipt=DEC + 300), bars, [])
    ok("zone touched before receipt flagged", r["zone_touched_before_receipt"] is True)
    ok("intent timestamp = receipt (>= decision)", r["intent_timestamp"] == DEC + 300)
    ok("no fill from pre-receipt bar (causal)", all(l["fill_ts"] is None or l["fill_ts"] >= DEC + 300 for l in r["legs"]))


def test_future_bar_rejection():
    # a bar strictly before intent must never fill a leg
    bars = [b(DEC - 60, 4018, 4019, 4006, 4007)]                 # before decision
    r = S.simulate(prop(), bars, [])
    ok("pre-intent bar rejected (no fills)", all(l["state"] != "FILLED" for l in r["legs"]))


# ---- gaps + ambiguity -------------------------------------------------------------------------
def test_gap_through_entry():
    # bar opens below far leg (gaps through) -> gap fill at open
    bars = [b(DEC + 60, 4000, 4001, 3999, 4000)]                 # opens below 4007 (far), stop 3985 not touched
    r = S.simulate(prop(), bars, [])
    far = [l for l in r["legs"] if l["leg"] == "far"][0]
    ok("gap-through entry fills at open", far["state"] == "FILLED" and far["gap_fill"] is True and far["fill_price"] == "4000")


def test_same_bar_entry_stop_ambiguous():
    bars = [b(DEC + 60, 4015, 4019, 3980, 4000)]                 # spans far entry 4007 AND stop 3985
    r = S.simulate(prop(), bars, [])
    ok("same-bar entry+stop -> AMBIGUOUS_INTRABAR_ORDER", r["ambiguous_intrabar_present"] is True)
    amb = [l for l in r["legs"] if l["ambiguous_intrabar"]]
    ok("ambiguous leg not eligible for perf attribution", r["eligible_for_performance_attribution"] is False and amb)
    ok("reconciliation AMBIGUOUS", r["reconciliation"] == "AMBIGUOUS")
    # no profitable ordering chosen: an AMBIGUITY_STATE event records both cases, not a pick
    a = [e for e in r["events"] if e.get("detail") == "AMBIGUOUS_INTRABAR_ORDER"][0]
    ok("both cases recorded, unresolved primary", a["pessimistic_case"] and a["optimistic_case"] and a["unresolved_primary"])


# ---- duplicate / out-of-order bars ------------------------------------------------------------
def test_duplicate_and_out_of_order_bars():
    bars = [b(DEC + 120, 4013, 4014, 4007, 4010), b(DEC + 60, 4018, 4019, 4012, 4015)]  # out of order
    r1 = S.simulate(prop(), bars, [])
    r2 = S.simulate(prop(), bars + [bars[0]], [])               # + duplicate
    ok("dup + out-of-order bars -> identical canonical hash", r1["canonical_hash"] == r2["canonical_hash"])


# ---- restart idempotency + ledger reconstruction ----------------------------------------------
def test_restart_and_ledger_reconstruction():
    bars = [b(DEC + 60, 4018, 4019, 4012, 4015), b(DEC + 120, 4013, 4014, 4007, 4010)]
    ins = [{"type": "SL_TO_ENTRY", "ts": DEC + 180}, {"type": "RISK_OFF", "ts": DEC + 200}]
    r1 = S.simulate(prop(), bars, ins)
    r2 = S.simulate(prop(), bars, ins)
    ok("restart determinism: identical hash", r1["canonical_hash"] == r2["canonical_hash"])
    recon = RC.reconstruct_from_ledger(r1["events"])
    live = {l["leg"]: l["state"] for l in r1["legs"]}
    ok("ledger replay reconstructs the same leg states", all(recon.get(k, {}).get("state") == v for k, v in live.items()))


# ---- reconciliation divergence detection ------------------------------------------------------
def test_reconciliation_divergence():
    bars = [b(DEC + 60, 4018, 4019, 4012, 4015)]
    r = S.simulate(prop(), bars, [])
    clean = RC.reconcile(r["events"])
    ok("clean run RECONCILED", clean["status"] == "RECONCILED")
    # inject a duplicate fill event -> must be DETECTED, never silently repaired
    poisoned = list(r["events"]) + [{"record_type": "SIMULATED_FILL", "leg": "near", "event_timestamp": DEC + 99}]
    d = RC.reconcile(poisoned)
    ok("injected duplicate fill -> DIVERGENCE_DETECTED", d["status"] == "DIVERGENCE_DETECTED")
    ok("divergence not silently repaired", d["silent_repair"] is False and any(x["class"] == "DUPLICATE_FILL" for x in d["divergences"]))
    # fill-after-cancellation
    p2 = list(r["events"]) + [{"record_type": "SIMULATED_CANCEL", "leg": "near", "event_timestamp": DEC + 50},
                              {"record_type": "SIMULATED_FILL", "leg": "near", "event_timestamp": DEC + 200}]
    ok("fill-after-cancel detected", any(x["class"] == "FILL_AFTER_CANCELLATION" for x in RC.reconcile(p2)["divergences"]))


# ---- profile isolation + Lane A immutability --------------------------------------------------
def test_profile_isolation():
    bars = [b(DEC + 60, 4018, 4019, 4012, 4015), b(DEC + 120, 4013, 4014, 4010, 4013)]
    ins = [{"type": "SL_TO_ENTRY", "ts": DEC + 180}]
    a = S.simulate(prop(), bars, ins, profile="LANE_A_CONSTITUTION_V0_1")
    w = S.simulate(prop(), bars, ins, profile="WHALEROOM_COMPARATOR_RESEARCH_ONLY")
    bb = S.simulate(prop(), bars, ins, profile="LANE_B_EXECUTION_ALTERNATIVES_RESEARCH_ONLY")
    ok("profiles produce separate states (distinct hashes)", len({a["canonical_hash"], w["canonical_hash"], bb["canonical_hash"]}) >= 2)
    # Lane A BE is per-leg; Whaleroom BE is campaign-average -> different BE detail
    a_be = [e["detail"] for e in a["events"] if e["record_type"] == "SIMULATED_MODIFY"]
    w_be = [e["detail"] for e in w["events"] if e["record_type"] == "SIMULATED_MODIFY"]
    ok("Lane A per-leg BE unchanged by other profiles", "BE_PER_LEG" in a_be and "BE_PER_LEG" not in w_be)
    ok("Lane A result identical when re-run (not rewritten by Whaleroom run)",
       a["canonical_hash"] == S.simulate(prop(), bars, ins, profile="LANE_A_CONSTITUTION_V0_1")["canonical_hash"])


def test_cost_scenario_isolation():
    bars = [b(DEC + 60, 4018, 4019, 4012, 4015)]
    z = S.simulate(prop(), bars, [], cost_scenario="ZERO_COST", cost_cfg={"spread_usd": "0", "slippage_usd": "0"})
    p = S.simulate(prop(), bars, [], cost_scenario="PESSIMISTIC", cost_cfg={"spread_usd": "0.50", "slippage_usd": "0.50"})
    ok("cost assumptions visible in result", z["cost_assumptions"]["penalty_per_unit_usd"] == "0" and p["cost_assumptions"]["penalty_per_unit_usd"] == "1.00")
    # cost scenario does NOT change the underlying leg states/fills (strategy outcome unchanged)
    ok("cost scenario does not rewrite leg fills", [l["fill_price"] for l in z["legs"]] == [l["fill_price"] for l in p["legs"]])


# ---- broker / credential surface prohibition + stamps -----------------------------------------
def test_no_broker_or_credential_surface():
    r = S.simulate(prop(), [b(DEC + 60, 4018, 4019, 4012, 4015)], [])
    ok("SIMULATION_ONLY stamped", r["SIMULATION_ONLY"] is True)
    ok("NO_BROKER_EXECUTION stamped", r["NO_BROKER_EXECUTION"] is True)
    ok("not perf-attribution eligible", r["eligible_for_performance_attribution"] is False)
    # dangerous IDENTIFIERS only (the safety stamps legitimately contain 'broker'/'credential' words)
    blob = json.dumps(r).lower()
    for tok in ("api_key", "ctrader_order", "lot_size", "account_id", "submit_order", "broker_route", "leverage", "place_order"):
        ok(f"no '{tok}' surface in simulation output", tok not in blob)
    # source-file surface check: real execution code, not safety-disclaimer words
    src = open(os.path.join(HERE, "copy_execution_simulator.py"), encoding="utf-8").read().lower()
    for tok in ("import ctrader", "broker_api", "place_order(", "submit_order(", "api_key", "os.environ", "requests.post"):
        ok(f"simulator source free of '{tok}'", tok not in src)


def test_unknown_instruction_fails_closed():
    r = S.simulate(prop(), [b(DEC + 60, 4018, 4019, 4012, 4015)], [{"type": "DO_SOMETHING_WEIRD", "ts": DEC + 120}])
    ok("unknown instruction -> MANUAL_REVIEW_REQUIRED", any(m["result"] == "MANUAL_REVIEW_REQUIRED" for m in r["manual_review"]))
    ok("unknown instruction -> NO state mutation", all(l["be_price"] is None for l in r["legs"]))


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    for fn in [test_constitution_fidelity, test_three_leg_creation, test_per_leg_be, test_vague_take_some_25,
               test_cancel_unfilled_legs, test_duplicate_message_idempotent,
               test_delayed_and_zone_touched_before_receipt, test_future_bar_rejection, test_gap_through_entry,
               test_same_bar_entry_stop_ambiguous, test_duplicate_and_out_of_order_bars,
               test_restart_and_ledger_reconstruction, test_reconciliation_divergence,
               test_profile_isolation, test_cost_scenario_isolation, test_no_broker_or_credential_surface,
               test_unknown_instruction_fails_closed]:
        fn()
    print(f"\n{PASS} passed, {FAIL} failed")
    print("TRADINGVIEW_PRICE_SEMANTICS_UNVERIFIED | BROKER_EXECUTION_EQUIVALENCE_UNPROVEN | SIMULATION_ONLY")
    sys.exit(1 if FAIL else 0)
