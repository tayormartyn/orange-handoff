"""
Farouk-Plus Shadow Engine Step 1 — winner/loss comparison table (offline, observation-only).

Static metadata hand-curated from the Day-1/Day-3 ledgers + Day-2/4/5 adjudications.
Price features computed deterministically from the imported exports:
  1m (2026-06-21 22:01 .. 07-10) for late setups, 5m (05-18 .. 07-10) for earlier June.
Conventions: pip=$0.10; MFE/MAE measured from ZONE MID over signal..signal+6h; first-touch =
zone NOT traded in the 4h before signal; displacement = first bar with >= $5.00 favourable from
zone mid after entry touch. No execution surface. RESULT statuses come from Days 2/4/5 (authority).
"""
import csv, json, os, sys, io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BASE = r"C:\Users\Marty\signal-terminal\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling"
SRC_1M = BASE + r"\price_data\XAUUSD_1M_PEPPERSTONE_2026-06-21_to_2026-07-10_FULL_EXPORT.csv"
SRC_5M = BASE + r"\price_data\XAUUSD_5M_PEPPERSTONE_2026-05-18_to_2026-07-10_FULL_EXPORT.csv"
OUTDIR = BASE + r"\farouk_plus"
os.makedirs(OUTDIR, exist_ok=True)
OUT = OUTDIR + r"\winner_loss_comparison_v1.json"

def load(path):
    out = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            out.append((int(r["time"]), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])))
    out.sort()
    return out

B1, B5 = load(SRC_1M), load(SRC_5M)
CUT_1M = B1[0][0]

def iso(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()

# id, signal_utc, dir, zone(lo,hi)|None, sl, status, idea_attempt, internal_reentries, day_index,
# media_captured, claim_accuracy, htf_note
S = [
 ("XAU-J01-20260602","2026-06-02T11:12:18","LONG",(4519,4529),4500,"PARTIAL",1,0,1,False,"SUPPORTED","-"),
 ("XAU-J02-20260602","2026-06-02T13:02:03","LONG",(4505,4514),4480,"VERIFIED_WIN",1,0,2,False,"SUPPORTED","-"),
 ("XAU-J03-20260602","2026-06-02T15:58:50","LONG",(4490,4502),4468,"PARTIAL_LOSS",1,0,3,False,"SUPPORTED","choppy day,他 noted market would not move"),
 ("XAU-J04-20260603","2026-06-03T11:48:33","SHORT",(4463,4470),4487,"VERIFIED_WIN",1,3,1,True,"SUPPORTED","-"),
 ("XAU-J05-20260603","2026-06-03T14:12:56","SHORT",(4456,4462),4480,"VERIFIED_WIN",1,0,2,True,"SUPPORTED","-"),
 ("XAU-J06-20260603","2026-06-03T17:52:04","SHORT",(4440,4446),4470,"VERIFIED_WIN",1,0,3,True,"SUPPORTED","-"),
 ("XAU-J07-20260604","2026-06-04T06:03:34","SHORT",(4474,4485),4515,"VERIFIED_WIN",1,0,1,True,"SUPPORTED","plan-following (prior-day video)"),
 ("XAU-J08-20260604","2026-06-04T11:10:09","SHORT",(4479,4488),4515,"PARTIAL_LOSS",2,0,2,False,"SUPPORTED","same-idea re-entry while J07 runner alive"),
 ("XAU-J09-20260611","2026-06-11T07:58:30","LONG",(4090,4103),4080,"VERIFIED_WIN",1,0,1,True,"SUPPORTED","HIGH RISK label"),
 ("XAU-J10-20260611","2026-06-11T08:22:49","LONG",None,4060,"VERIFIED_LOSS",2,0,2,False,"SUPPORTED","layered re-entry after BE stop"),
 ("XAU-J11-20260611","2026-06-11T13:58:19","LONG",None,4035,"PARTIAL",1,0,3,True,"UNCLEAR_FILL_DEPENDENT","recovery trade, new level"),
 ("XAU-J12-20260615","2026-06-15T09:40:01","SHORT",(4339,4345),4360,"VERIFIED_WIN",1,0,1,False,"SUPPORTED","-"),
 ("XAU-J13-20260615","2026-06-15T14:04:10","LONG",(4350,4355),4330,"VERIFIED_WIN",1,0,2,True,"SUPPORTED","HIGH RISK; above Asia high + 15m FVG"),
 ("XAU-J14-20260615","2026-06-15T14:35:08","LONG",(4348,4358),4330,"VERIFIED_WIN",2,0,3,False,"SUPPORTED","re-enter same setup"),
 ("XAU-J15-20260615","2026-06-15T15:06:22","LONG",(4346,4356),4330,"PARTIAL",3,0,4,False,"SUPPORTED","re-entry"),
 ("XAU-J16-20260615","2026-06-15T15:37:15","LONG",(4340,4350),4330,"PARTIAL",4,0,5,False,"SUPPORTED","low-lot re-entry"),
 ("XAU-J17-20260615","2026-06-15T16:42:35","LONG",(4330,4339),4318,"VERIFIED_LOSS",5,0,6,True,"SUPPORTED","'last re-entry' after 4 scratches"),
 ("XAU-J18-20260616","2026-06-16T09:40:22","SHORT",(4346,4356),4372,"VERIFIED_WIN",1,0,1,True,"SUPPORTED","-"),
 ("XAU-J19-20260616","2026-06-16T10:10:08","SHORT",(4346,4356),4375,"VERIFIED_WIN",2,0,2,True,"SUPPORTED","same zone, second trade"),
 ("XAU-J20-20260617","2026-06-17T08:57:07","LONG",(4315,4323),4295,"VERIFIED_WIN",1,0,1,True,"SUPPORTED","Asia-low sweep + 5m FVG -> BPR target"),
 ("XAU-J21-20260618","2026-06-18T10:18:39","SHORT",(4269,4280),4300,"VERIFIED_WIN",1,0,1,True,"SUPPORTED","-"),
 ("XAU-J22-20260618","2026-06-18T11:12:51","LONG",(4231,4241),4218,"VERIFIED_WIN",1,0,2,True,"SUPPORTED","SL typo in post (4318)"),
 ("XAU-J23-20260619","2026-06-19T09:35:25","LONG",(4154,4164),4135,"PARTIAL_LOSS",1,0,1,False,"SUPPORTED","self-described bad timing both ways"),
 ("XAU-J25-20260623","2026-06-23T13:55:42","SHORT",(4138,4155),4180,"VERIFIED_WIN",1,1,2,True,"SUPPORTED","15m bearish OB + unmitigated FVG"),
 ("XAU-J26-20260624","2026-06-24T14:32:13","SHORT",(4030,4045),4130,"VERIFIED_WIN",1,0,1,True,"SUPPORTED","H4 BOS+H1 nBOS+3m/5m OB confluence; HIGH RISK LOW LOT"),
 ("XAU-J27-20260625","2026-06-25T14:42:30","LONG",(4006,4016),3970,"VERIFIED_WIN",1,0,1,True,"SUPPORTED","-"),
 ("XAU-J28-20260626","2026-06-26T13:58:29","SHORT",(4078,4092),4120,"PARTIAL",1,1,1,True,"SUPPORTED","explicitly AGAINST trend, half size"),
 ("XAU-J29-20260626","2026-06-26T14:12:55","SHORT",(4084,4094),4120,"VERIFIED_WIN",3,0,2,True,"SUPPORTED","3rd execution of the same campaign"),
 ("XAU-J30-20260629","2026-06-29T08:59:32","LONG",(4035,4045),4010,"PARTIAL",1,0,1,True,"CONTRADICTED_MAGNITUDE","+33-56% pip inflation; hard SL traded after exit"),
 ("XAU-S1-20260630","2026-06-30T14:25:23","SHORT",(4060,4075),4100,"VERIFIED_WIN",1,0,1,False,"SUPPORTED_MILD_OVERSTATE","London OB + CHoCH + sweep + daily FVG midpoint"),
 ("XAU-S2-20260707","2026-07-07T11:29:34","SHORT",(4144,4154),4180,"VERIFIED_LOSS",1,0,1,False,"SUPPORTED","counter-trend fade into rally"),
 ("XAU-S3-20260708","2026-07-08T12:14:29","SHORT",(4072,4083),4125,"VERIFIED_WIN",1,0,1,False,"SUPPORTED","-"),
 ("XAU-S4-20260710","2026-07-10T12:43:32","SHORT",(4102,4115),4152,"PARTIAL",1,0,1,True,"SUPPORTED","lost Asia low on 5m/15m/H1"),
]

LON = (7*3600, 11*3600 + 1800)   # 07:00-11:30Z
NY = (13*3600 + 1800, 15*3600 + 1800)  # 13:30-15:30Z

rows = []
for sid, sig_s, d, zone, sl, status, att, internal, dayix, media, claim, htf in S:
    sig = iso(sig_s)
    bars = B1 if sig >= CUT_1M else B5
    res = "1m" if bars is B1 else "5m"
    short = d == "SHORT"
    row = {"setup_id": sid, "signal_utc": sig_s, "direction": d, "sl": sl,
           "outcome_status": status, "idea_attempt": att, "internal_reentries": internal,
           "day_trade_index": dayix, "media_captured": media, "claim_accuracy": claim,
           "htf_note": htf, "precision": res}
    if zone is None:
        row.update({"entry_zone": None, "computed": "LIMITED — no numeric zone posted"})
        rows.append(row)
        continue
    lo, hi = zone
    mid = (lo + hi) / 2
    row["entry_zone"] = f"{lo}-{hi}"
    pre = [b for b in bars if sig - 4*3600 <= b[0] < sig]
    row["zone_pretraded_4h"] = any(b[2] >= lo and b[3] <= hi for b in pre)
    row["first_touch"] = not row["zone_pretraded_4h"]
    seq = [b for b in bars if sig - 300 <= b[0] <= sig + 6*3600]
    eb = next((b for b in seq if b[2] >= lo and b[3] <= hi), None)
    if eb is None:
        row["entry_touched"] = False
        rows.append(row)
        continue
    row["entry_touched"] = True
    tsec = (eb[0] - sig) / 60
    row["entry_touch_min_after_signal"] = round(tsec)
    hh = datetime.fromtimestamp(eb[0], tz=timezone.utc)
    secs = hh.hour*3600 + hh.minute*60
    row["session"] = ("LONDON" if LON[0] <= secs <= LON[1] else
                      "NY_OPEN" if NY[0] <= secs <= NY[1] else "OFF_WINDOW")
    row["entry_hour_utc"] = hh.strftime("%H:%M")
    after = [b for b in seq if b[0] >= eb[0]]
    if short:
        fav = min(b[3] for b in after); adv = max(b[2] for b in after)
        row["mfe_pips_from_mid"] = round((mid - fav) / 0.1)
        row["mae_pips_from_mid"] = round((adv - mid) / 0.1)
        disp = next((b for b in after if mid - b[3] >= 5.0), None)
    else:
        fav = max(b[2] for b in after); adv = min(b[3] for b in after)
        row["mfe_pips_from_mid"] = round((fav - mid) / 0.1)
        row["mae_pips_from_mid"] = round((mid - adv) / 0.1)
        disp = next((b for b in after if b[2] - mid >= 5.0), None)
    row["min_to_50p_from_mid"] = round((disp[0] - eb[0]) / 60) if disp else None
    row["disp_50p_within_60min"] = bool(disp and disp[0] - eb[0] <= 3600)
    rows.append(row)

# ---- group stats ----
def grp(status_pred):
    return [r for r in rows if status_pred(r["outcome_status"])]
W = grp(lambda s: s == "VERIFIED_WIN")
L = grp(lambda s: s in ("VERIFIED_LOSS", "PARTIAL_LOSS"))
P = grp(lambda s: s == "PARTIAL")

def stat(g, key):
    v = [r[key] for r in g if r.get(key) is not None and isinstance(r.get(key), (int, float))]
    return {"n": len(v), "mean": round(sum(v)/len(v), 1) if v else None,
            "median": sorted(v)[len(v)//2] if v else None}

def frac(g, key, val=True):
    v = [r for r in g if r.get(key) is not None]
    return f"{sum(1 for r in v if r[key] == val)}/{len(v)}" if v else "0/0"

groups = {}
for name, g in (("VERIFIED_WIN", W), ("LOSSES(verified+manual)", L), ("PARTIAL(non-loss)", P)):
    groups[name] = {
        "n": len(g),
        "first_touch": frac(g, "first_touch"),
        "disp_50p_within_60min": frac(g, "disp_50p_within_60min"),
        "min_to_50p": stat(g, "min_to_50p_from_mid"),
        "mfe_pips_from_mid": stat(g, "mfe_pips_from_mid"),
        "mae_pips_from_mid": stat(g, "mae_pips_from_mid"),
        "idea_attempt": stat(g, "idea_attempt"),
        "session_counts": {s: sum(1 for r in g if r.get("session") == s) for s in ("LONDON","NY_OPEN","OFF_WINDOW")},
    }

# ---- rule tests ----
def removed_by(pred):
    rem = [r for r in rows if pred(r)]
    return {"removed_total": len(rem),
            "wins_removed": [r["setup_id"] for r in rem if r["outcome_status"] == "VERIFIED_WIN"],
            "losses_removed": [r["setup_id"] for r in rem if r["outcome_status"] in ("VERIFIED_LOSS","PARTIAL_LOSS")],
            "partials_removed": [r["setup_id"] for r in rem if r["outcome_status"] == "PARTIAL"]}

rules = {
 "R1_first_touch_only": removed_by(lambda r: r.get("first_touch") is False),
 "R2_attempt_cap_le2": removed_by(lambda r: r["idea_attempt"] >= 3),
 "R2b_no_reentries_cap_le1": removed_by(lambda r: r["idea_attempt"] >= 2),
 "R3_disp50_within_60min": removed_by(lambda r: r.get("disp_50p_within_60min") is False),
 "R4_session_filter": removed_by(lambda r: r.get("session") == "OFF_WINDOW"),
}

out = {"table_id": "winner_loss_comparison_v1", "generated_on": "2026-07-11",
       "mode": "OBSERVATION_ONLY / REVIEW_ONLY",
       "conventions": "pip=$0.10; MFE/MAE from zone MID over signal..+6h; first-touch = zone untraded in prior 4h; displacement = $5 favourable from mid; statuses from Days 2/4/5 (deterministic authority). PARTIAL_LOSS = his manual-cut losses (J03,J08,J23).",
       "setups": rows, "group_stats": groups, "rule_tests": rules}
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2, ensure_ascii=False)

print(json.dumps(groups, indent=1))
print(json.dumps(rules, indent=1))
print("written:", OUT)
