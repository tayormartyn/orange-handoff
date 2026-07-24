"""Step 8 rerun — lane-4 with NEAR-EDGE fills (primary) + mid-zone sensitivity; J11 diagnostics."""
import csv, json, sys, io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BASE = r"C:\Users\Marty\signal-terminal\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling"

def load(p):
    out = []
    with open(p, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            out.append((int(r["time"]), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])))
    out.sort()
    return out

B1 = load(BASE + r"\price_data\XAUUSD_1M_PEPPERSTONE_2026-06-21_to_2026-07-10_FULL_EXPORT.csv")
B5 = load(BASE + r"\price_data\XAUUSD_5M_PEPPERSTONE_2026-05-18_to_2026-07-10_FULL_EXPORT.csv")
CUT = B1[0][0]

def iso(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()

def fmt(t):
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%m-%d %H:%M")

S = [
 ("J01","2026-06-02T11:12:18","LONG",(4519,4529),4500,"PARTIAL",None,None),
 ("J02","2026-06-02T13:02:03","LONG",(4505,4514),4480,"VERIFIED_WIN",None,None),
 ("J03","2026-06-02T15:58:50","LONG",(4490,4502),4468,"PARTIAL_LOSS",-45,None),
 ("J04","2026-06-03T11:48:33","SHORT",(4463,4470),4487,"VERIFIED_WIN",None,None),
 ("J05","2026-06-03T14:12:56","SHORT",(4456,4462),4480,"VERIFIED_WIN",100,None),
 ("J06","2026-06-03T17:52:04","SHORT",(4440,4446),4470,"VERIFIED_WIN",None,None),
 ("J07","2026-06-04T06:03:34","SHORT",(4474,4485),4515,"VERIFIED_WIN",None,None),
 ("J08","2026-06-04T11:10:09","SHORT",(4479,4488),4515,"PARTIAL_LOSS",-50,None),
 ("J09","2026-06-11T07:58:30","LONG",(4090,4103),4080,"VERIFIED_WIN",70,4105.40),
 ("J10","2026-06-11T08:22:49","LONG",None,4060,"VERIFIED_LOSS",None,None),
 ("J11","2026-06-11T13:58:19","LONG",None,4035,"PARTIAL",800,4056.64),
 ("J12","2026-06-15T09:40:01","SHORT",(4339,4345),4360,"VERIFIED_WIN",50,None),
 ("J13","2026-06-15T14:04:10","LONG",(4350,4355),4330,"VERIFIED_WIN",100,4357.05),
 ("J14","2026-06-15T14:35:08","LONG",(4348,4358),4330,"VERIFIED_WIN",100,None),
 ("J15","2026-06-15T15:06:22","LONG",(4346,4356),4330,"PARTIAL",None,None),
 ("J16","2026-06-15T15:37:15","LONG",(4340,4350),4330,"PARTIAL",None,None),
 ("J17","2026-06-15T16:42:35","LONG",(4330,4339),4318,"VERIFIED_LOSS",None,None),
 ("J18","2026-06-16T09:40:22","SHORT",(4346,4356),4372,"VERIFIED_WIN",50,None),
 ("J19","2026-06-16T10:10:08","SHORT",(4346,4356),4375,"VERIFIED_WIN",130,None),
 ("J20","2026-06-17T08:57:07","LONG",(4315,4323),4295,"VERIFIED_WIN",100,None),
 ("J21","2026-06-18T10:18:39","SHORT",(4269,4280),4300,"VERIFIED_WIN",200,4270.91),
 ("J22","2026-06-18T11:12:51","LONG",(4231,4241),4218,"VERIFIED_WIN",None,None),
 ("J23","2026-06-19T09:35:25","LONG",(4154,4164),4135,"PARTIAL_LOSS",None,None),
 ("J24","2026-06-23T10:25:04","SHORT",None,None,"VERIFIED_WIN",170,4132.02),
 ("J25","2026-06-23T13:55:42","SHORT",(4138,4155),4180,"VERIFIED_WIN",170,None),
 ("J26","2026-06-24T14:32:13","SHORT",(4030,4045),4130,"VERIFIED_WIN",650,4029.76),
 ("J27","2026-06-25T14:42:30","LONG",(4006,4016),3970,"VERIFIED_WIN",300,None),
 ("J28","2026-06-26T13:58:29","SHORT",(4078,4092),4120,"PARTIAL",100,None),
 ("J29","2026-06-26T14:12:55","SHORT",(4084,4094),4120,"VERIFIED_WIN",150,None),
 ("J30","2026-06-29T08:59:32","LONG",(4035,4045),4010,"PARTIAL",240,4027.37),
 ("S1","2026-06-30T14:25:23","SHORT",(4060,4075),4100,"VERIFIED_WIN",1000,None),
 ("S2","2026-07-07T11:29:34","SHORT",(4144,4154),4180,"VERIFIED_LOSS",None,None),
 ("S3","2026-07-08T12:14:29","SHORT",(4072,4083),4125,"VERIFIED_WIN",500,None),
 ("S4","2026-07-10T12:43:32","SHORT",(4102,4115),4152,"PARTIAL",200,None),
]

DET_LABEL = {"J01":"SHADOW_CANDIDATE_MEDIUM","J02":"SHADOW_CANDIDATE_MEDIUM","J03":"WATCH",
 "J04":"SHADOW_CANDIDATE_MEDIUM","J05":"SHADOW_CANDIDATE_MEDIUM","J06":"WATCH",
 "J07":"SHADOW_CANDIDATE_MEDIUM","J08":"WATCH","J09":"SHADOW_CANDIDATE_MEDIUM",
 "J10":"HUMAN_REVIEW_REQUIRED","J11":"HUMAN_REVIEW_REQUIRED","J12":"SHADOW_CANDIDATE_MEDIUM",
 "J13":"SHADOW_CANDIDATE_MEDIUM","J14":"WATCH","J15":"WATCH","J16":"REJECT","J17":"REJECT",
 "J18":"SHADOW_CANDIDATE_MEDIUM","J19":"WATCH","J20":"SHADOW_CANDIDATE_MEDIUM",
 "J21":"SHADOW_CANDIDATE_MEDIUM","J22":"SHADOW_CANDIDATE_MEDIUM","J23":"SHADOW_CANDIDATE_MEDIUM",
 "J24":"HUMAN_REVIEW_REQUIRED","J25":"SHADOW_CANDIDATE_MEDIUM","J26":"SHADOW_CANDIDATE_MEDIUM",
 "J27":"SHADOW_CANDIDATE_MEDIUM","J28":"SHADOW_CANDIDATE_MEDIUM","J29":"WATCH",
 "J30":"SHADOW_CANDIDATE_MEDIUM","S1":"SHADOW_CANDIDATE_MEDIUM","S2":"SHADOW_CANDIDATE_MEDIUM",
 "S3":"SHADOW_CANDIDATE_MEDIUM","S4":"SHADOW_CANDIDATE_MEDIUM"}


def simulate(sid, sig_s, d, zone, hsl, fill_model):
    sig = iso(sig_s)
    bars = B1 if sig >= CUT else B5
    short = d == "SHORT"
    seq = [b for b in bars if sig - 300 <= b[0] <= sig + 6 * 3600]
    if not seq:
        return None
    post_px = seq[0][4]
    if sid == "J24":
        fill, fillbar = 4128.38, seq[0]
    elif zone is None:
        fill, fillbar = post_px, seq[0]
    else:
        lo, hi = zone
        fb = next((b for b in seq if b[2] >= lo and b[3] <= hi), None)
        if fb is None:
            return {"status": "UNCLEAR", "note": "zone never touched"}
        if fill_model == "NEAR_EDGE":
            fill = lo if fb[1] < lo else (hi if fb[1] > hi else max(lo, min(hi, fb[4])))
        else:
            fill = (lo + hi) / 2
            fb2 = next((b for b in seq if b[3] <= fill <= b[2]), None)
            if fb2 is None:
                return {"status": "UNFILLED", "note": "mid never traded"}
            fb = fb2
        fillbar = fb
    run = [b for b in seq if b[0] >= fillbar[0]]
    mfe = max((fill - b[3]) if short else (b[2] - fill) for b in run)
    mae = max((b[2] - fill) if short else (fill - b[3]) for b in run)
    banked, state, tp1, tp2, pips, sl_eff = 0.0, "OPEN", False, False, None, "NONE"
    for b in run:
        hi_f = (fill - b[3]) if short else (b[2] - fill)
        sl_hit = hsl is not None and ((b[2] >= hsl) if short else (b[3] <= hsl))
        if state == "OPEN":
            if sl_hit and hi_f < 5.0:
                pips, state = -abs(hsl - fill) / 0.1, "STOPPED_FULL"
                break
            if hi_f >= 5.0:
                banked += 25.0; tp1 = True; state = "BE_ARMED"
                if hi_f >= 10.0:
                    banked += 25.0; tp2 = True
                continue
        elif state == "BE_ARMED":
            if not tp2 and hi_f >= 10.0:
                banked += 25.0; tp2 = True
            if (b[2] >= fill) if short else (b[3] <= fill):
                sl_eff, pips, state = f"SCRATCHED_{fmt(b[0])}", banked, "BE_STOPPED"
                break
    if state in ("OPEN", "BE_ARMED"):
        rem = (0.25 if tp2 else 0.5) if state == "BE_ARMED" else 1.0
        tail = ((fill - run[-1][4]) if short else (run[-1][4] - fill)) / 0.1
        pips = banked + rem * tail if state == "BE_ARMED" else tail
        sl_eff = "SURVIVED_TO_WINDOW_END"
    if state == "STOPPED_FULL":
        st = "FOLLOWER_LOSS"
    elif pips >= 40: st = "FOLLOWER_WIN"
    elif pips >= 20: st = "FOLLOWER_PARTIAL"
    elif pips > -20: st = "FOLLOWER_SCRATCH"
    else: st = "FOLLOWER_LOSS"
    return {"status": st, "fill": round(fill, 2), "post_px": post_px,
            "pips": round(pips, 1), "mfe": round(mfe / 0.1), "mae": round(mae / 0.1),
            "tp1": tp1, "tp2": tp2, "sl_eff": sl_eff}


rows = []
for sid, sig_s, d, zone, hsl, det, claim, ffill in S:
    near = simulate(sid, sig_s, d, zone, hsl, "NEAR_EDGE")
    mid = simulate(sid, sig_s, d, zone, hsl, "MID")
    r = {"setup_id": sid, "posted_time_utc": sig_s, "direction": d,
         "posted_zone": f"{zone[0]}-{zone[1]}" if zone else None,
         "hard_sl": hsl, "farouk_fill_if_known": ffill,
         "deterministic_outcome": det, "detector_label": DET_LABEL[sid],
         "headline_claim_pips": claim,
         "lane4_near_edge": near, "lane4_mid_sensitivity": mid}
    if near and near.get("fill") is not None:
        if claim and claim > 0:
            r["inflation_ratio_vs_near_mfe"] = round(claim / max(near["mfe"], 1), 2)
        if ffill:
            sgn = 1 if d == "SHORT" else -1
            r["farouk_fill_advantage_usd"] = round((ffill - near["fill"]) * sgn, 2)
    rows.append(r)

ok = [r for r in rows if r["lane4_near_edge"] and "pips" in r["lane4_near_edge"]]
vals = sorted(r["lane4_near_edge"]["pips"] for r in ok)
agg = {"setups_analysed": len(rows), "lane4_computable_near_edge": len(ok),
       "counts": {}, "mean_pips": round(sum(vals) / len(vals), 1),
       "median_pips": vals[len(vals) // 2], "total_pips": round(sum(vals), 1),
       "scratch_like_rate": None}
for stt in ("FOLLOWER_WIN", "FOLLOWER_PARTIAL", "FOLLOWER_SCRATCH", "FOLLOWER_LOSS"):
    agg["counts"][stt] = sum(1 for r in ok if r["lane4_near_edge"]["status"] == stt)
claims = [(r["setup_id"], r["headline_claim_pips"], r["lane4_near_edge"]["pips"])
          for r in ok if r.get("headline_claim_pips") and r["headline_claim_pips"] > 0]
agg["headline_vs_lane4"] = {"n": len(claims), "claimed_total": sum(c[1] for c in claims),
                             "follower_total": round(sum(c[2] for c in claims), 1),
                             "capture_ratio": round(sum(c[2] for c in claims) / sum(c[1] for c in claims), 3)}
agg["farouk_fill_advantage_usd"] = {r["setup_id"]: r["farouk_fill_advantage_usd"]
                                     for r in rows if "farouk_fill_advantage_usd" in r}

out = {"table_id": "follower_fill_expectancy_table_v0_1", "generated_on": "2026-07-11",
       "mode": "OBSERVATION_ONLY / REVIEW_ONLY",
       "lane4_playbook": "bank 50% at +50p & SL->entry; bank 25% at +100p; runner to BE-return/hard-SL/window-end (+6h). PRIMARY fill = NEAR-EDGE (limit at first-touched zone boundary — always fills when zone trades, at the worst zone price). Sensitivity = MID-ZONE (often never fills; unfilled = missed trade, not loss).",
       "setups": rows, "aggregate_lane4_near_edge": agg}
with open(BASE + r"\farouk_plus\follower_fill_expectancy_table_v0_1.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)

print(json.dumps(agg, indent=1))
print("\nper-setup (near-edge):")
for r in rows:
    n = r["lane4_near_edge"]
    if n and "pips" in n:
        print(f" {r['setup_id']:4s} {n['status']:17s} fill={n['fill']:<8} pips={n['pips']:>7} mfe={n['mfe']:>5} mae={n['mae']:>5} {n['sl_eff']}")
    else:
        print(f" {r['setup_id']:4s} {n}")
# J11 diagnostic
sig = iso("2026-06-11T13:58:19")
seq = [b for b in B5 if sig - 300 <= b[0] <= sig + 6 * 3600]
print(f"\nJ11 diag: fill(bar close)={seq[0][4]} window_max_high={max(b[2] for b in seq)} "
      f"window_min_low={min(b[3] for b in seq)} last={fmt(seq[-1][0])}")
