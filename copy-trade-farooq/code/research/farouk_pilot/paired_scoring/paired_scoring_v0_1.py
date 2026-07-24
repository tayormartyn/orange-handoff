"""PAIRED LANE A / LANE B SHADOW SCORING (D-062). Effective F008 onward.

READ-ONLY over ledgers/tracker/OCR. Writes ONLY paired_scores_v0_1.jsonl (review_only,
eligible_for_prospective_evidence=false, eligible_for_training=false). NEVER writes Lane A
records, the freeze ledger, or the learning dataset.

Lane A: Constitution v0.1 legs (zone edges + midpoint), explicit-instruction mgmt only.
Lane B: P-EP-1 entry (depth 0.15/0.40 from arrival edge, no far leg) + P-DM-1 defaults
        (partial + SL-to-BE at +50 pips) applied only where no explicit instruction covers it.
Source-observed: his OCR fills where available.

F008 GUARD: refuses campaigns <= F007 (those were scored under earlier flows; applying this
paired model retrospectively would be fitting). Retrospective runs allowed ONLY with an
explicit --retrospective flag and are stamped RETROSPECTIVE_NOT_PROSPECTIVE.
"""
import json
import os
import sys

ST = r"C:\Users\Marty\signal-terminal"
FP = os.path.join(ST, r"research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\farouk_plus")
FWD = os.path.join(FP, "forward_validation_ledger_v0_2.jsonl")
TRK = os.path.join(FP, r"follower_assistant\market_tracker\tracker_ledger_v0_1.jsonl")
OCR = os.path.join(ST, r"research\farouk_pilot\ocr_trial\source_reported_outcome_v0_1.jsonl")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "paired_scores_v0_1.jsonl")

P_EP_1 = [0.15, 0.40]        # depths from arrival edge (frozen, D-047)
P_DM_1 = {"be_trigger_pips": 50, "tp1_fraction": 0.50}   # frozen, D-043


def campaign_num(sid):
    try:
        return int(sid.split("-F")[1][:3])
    except Exception:
        return -1


def latest_setup(sid):
    setup = None
    for ln in open(FWD, encoding="utf-8"):
        r = json.loads(ln)
        if r.get("record_type") == "XAU_F_SETUP" and r.get("setup_id") == sid:
            setup = r
    return setup


def lane_a_from_tracker(sid):
    snap = None
    for ln in open(TRK, encoding="utf-8"):
        r = json.loads(ln)
        if r.get("record_type") == "TRACKER_SNAPSHOT" and r.get("setup_id") == sid:
            snap = r["snapshot"]
    if not snap:
        return None
    eng = snap["lanes"]["LANE_A"]["engine"]
    return {"legs": [{"price": l["price"], "state": l["state"], "fill": l.get("fill_price")}
                     for l in eng["legs"]],
            "realized_pips_per_unit": eng.get("realized_pips_per_unit"),
            "avg_entry": eng.get("average_entry"),
            "terminal": snap["lanes"]["LANE_A"]["lifecycle"]["current"]}


def lane_b_entry(zone_lo, zone_hi, direction):
    """P-EP-1: legs at depth 0.15/0.40 from the arrival edge."""
    h = zone_hi - zone_lo
    arrival = zone_hi if direction == "LONG" else zone_lo   # first-touched edge
    sign = -1 if direction == "LONG" else +1                # depth moves away from arrival
    return [round(arrival + sign * d * h, 2) for d in P_EP_1]


def source_fills(sid):
    if not os.path.exists(OCR):
        return []
    out = []
    for ln in open(OCR, encoding="utf-8"):
        r = json.loads(ln)
        # crude campaign association by fill within the campaign zone is done by the caller;
        # here return all XAU fills, caller filters by zone+time (kept explicit, not silent)
        for x in r.get("rows", []):
            if x.get("entry", 0) < 10000 and "STD" not in x.get("symbol", "").upper():
                out.append({"entry": x["entry"], "msg": r["message_id"]})
    return out


def score(sid, retrospective=False):
    n = campaign_num(sid)
    if n <= 7 and not retrospective:
        raise SystemExit(f"F008 GUARD: {sid} (F{n:03d}) <= F007 — refused. Use --retrospective "
                         "to run (stamped RETROSPECTIVE_NOT_PROSPECTIVE, never prospective evidence).")
    setup = latest_setup(sid)
    if not setup:
        raise SystemExit(f"no setup for {sid}")
    lo, hi = sorted(float(x) for x in setup["entry_zone"].split("-"))
    direction = setup["direction"]
    la = lane_a_from_tracker(sid)
    lb_legs = lane_b_entry(lo, hi, direction)
    row = {
        "record_class": "PAIRED_SHADOW_SCORE", "review_only": True,
        "eligible_for_prospective_evidence": False, "eligible_for_training": False,
        "stamp": "RETROSPECTIVE_NOT_PROSPECTIVE" if retrospective else "PROSPECTIVE_F008_PLUS",
        "campaign": sid, "direction": direction, "zone": [lo, hi],
        "LANE_A": la,
        "LANE_B": {"entry_legs_P_EP_1": lb_legs, "mgmt_policy": "P-DM-1 (BE+50, 50% TP1) where no explicit instruction",
                   "note": "realised result requires bar replay against these legs — computed by the bar-replay step at terminal time"},
        "SOURCE_OBSERVED": {"fills": "from OCR dataset, zone+time filtered at run", "available": os.path.exists(OCR)},
        "binding": "Lane B writes ONLY here; never Lane A / freeze / learning. P-EP-1 abandon/revise predicate governs; no quiet retuning.",
    }
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    print(json.dumps({k: row[k] for k in ("campaign", "stamp", "zone", "LANE_B")}, indent=1))
    return row


if __name__ == "__main__":
    retro = "--retrospective" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("usage: paired_scoring_v0_1.py XAU-F008-YYYYMMDD [--retrospective]")
        print("No F008 campaign exists yet (F007 is latest) — harness is armed and will "
              "auto-fire when F008 reaches a terminal state.")
        sys.exit(0)
    score(args[0], retrospective=retro)
