"""Pre-activation live-shadow companion tests (RESEARCH-ONLY). Fully sandboxed ledgers/cursor; the
genuine ledgers are never touched. record_class = SYNTHETIC_LIVE_SHADOW_TEST.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import sys
import tempfile
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
EVDIR = os.path.dirname(HERE)
FA = os.path.dirname(EVDIR)
for p in (HERE, EVDIR, FA):
    if p not in sys.path:
        sys.path.insert(0, p)
import strategy_router as R                                       # noqa: E402
import live_shadow_simulator as LS                               # noqa: E402

PASS = 0
FAIL = 0
DEC = 1_000_000


def ok(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {name}")


def bar(ts, o, h, l, c):
    return (ts, D(str(o)), D(str(h)), D(str(l)), D(str(c)))


def make_freeze(rclass="PROSPECTIVE", sid="XAU-F970-SHADOW"):
    from datetime import datetime, timezone
    pre = [bar(DEC - (60 - i) * 60, 4011, 4013, 4009, 4011) for i in range(60)]
    # receipt ISO must match decision_ts so post-decision bars are actually eligible (fixture realism)
    src_iso = datetime.fromtimestamp(DEC, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return R.freeze_router(setup_id=sid, direction="LONG", zone_low="4007", zone_high="4019",
                           sl="3985", decision_ts=DEC, bars=pre, record_class=rclass,
                           raw_source_ref={"pretrade_logical_hash": "abc", "source_message_utc": src_iso},
                           activation_ts=DEC - 100)


def sandbox(tmp):
    return {"camp": os.path.join(tmp, "camp.jsonl"), "events": os.path.join(tmp, "events.jsonl"),
            "recon": os.path.join(tmp, "recon.jsonl"), "fid": os.path.join(tmp, "fid.jsonl")}


def _genuine_state():
    out = {}
    for f in (LS.CAMP_LEDGER, LS.EVENT_LEDGER, LS.RECON_LEDGER, LS.FID_LEDGER):
        out[f] = (os.path.getsize(f) if os.path.exists(f) else 0)
    return out


def write_freeze(path, fz):
    open(path, "w", encoding="utf-8").write(json.dumps(fz, default=str) + "\n")


BARS = ([bar(DEC + 60, 4018, 4020, 4012, 4015), bar(DEC + 120, 4013, 4016, 4008, 4014),
         bar(DEC + 180, 4014, 4035, 4013, 4030)])
INS = [{"type": "SL_TO_ENTRY", "ts": DEC + 240}, {"type": "TAKE_SOME", "ts": DEC + 300},
       {"type": "RISK_OFF", "ts": DEC + 300}, {"type": "FINAL_CLOSE", "ts": DEC + 600}]


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    genuine_before = _genuine_state()
    tmp = tempfile.mkdtemp(prefix="liveshadow_")
    fl = os.path.join(tmp, "freeze.jsonl")
    cur = os.path.join(tmp, "cursor.json")
    L = sandbox(tmp)
    fz = make_freeze()
    write_freeze(fl, fz)

    def run(cursor=cur, profiles=("LANE_A_CONSTITUTION_V0_1",), rco="SYNTHETIC_LIVE_SHADOW_TEST"):
        return LS.run_cycle(freeze_ledger=fl, bars=BARS, instructions_for=lambda sid: INS,
                            ledgers=L, cursor_path=cursor, record_class_override=rco, profiles=profiles)

    # 1) full lifecycle through the REAL companion run_cycle
    a1 = run()
    ok("companion self-discovers + simulates", any("LIVE_SHADOW_SIMULATED(" in a for a in a1))
    camp = [json.loads(l) for l in open(L["camp"], encoding="utf-8")]
    ok("exactly one shadow campaign", len(camp) == 1)
    sim = camp[0]["campaign"]
    legs = {lg["leg"]: lg for lg in sim["legs"]}
    ok("three Lane A legs", set(legs) == {"near", "mid", "far"})
    ok("per-leg BE applied", legs["near"]["be_price"] == legs["near"]["fill_price"])
    ok("unfilled far leg cancelled at risk-off", legs["far"]["state"] == "CANCELLED")
    ok("campaign closed flat", all(lg["open_size"] == "0" for lg in sim["legs"]))
    ok("reconciliation RECONCILED", sim["reconciliation"] == "RECONCILED")

    # 2) record class + eligibility + stamps
    ok("record_class SYNTHETIC_LIVE_SHADOW_TEST", camp[0]["record_class"] == "SYNTHETIC_LIVE_SHADOW_TEST")
    ok("SIMULATION_ONLY + NO_BROKER", camp[0]["SIMULATION_ONLY"] and camp[0]["NO_BROKER_EXECUTION"])
    ok("training + perf-attr ineligible", camp[0]["eligible_for_training"] is False and camp[0]["eligible_for_performance_attribution"] is False)

    # 3) ledger isolation — genuine ledgers untouched; test writes to sandbox
    ok("genuine live-shadow ledgers untouched", _genuine_state() == genuine_before)
    ok("test wrote to sandbox events/recon/fid", os.path.exists(L["events"]) and os.path.exists(L["recon"]) and os.path.exists(L["fid"]))

    # 4) idempotency: re-run same cursor -> no duplicate campaign
    run()
    ok("duplicate run -> no second campaign", sum(1 for _ in open(L["camp"])) == 1)
    # restart: fresh cursor, but writes append -> the guard is the done-tag; fresh cursor would re-add.
    # prove canonical determinism instead: same inputs -> identical campaign canonical hash
    L2 = sandbox(os.path.join(tmp, "d2")); os.makedirs(os.path.join(tmp, "d2"), exist_ok=True)
    LS.run_cycle(freeze_ledger=fl, bars=BARS, instructions_for=lambda sid: INS, ledgers=L2,
                 cursor_path=os.path.join(tmp, "cur2.json"), record_class_override="SYNTHETIC_LIVE_SHADOW_TEST")
    sim2 = json.loads(open(L2["camp"], encoding="utf-8").readline())["campaign"]
    ok("restart reconstruction: identical canonical hash", sim["canonical_hash"] == sim2["canonical_hash"])

    # 5) duplicate + out-of-order bars -> identical hash
    L3 = sandbox(os.path.join(tmp, "d3")); os.makedirs(os.path.join(tmp, "d3"), exist_ok=True)
    LS.run_cycle(freeze_ledger=fl, bars=list(reversed(BARS)) + [BARS[0]], instructions_for=lambda sid: INS,
                 ledgers=L3, cursor_path=os.path.join(tmp, "cur3.json"), record_class_override="SYNTHETIC_LIVE_SHADOW_TEST")
    sim3 = json.loads(open(L3["camp"], encoding="utf-8").readline())["campaign"]
    ok("dup + out-of-order bars -> identical hash", sim["canonical_hash"] == sim3["canonical_hash"])

    # 6) authentic gate: WITHOUT override, non-genuine classes are rejected
    for rc in ("SCHEMA_BACKFILL_NOT_PROSPECTIVE", "ACTIVATION_STRADDLE", "SYNTHETIC_INTEGRATION_TEST"):
        flx = os.path.join(tmp, f"fz_{rc}.jsonl"); write_freeze(flx, make_freeze(rclass=rc, sid=f"XAU-{rc}"))
        Lx = sandbox(os.path.join(tmp, rc)); os.makedirs(os.path.join(tmp, rc), exist_ok=True)
        acts = LS.run_cycle(freeze_ledger=flx, bars=BARS, instructions_for=lambda sid: INS, ledgers=Lx,
                            cursor_path=os.path.join(tmp, f"cur_{rc}.json"), record_class_override=None)
        ok(f"authentic gate rejects {rc}", not os.path.exists(Lx["camp"]) and not acts)

    # 7) same-bar ambiguity fails closed
    L4 = sandbox(os.path.join(tmp, "amb")); os.makedirs(os.path.join(tmp, "amb"), exist_ok=True)
    LS.run_cycle(freeze_ledger=fl, bars=[bar(DEC + 60, 4015, 4019, 3980, 4000)], instructions_for=lambda sid: [],
                 ledgers=L4, cursor_path=os.path.join(tmp, "cur4.json"), record_class_override="SYNTHETIC_LIVE_SHADOW_TEST")
    sim4 = json.loads(open(L4["camp"], encoding="utf-8").readline())["campaign"]
    ok("same-bar ambiguity -> AMBIGUOUS_INTRABAR_ORDER", sim4["ambiguous_intrabar_present"] is True and sim4["reconciliation"] == "AMBIGUOUS")
    ok("ambiguous perf-attr ineligible", sim4["eligible_for_performance_attribution"] is False)

    # 8) profile isolation
    L5 = sandbox(os.path.join(tmp, "prof")); os.makedirs(os.path.join(tmp, "prof"), exist_ok=True)
    LS.run_cycle(freeze_ledger=fl, bars=BARS, instructions_for=lambda sid: INS, ledgers=L5,
                 cursor_path=os.path.join(tmp, "cur5.json"), record_class_override="SYNTHETIC_LIVE_SHADOW_TEST",
                 profiles=("LANE_A_CONSTITUTION_V0_1", "WHALEROOM_COMPARATOR_RESEARCH_ONLY", "LANE_B_EXECUTION_ALTERNATIVES_RESEARCH_ONLY"))
    camps5 = [json.loads(l)["campaign"] for l in open(L5["camp"], encoding="utf-8")]
    profs = {c["profile"] for c in camps5}
    ok("three profiles simulated separately", profs == {"LANE_A_CONSTITUTION_V0_1", "WHALEROOM_COMPARATOR_RESEARCH_ONLY", "LANE_B_EXECUTION_ALTERNATIVES_RESEARCH_ONLY"})
    lane_a = [c for c in camps5 if c["profile"] == "LANE_A_CONSTITUTION_V0_1"][0]
    ok("Lane A unchanged across profile run (matches single-profile hash)", lane_a["canonical_hash"] == sim["canonical_hash"])

    # 9) broker/credential surface absent in the shadow module + output
    src = open(os.path.join(HERE, "live_shadow_simulator.py"), encoding="utf-8").read().lower()
    for tok in ("import ctrader", "broker_api", "place_order(", "submit_order(", "api_key", "os.environ", "requests.post"):
        ok(f"shadow module free of '{tok}'", tok not in src)
    blob = json.dumps(camp[0]).lower()
    for tok in ("api_key", "ctrader_order", "lot_size", "account_id", "submit_order", "leverage"):
        ok(f"shadow output free of '{tok}'", tok not in blob)

    print(f"\n{PASS} passed, {FAIL} failed")
    print("TRADINGVIEW_PRICE_SEMANTICS_UNVERIFIED | BROKER_EXECUTION_EQUIVALENCE_UNPROVEN | SIMULATION_ONLY")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
