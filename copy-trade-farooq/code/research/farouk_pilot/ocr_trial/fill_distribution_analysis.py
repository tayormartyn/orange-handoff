"""LANE_A_ENTRY_MODEL_ADVERSE_DIVERGENCE — fill-placement distribution analysis.

TRUST-GATED: refuses to run until the 10-image operator sample is verified clean
(operator creates operator_sample_verified.flag in this directory — D-046 round).

Measures, for every XAU card row joinable to a published campaign zone:
  relative position of his fill within the zone -> bottom / middle / top third
  (for LONGs the three-leg model places legs at bottom edge / mid / top edge;
   mid-zone clustering = the F006/F007 mechanism operating systematically).
Also the signed distance from the nearest model leg.

Survivorship-limited (posted cards only). MECHANICAL comparison ONLY. NEVER expectancy.
This distribution is the frozen parameter source for the Lane B entry-placement
candidate (D-044) — parameters freeze FROM this output, before any scoring.
"""
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ST = r"C:\Users\Marty\signal-terminal"
FWD = os.path.join(ST, r"research\farouk_pilot\always_on_tradingview_receiver_plan"
                       r"\stage_c_tooling\farouk_plus\forward_validation_ledger_v0_2.jsonl")
ROWS = os.path.join(HERE, "source_reported_outcome_v0_1.jsonl")
FLAG = os.path.join(HERE, "operator_sample_verified.flag")
OUT = os.path.join(HERE, "FILL_DISTRIBUTION_ANALYSIS.md")

if not os.path.exists(FLAG):
    sys.exit("TRUST GATE: operator_sample_verified.flag missing — the 10-image sample has "
             "not been verified clean. Refusing to run (D-046).")


def parse_ts(s):
    s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def main():
    # latest revision per campaign, with zone + timestamp
    setups = {}
    for ln in open(FWD, encoding="utf-8"):
        r = json.loads(ln)
        if r.get("record_type") == "XAU_F_SETUP" and r.get("entry_zone"):
            lo, hi = sorted(float(x) for x in r["entry_zone"].split("-"))
            setups[r["setup_id"]] = {"lo": lo, "hi": hi, "dir": r.get("direction"),
                                     "ts": parse_ts(r["timestamp_utc"])}
    cards = [json.loads(l) for l in open(ROWS, encoding="utf-8")]
    matched, unmatched, thirds = [], 0, {"bottom": 0, "middle": 0, "top": 0}
    for c in cards:
        cts = parse_ts(c["posted_at_utc"])
        for x in c["rows"]:
            if x["entry"] >= 10000 or "STD" in x.get("symbol", "").upper():
                continue                       # crypto-scoped / OQ-12 quarantined
            best = None
            for sid, s in setups.items():
                if s["lo"] - 3 <= x["entry"] <= s["hi"] + 3 and \
                        0 <= (cts - s["ts"]).total_seconds() <= 48 * 3600:
                    best = (sid, s)
            if not best:
                unmatched += 1
                continue
            sid, s = best
            h = s["hi"] - s["lo"]
            rel = (x["entry"] - s["lo"]) / h if h else 0.5
            rel = max(0.0, min(1.0, rel))
            third = "bottom" if rel < 1 / 3 else ("middle" if rel < 2 / 3 else "top")
            thirds[third] += 1
            legs = [s["lo"], (s["lo"] + s["hi"]) / 2, s["hi"]]
            nearest = min(legs, key=lambda p: abs(p - x["entry"]))
            matched.append({"campaign": sid, "msg": c["message_id"], "fill": x["entry"],
                            "zone": [s["lo"], s["hi"]], "rel_position": round(rel, 3),
                            "third": third, "nearest_model_leg": nearest,
                            "delta_from_nearest_leg": round(x["entry"] - nearest, 2)})
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("# FILL-PLACEMENT DISTRIBUTION (D-046 round)\n\n")
        f.write("**Survivorship-limited (posted cards only). Mechanical comparison only. "
                "NEVER expectancy.**\n\n")
        f.write(f"Matched fills: {len(matched)} | unmatched (no ledger zone within 48h, "
                f"incl. pre-F001 era): {unmatched}\n\n")
        f.write(f"## Distribution across zone thirds\n{json.dumps(thirds, indent=1)}\n\n")
        f.write("## Per-fill rows\n")
        for m in matched:
            f.write(f"- {m['campaign']} msg {m['msg']}: fill {m['fill']} in {m['zone']} "
                    f"rel {m['rel_position']} ({m['third']}); nearest leg {m['nearest_model_leg']} "
                    f"delta {m['delta_from_nearest_leg']}\n")
    print(f"matched {len(matched)} | unmatched {unmatched} | thirds {thirds}")
    print("->", OUT)


if __name__ == "__main__":
    main()
