"""
Step 8 — Lane-4 follower expectancy table (34 setups) + Lane-6 pre-mark retrospective.

Lane-4 sim (his own stated playbook, applied literally from follower fills):
  fill = posted-zone MEDIAN (lane 2) if zone posted, else first bar close at/after post (lane 3);
  full loss if hard SL trades before +50p; at +50p bank 50% and move SL to fill;
  at +100p bank a further 25%; runner exits at BE-return / hard SL / window end (+6h).
Deterministic OHLC only (1m where covered, else 5m). Observation-only; no execution surface.
"""
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

# id, signal, dir, zone|None, hard_sl|None, outcome, det_label, headline_claim_pips|None, farouk_fill|None
S = [
 ("J01","2026-06-02T11:12:18","LONG",(4519,4529),4500,"PARTIAL","SHADOW_CANDIDATE_MEDIUM",None,None),
 ("J02","2026-06-02T13:02:03","LONG",(4505,4514),4480,"VERIFIED_WIN","SHADOW_CANDIDATE_MEDIUM",None,None),
 ("J03","2026-06-02T15:58:50","LONG",(4490,4502),4468,"PARTIAL_LOSS","WATCH",-45,None),
 ("J04","2026-06-03T11:48:33","SHORT",(4463,4470),4487,"VERIFIED_WIN","SHADOW_CANDIDATE_MEDIUM",None,None),
 ("J05","2026-06-03T14:12:56","SHORT",(4456,4462),4480,"VERIFIED_WIN","SHADOW_CANDIDATE_MEDIUM",100,None),
 ("J06","2026-06-03T17:52:04","SHORT",(4440,4446),4470,"VERIFIED_WIN","WATCH",None,None),
 ("J07","2026-06-04T06:03:34","SHORT",(4474,4485),4515,"VERIFIED_WIN","SHADOW_CANDIDATE_MEDIUM",None,None),
 ("J08","2026-06-04T11:10:09","SHORT",(4479,4488),4515,"PARTIAL_LOSS","WATCH",-50,None),
 ("J09","2026-06-11T07:58:30","LONG",(4090,4103),4080,"VERIFIED_WIN","SHADOW_CANDIDATE_MEDIUM",70,4105.40),
 ("J10","2026-06-11T08:22:49","LONG",None,4060,"VERIFIED_LOSS","HUMAN_REVIEW_REQUIRED",None,None),
 ("J11","2026-06-11T13:58:19","LONG",None,4035,"PARTIAL","HUMAN_REVIEW_REQUIRED",800,4056.64),
 ("J12","2026-06-15T09:40:01","SHORT",(4339,4345),4360,"VERIFIED_WIN","SHADOW_CANDIDATE_MEDIUM",50,None),
 ("J13","2026-06-15T14:04:10","LONG",(4350,4355),4330,"VERIFIED_WIN","SHADOW_CANDIDATE_MEDIUM",100,4357.05),
 ("J14","2026-06-15T14:35:08","LONG",(4348,4358),4330,"VERIFIED_WIN","WATCH",100,None),
 ("J15","2026-06-15T15:06:22","LONG",(4346,4356),4330,"PARTIAL","WATCH",None,None),
 ("J16","2026-06-15T15:37:15","LONG",(4340,4350),4330,"PARTIAL","REJECT",None,None),
 ("J17","2026-06-15T16:42:35","LONG",(4330,4339),4318,"VERIFIED_LOSS","REJECT",None,None),
 ("J18","2026-06-16T09:40:22","SHORT",(4346,4356),4372,"VERIFIED_WIN","SHADOW_CANDIDATE_MEDIUM",50,None),
 ("J19","2026-06-16T10:10:08","SHORT",(4346,4356),4375,"VERIFIED_WIN","WATCH",130,None),
 ("J20","2026-06-17T08:57:07","LONG",(4315,4323),4295,"VERIFIED_WIN","SHADOW_CANDIDATE_MEDIUM",100,None),
 ("J21","2026-06-18T10:18:39","SHORT",(4269,4280),4300,"VERIFIED_WIN","SHADOW_CANDIDATE_MEDIUM",200,4270.91),
 ("J22","2026-06-18T11:12:51","LONG",(4231,4241),4218,"VERIFIED_WIN","SHADOW_CANDIDATE_MEDIUM",None,None),
 ("J23","2026-06-19T09:35:25","LONG",(4154,4164),4135,"PARTIAL_LOSS","SHADOW_CANDIDATE_MEDIUM",None,None),
 ("J24","2026-06-23T10:25:04","SHORT",None,None,"VERIFIED_WIN","HUMAN_REVIEW_REQUIRED",170,4132.02),
 ("J25","2026-06-23T13:55:42","SHORT",(4138,4155),4180,"VERIFIED_WIN","SHADOW_CANDIDATE_MEDIUM",170,None),
 ("J26","2026-06-24T14:32:13","SHORT",(4030,4045),4130,"VERIFIED_WIN","SHADOW_CANDIDATE_MEDIUM",650,4029.76),
 ("J27","2026-06-25T14:42:30","LONG",(4006,4016),3970,"VERIFIED_WIN","SHADOW_CANDIDATE_MEDIUM",300,None),
 ("J28","2026-06-26T13:58:29","SHORT",(4078,4092),4120,"PARTIAL","SHADOW_CANDIDATE_MEDIUM",100,None),
 ("J29","2026-06-26T14:12:55","SHORT",(4084,4094),4120,"VERIFIED_WIN","WATCH",150,None),
 ("J30","2026-06-29T08:59:32","LONG",(4035,4045),4010,"PARTIAL","SHADOW_CANDIDATE_MEDIUM",240,4027.37),
 ("S1","2026-06-30T14:25:23","SHORT",(4060,4075),4100,"VERIFIED_WIN","SHADOW_CANDIDATE_MEDIUM",1000,None),
 ("S2","2026-07-07T11:29:34","SHORT",(4144,4154),4180,"VERIFIED_LOSS","SHADOW_CANDIDATE_MEDIUM",None,None),
 ("S3","2026-07-08T12:14:29","SHORT",(4072,4083),4125,"VERIFIED_WIN","SHADOW_CANDIDATE_MEDIUM",500,None),
 ("S4","2026-07-10T12:43:32","SHORT",(4102,4115),4152,"PARTIAL","SHADOW_CANDIDATE_MEDIUM",200,None),
]

rows = []
for sid, sig_s, d, zone, hsl, det, label, claim, ffill in S:
    sig = iso(sig_s)
    bars = B1 if sig >= CUT else B5
    prec = "1m" if bars is B1 else "5m"
    short = d == "SHORT"
    seq = [b for b in bars if sig - 60 <= b[0] <= sig + 6 * 3600]
    r = {"setup_id": sid, "posted_time_utc": sig_s, "direction": d,
         "posted_zone": f"{zone[0]}-{zone[1]}" if zone else None,
         "farouk_fill_if_known": ffill, "hard_sl": hsl,
         "deterministic_outcome": det, "detector_label": label,
         "headline_claim_pips": claim, "precision": prec}
    if not seq:
        r.update({"follower_outcome_status": "UNCLEAR", "note": "no bars"})
        rows.append(r)
        continue
    post_px = seq[0][4]
    r["post_time_market_price"] = post_px
    if sid == "J24":
        fill = 4128.38   # widget price at the 10:25Z moment (earliest follower-visible)
    elif zone:
        fill = (zone[0] + zone[1]) / 2
    else:
        fill = post_px
    r["follower_fill_used"] = round(fill, 2)
    r["fill_lane"] = "lane2_zone_median" if zone else "lane3_post_time"

    # wait for fill: zone median must trade (bar range contains fill); lane3 fills immediately
    if zone:
        fb = next((b for b in seq if b[3] <= fill <= b[2]), None)
        if fb is None:
            r.update({"follower_outcome_status": "UNCLEAR", "note": "zone median never traded in window"})
            rows.append(r)
            continue
        run = [b for b in seq if b[0] >= fb[0]]
    else:
        run = seq
    sgn = -1 if short else 1
    fav = lambda b: sgn * ((b[3] if short else b[2]) - fill)   # most favourable in bar, signed +
    adv = lambda b: sgn * ((b[2] if short else b[3]) - fill)   # most adverse (negative)
    mfe = max(-fav(b) * -1 for b in run)  # = max favourable
    mfe = max((fill - b[3]) if short else (b[2] - fill) for b in run)
    mae = max((b[2] - fill) if short else (fill - b[3]) for b in run)
    r["max_follower_mfe_pips"] = round(mfe / 0.1)
    r["max_follower_mae_pips"] = round(mae / 0.1)

    banked = 0.0
    state = "OPEN"
    tp1 = tp2 = False
    sl_effect = "NONE"
    pips = None
    for b in run:
        hi_f = (fill - b[3]) if short else (b[2] - fill)      # favourable extreme this bar
        hi_a = (b[2] - fill) if short else (fill - b[3])      # adverse extreme this bar
        sl_hit = hsl is not None and ((b[2] >= hsl) if short else (b[3] <= hsl))
        if state == "OPEN":
            if sl_hit and hi_f < 5.0:
                pips = -abs(hsl - fill) / 0.1
                state = "STOPPED_FULL"
                break
            if hi_f >= 5.0:
                banked += 0.5 * 50
                tp1 = True
                state = "BE_ARMED"
                if hi_f >= 10.0:
                    banked += 0.25 * 100
                    tp2 = True
                # BE-return same bar? conservative: if adverse also >= 0 after arming -> cannot order intrabar
                continue
        elif state == "BE_ARMED":
            if not tp2 and hi_f >= 10.0:
                banked += 0.25 * 100
                tp2 = True
            be_ret = (b[2] >= fill) if short else (b[3] <= fill)
            if be_ret:
                sl_effect = f"SCRATCHED_AT_{fmt(b[0])}"
                pips = banked
                state = "BE_STOPPED"
                break
    if state == "OPEN":
        pips = ((fill - run[-1][4]) if short else (run[-1][4] - fill)) / 0.1
        sl_effect = "SURVIVED_TO_WINDOW_END"
    elif state == "BE_ARMED":
        rem = 0.25 if tp2 else 0.5
        pips = banked + rem * (((fill - run[-1][4]) if short else (run[-1][4] - fill)) / 0.1)
        sl_effect = "SURVIVED_TO_WINDOW_END"
    r["tp1_reachable_50p"] = tp1
    r["tp2_reachable_100p"] = tp2
    r["sl_to_entry_effect"] = sl_effect
    r["follower_pips_lane4"] = round(pips, 1)
    if state == "STOPPED_FULL":
        st = "FOLLOWER_LOSS"
    elif pips >= 40:
        st = "FOLLOWER_WIN"
    elif pips >= 20:
        st = "FOLLOWER_PARTIAL"
    elif pips > -20:
        st = "FOLLOWER_SCRATCH"
    else:
        st = "FOLLOWER_LOSS"
    r["follower_outcome_status"] = st
    if claim:
        r["inflation_ratio_vs_lane4_mfe"] = round(abs(claim) / max(r["max_follower_mfe_pips"], 1), 2)
    if ffill:
        r["divergence_fill_vs_follower_usd"] = round((ffill - fill) * (1 if short else -1), 2)
    rows.append(r)

ok = [r for r in rows if "follower_pips_lane4" in r]
agg = {"setups_analysed": len(rows), "lane4_computable": len(ok),
       "unavailable_or_unclear": len(rows) - len(ok)}
for st in ("FOLLOWER_WIN", "FOLLOWER_PARTIAL", "FOLLOWER_SCRATCH", "FOLLOWER_LOSS"):
    agg[st] = sum(1 for r in ok if r["follower_outcome_status"] == st)
vals = sorted(r["follower_pips_lane4"] for r in ok)
agg["mean_follower_pips"] = round(sum(vals) / len(vals), 1)
agg["median_follower_pips"] = vals[len(vals) // 2]
agg["total_follower_pips"] = round(sum(vals), 1)
claims = [(r["setup_id"], abs(r["headline_claim_pips"]), r["follower_pips_lane4"])
          for r in ok if r.get("headline_claim_pips") and r["headline_claim_pips"] > 0]
agg["headline_vs_lane4"] = {"n": len(claims),
    "total_claimed": sum(c[1] for c in claims), "total_follower": round(sum(c[2] for c in claims), 1)}
divs = [(r["setup_id"], r["divergence_fill_vs_follower_usd"]) for r in ok if "divergence_fill_vs_follower_usd" in r]
agg["farouk_fill_divergences_usd"] = divs

out = {"table_id": "follower_fill_expectancy_table_v0_1", "generated_on": "2026-07-11",
       "mode": "OBSERVATION_ONLY / REVIEW_ONLY",
       "lane4_playbook": "bank 50% at +50p & SL->entry; bank 25% at +100p; runner to BE-return/hard-SL/window-end (+6h); zone-median fill (lane2) else post-time fill (lane3); his own stated rules applied literally",
       "setups": rows, "aggregate_lane4": agg}
with open(BASE + r"\farouk_plus\follower_fill_expectancy_table_v0_1.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)

print(json.dumps(agg, indent=1))
print("\nper-setup lane4:")
for r in rows:
    print(f" {r['setup_id']:4s} {r.get('follower_outcome_status','-'):17s} pips={r.get('follower_pips_lane4','-'):>7} "
          f"mfe={r.get('max_follower_mfe_pips','-'):>5} mae={r.get('max_follower_mae_pips','-'):>5} "
          f"sl_eff={r.get('sl_to_entry_effect','-')} det={r['deterministic_outcome']}")
