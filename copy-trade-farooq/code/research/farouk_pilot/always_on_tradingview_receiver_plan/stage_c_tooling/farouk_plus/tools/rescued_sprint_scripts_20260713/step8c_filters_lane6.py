"""Step 8 final: filter-conditioned lane-4 expectancy + lane-6 pre-mark retrospective."""
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

tbl = json.load(open(BASE + r"\farouk_plus\follower_fill_expectancy_table_v0_1.json", encoding="utf-8"))
PIPS = {r["setup_id"]: r["lane4_near_edge"]["pips"] for r in tbl["setups"]
        if r["lane4_near_edge"] and "pips" in r["lane4_near_edge"]}

RE_ENTRY = {"J08", "J10", "J14", "J15", "J16", "J17", "J19", "J29"}       # attempt >= 2
ATT3 = {"J15", "J16", "J17", "J29"}                                        # attempt >= 3
LATE = {"J03", "J06", "J16", "J17"}                                        # entry >= 15:30Z

def filt(excl):
    keep = {k: v for k, v in PIPS.items() if k not in excl}
    tot = round(sum(keep.values()), 1)
    return {"kept": len(keep), "total_pips": tot, "mean_pips": round(tot / len(keep), 1),
            "removed": sorted(excl & set(PIPS)), "removed_pips": round(sum(PIPS[k] for k in excl & set(PIPS)), 1)}

filters = {
    "raw_all_34": {"kept": len(PIPS), "total_pips": round(sum(PIPS.values()), 1),
                   "mean_pips": round(sum(PIPS.values()) / len(PIPS), 1)},
    "R2_attempt_cap_le2": filt(ATT3),
    "R2b_first_attempt_only": filt(RE_ENTRY),
    "R4b_no_late_entries": filt(LATE),
    "R2b_plus_R4b": filt(RE_ENTRY | LATE),
}

# ---- Lane 6: the three genuine advance-level posts (leak-free by message timestamps) ----
def premark(pm_id, evid_ts, zone, direction, window_end, farouk_ref):
    t0 = iso(evid_ts)
    lo, hi = zone
    bars = B1 if t0 >= CUT else B5
    seq = [b for b in bars if t0 <= b[0] <= iso(window_end)]
    short = direction == "SHORT"
    fb = next((b for b in seq if b[2] >= lo and b[3] <= hi), None)
    rec = {"pre_mark_id": pm_id, "pre_mark_time_utc": evid_ts, "pre_mark_zone": f"{lo}-{hi}",
           "pre_mark_direction": direction, "mechanical_sl": (hi + 10) if short else (lo - 10),
           "window_end_utc": window_end, "farouk_reference": farouk_ref,
           "evidence_note": "message timestamp precedes pre-mark; zero lookahead"}
    if fb is None:
        rec.update({"label": "PRE_MARK_EXPIRED", "note": "zone never touched in window"})
        return rec
    fill = lo if fb[1] < lo else (hi if fb[1] > hi else max(lo, min(hi, fb[4])))
    run = [b for b in seq if b[0] >= fb[0]]
    sl = rec["mechanical_sl"]
    sl_bar = next((b for b in run if ((b[2] >= sl) if short else (b[3] <= sl))), None)
    if short:
        pre_sl = [b for b in run if sl_bar is None or b[0] <= sl_bar[0]]
        mfe = round((fill - min(b[3] for b in pre_sl)) / 0.1)
        mae = round((max(b[2] for b in run) - fill) / 0.1)
    else:
        pre_sl = [b for b in run if sl_bar is None or b[0] <= sl_bar[0]]
        mfe = round((max(b[2] for b in pre_sl) - fill) / 0.1)
        mae = round((fill - min(b[3] for b in run)) / 0.1)
    rec.update({"fill": round(fill, 2), "fill_time_utc": fmt(fb[0]),
                "sl_hit_utc": fmt(sl_bar[0]) if sl_bar else None,
                "hypothetical_mfe_pips_before_sl": mfe, "hypothetical_mae_pips": mae,
                "hypothetical_pips": round(-(abs(sl - fill)) / 0.1, 1) if sl_bar else None})
    return rec

lane6 = [
 premark("PM-45284", "2026-06-29T12:43:27", (4070, 4080), "SHORT", "2026-06-30T21:00:00",
         "S1 posted Jun-30 14:25 zone 4060-4075 (overlap 4070-4075 -> level match; mid-dist $7.5)"),
 premark("PM-45097", "2026-06-24T14:50:21", (4070, 4080), "SHORT", "2026-06-26T21:00:00",
         "J28 posted Jun-26 13:58 zone 4078-4092 (overlap 4078-4080 -> level match)"),
 premark("PM-44877", "2026-06-18T22:13:46", (4250, 4260), "SHORT", "2026-06-19T16:55:00",
         "no matching Farouk setup on Jun-19 (J23 was a BUY at 4154-4164)"),
]
for rec in lane6:
    if rec.get("sl_hit_utc"):
        rec["label"] = "PRE_MARK_MATCHED_FAROUK" if "level match" in rec["farouk_reference"] else "PRE_MARK_OBSERVED"
        rec["outcome_note"] = "mechanical pre-mark filled EARLY and was STOPPED by the pre-post adverse move"
    elif rec.get("fill") and not rec.get("sl_hit_utc"):
        rec["label"] = rec.get("label") or ("PRE_MARK_MATCHED_FAROUK" if "level match" in rec["farouk_reference"] else "PRE_MARK_OBSERVED")

agg6 = {"advance_level_posts_found_in_corpus": 3,
        "computed": [r for r in lane6],
        "insufficient_context": "remaining 31 setups: no leak-free pre-post level evidence exists in captured data (TV alert lane started Jul-7; June intraday structure = OHLC only)",
        }

out = {"retro_id": "orange_pre_mark_retrospective_v0_1", "generated_on": "2026-07-11",
       "mode": "OBSERVATION_ONLY / RESEARCH_ONLY",
       "anti_leakage": "pre-mark zones come verbatim from HIS OWN advance posts (timestamps precede everything computed); mechanical SL = far edge +/- $10 documented before computation; no post-dated evidence used",
       "lane6_records": lane6, "aggregate": agg6,
       "filters_lane4": filters}
with open(BASE + r"\farouk_plus\orange_pre_mark_retrospective_v0_1.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)

print(json.dumps(filters, indent=1))
print()
for r in lane6:
    print(json.dumps(r, indent=1))
