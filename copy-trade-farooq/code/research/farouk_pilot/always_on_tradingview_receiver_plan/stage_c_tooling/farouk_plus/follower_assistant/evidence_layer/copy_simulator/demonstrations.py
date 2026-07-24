"""Phase 13 — three brokerless demonstrations (RESEARCH-ONLY / SIMULATION_ONLY). Writes sample outputs
+ campaign-level and aggregate fidelity reports. All fixtures: eligible_for_training=false,
eligible_for_performance_attribution=false.
"""
from __future__ import annotations

import io
import json
import os
import sys
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import copy_execution_simulator as S                             # noqa: E402
import copy_fidelity_metrics as M                                # noqa: E402
import reconciliation as RC                                      # noqa: E402

DEC = 1_000_000
OUT = os.path.join(HERE, "sample_outputs")
os.makedirs(OUT, exist_ok=True)


def b(ts, o, h, l, c):
    return (ts, D(str(o)), D(str(h)), D(str(l)), D(str(c)))


def demo_a():
    """Full Lane A lifecycle: 3 legs -> fills -> unscoped BE -> take-some -> cancel unfilled -> close."""
    prop = {"campaign_id": "SIM-A-LANE-A-LIFECYCLE", "direction": "LONG", "zone_low": "4007",
            "zone_high": "4019", "sl": "3985", "decision_ts": DEC, "receipt_ts": DEC, "source_message_hash": "demoA"}
    bars = [b(DEC + 60, 4018, 4020, 4012, 4015), b(DEC + 120, 4013, 4016, 4008, 4014), b(DEC + 180, 4014, 4035, 4013, 4030)]
    ins = [{"type": "SL_TO_ENTRY", "ts": DEC + 240}, {"type": "TAKE_SOME", "ts": DEC + 300},
           {"type": "RISK_OFF", "ts": DEC + 300}, {"type": "FINAL_CLOSE", "ts": DEC + 600}]
    return S.simulate(prop, bars, ins)


def demo_b():
    """Delay + price-drift: proposal received 300s after decision, zone touched during the delay."""
    prop = {"campaign_id": "SIM-B-DELAY-DRIFT", "direction": "LONG", "zone_low": "4007",
            "zone_high": "4019", "sl": "3985", "decision_ts": DEC, "receipt_ts": DEC + 300, "source_message_hash": "demoB"}
    bars = [b(DEC + 60, 4015, 4019, 4008, 4012),                 # zone touched BEFORE receipt (missed)
            b(DEC + 360, 4025, 4026, 4024, 4025)]                # after receipt price drifted away
    return S.simulate(prop, bars, [])


def demo_c():
    """Ambiguous intrabar: a single bar spans a far-leg entry AND the shared stop."""
    prop = {"campaign_id": "SIM-C-AMBIGUOUS", "direction": "LONG", "zone_low": "4007",
            "zone_high": "4019", "sl": "3985", "decision_ts": DEC, "receipt_ts": DEC, "source_message_hash": "demoC"}
    bars = [b(DEC + 60, 4015, 4019, 3980, 4000)]                 # spans 4007 (far) and 3985 (stop)
    return S.simulate(prop, bars, [])


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sims = [demo_a(), demo_b(), demo_c()]
    for s in sims:
        json.dump(s, open(os.path.join(OUT, f"{s['campaign_id']}.json"), "w", encoding="utf-8"), indent=1, default=str)
    camp = [M.campaign_fidelity(s) for s in sims]
    agg = M.aggregate(sims)
    json.dump({"campaign_fidelity": camp}, open(os.path.join(OUT, "campaign_fidelity_report.json"), "w", encoding="utf-8"), indent=1, default=str)
    json.dump(agg, open(os.path.join(OUT, "aggregate_fidelity_report.json"), "w", encoding="utf-8"), indent=1, default=str)

    a, bb, c = sims
    print("DEMO A (Lane A lifecycle):")
    for lg in a["legs"]:
        print(f"   {lg['leg']}: {lg['state']} fill={lg['fill_price']} BE={lg['be_price']} open={lg['open_size']}")
    print("   reconciliation:", a["reconciliation"])
    print("DEMO B (delay/drift): zone_touched_before_receipt=", bb["zone_touched_before_receipt"],
          "| intent_ts>decision:", bb["intent_timestamp"] > bb["decision_timestamp"],
          "| any pre-receipt fill:", any(lg["fill_ts"] is not None and lg["fill_ts"] < bb["intent_timestamp"] for lg in bb["legs"]))
    print("DEMO C (ambiguous): ambiguous_intrabar=", c["ambiguous_intrabar_present"], "reconciliation=", c["reconciliation"],
          "| perf_attr_eligible:", c["eligible_for_performance_attribution"])
    print("AGGREGATE: 3-leg fidelity", agg["three_leg_fidelity"]["rate"], "| reconciliation_rate", agg["reconciliation_rate"]["rate"],
          "| ambiguous_rate", agg["ambiguous_intrabar_rate"]["rate"], "|", agg.get("sample_warning", ""))
    print("all fixtures eligible_for_training=False, eligible_for_performance_attribution=False")
    print("wrote sample outputs + fidelity reports ->", OUT)


if __name__ == "__main__":
    main()
