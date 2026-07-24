"""
Sprint Day 5 fallback — deterministic June XAUUSD outcome matcher on 5m OHLC.
Same semantics as Day 2/4 (LONG+SHORT, pip=$0.10, achievable-fill), with 5m-precision guards:
any conclusion that depends on candle-internal ordering inside ONE 5m bar is flagged
intrabar_ambiguity rather than asserted. Authority: this deterministic matching.
"""
import csv, json, sys, io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BASE = r"C:\Users\Marty\signal-terminal\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling"
SRC = BASE + r"\price_data\XAUUSD_5M_PEPPERSTONE_2026-05-18_to_2026-07-10_FULL_EXPORT.csv"
OUT = BASE + r"\SPRINT_DAY5_JUNE_XAU_5M_FALLBACK_OUTCOME_MATCHING_v1.json"

def iso(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()

def fmt(t):
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

bars = []
with open(SRC, newline="", encoding="utf-8-sig") as fh:
    for r in csv.DictReader(fh):
        bars.append((int(r["time"]), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])))
bars.sort()

# (setup_id, dir, signal, zone(lo,hi)|None, sl|None, tps, window, claims[(label,ts,pips|None)], claimed, special)
SETUPS = [
 ("XAU-J01-20260602","LONG","2026-06-02T11:12:18",(4519.0,4529.0),4500.0,[4535.0,4540.0,4560.0],
  ("2026-06-02T10:30","2026-06-02T13:30"),
  [("close worst/take tps","2026-06-02T12:36:17",None),("close it will wait","2026-06-02T12:47:48",None)],
  "UNCLEAR_SMALL ('almost hit TP1, took partials')", None),
 ("XAU-J02-20260602","LONG","2026-06-02T13:02:03",(4505.0,4514.0),4480.0,[4520.0,4540.0,4570.0],
  ("2026-06-02T12:30","2026-06-02T15:30"),
  [("tp1 hit","2026-06-02T13:05:11",None),("sl->entry","2026-06-02T13:15:14",None)],
  "WIN_CLAIM_SMALL (TP1 then BE-stop)", None),
 ("XAU-J03-20260602","LONG","2026-06-02T15:58:50",(4490.0,4502.0),4468.0,[4508.0,4520.0,4540.0,4560.0],
  ("2026-06-02T15:30","2026-06-02T17:30"),
  [("cut -40..-50 pips","2026-06-02T16:26:02",None)],
  "LOSS_CLAIM (manual cut -40/50 pips)", "loss"),
 ("XAU-J04-20260603","SHORT","2026-06-03T11:48:33",(4463.0,4470.0),4487.0,[4430.0],
  ("2026-06-03T11:15","2026-06-03T14:15"),
  [("small tp","2026-06-03T12:02:11",None),("sl entry hit","2026-06-03T12:03:26",None),
   ("tp1 (re-entry)","2026-06-03T12:16:46",None),("close here (waterfall)","2026-06-03T13:47:18",None)],
  "WIN_CLAIM (waterfall, 3 executions)", None),
 ("XAU-J05-20260603","SHORT","2026-06-03T14:12:56",(4456.0,4462.0),4480.0,[4440.0,4410.0],
  ("2026-06-03T13:45","2026-06-03T16:30"),
  [("50 pips tp1","2026-06-03T14:16:01",50),("100 pips sl->entry","2026-06-03T14:27:31",100)],
  "WIN_CLAIM", None),
 ("XAU-J06-20260603","SHORT","2026-06-03T17:52:04",(4440.0,4446.0),4470.0,[4436.0,4429.0,4420.0,4400.0],
  ("2026-06-03T17:30","2026-06-03T20:30"),
  [("tp1 hit","2026-06-03T18:14:47",None)],
  "WIN_CLAIM_SMALL", None),
 ("XAU-J07-20260604","SHORT","2026-06-04T06:03:34",(4474.0,4485.0),4515.0,[4461.0,4445.0,4420.0],
  ("2026-06-04T05:30","2026-06-04T11:15"),
  [(">50 pips secure","2026-06-04T06:24:06",50),("take tp1","2026-06-04T07:14:41",None),
   ("tp1 hit","2026-06-04T07:50:37",None)],
  "WIN_CLAIM", None),
 ("XAU-J08-20260604","SHORT","2026-06-04T11:10:09",(4479.0,4488.0),4515.0,[4470.0,4445.0,4420.0],
  ("2026-06-04T10:45","2026-06-04T13:30"),
  [("50 pips small tp","2026-06-04T11:12:39",50),("close small loss","2026-06-04T12:19:55",None)],
  "LOSS_CLAIM (manual small loss; 'just missed our sl')", "loss"),
 ("XAU-J09-20260611","LONG","2026-06-11T07:58:30",(4090.0,4103.0),4080.0,[4190.0],
  ("2026-06-11T07:30","2026-06-11T09:00"),
  [("tp1 70 pips","2026-06-11T08:02:09",70),("sl entry hit","2026-06-11T08:22:49",None)],
  "WIN_CLAIM_SCRATCH (70p then BE)", None),
 ("XAU-J10-20260611","LONG","2026-06-11T08:22:49",None,4060.0,[],
  ("2026-06-11T08:20","2026-06-11T14:00"),
  [("(no outcome posted)","2026-06-11T13:58:19",None)],
  "UNCLEAR_IMPLIED_LOSS (layered re-entry, SL 4060)", "no_zone_sl_test"),
 ("XAU-J11-20260611","LONG","2026-06-11T13:58:19",None,4035.0,[],
  ("2026-06-11T13:30","2026-06-11T18:30"),
  [("500 pips","2026-06-11T16:16:07",500),("800 pips","2026-06-11T17:34:26",800)],
  "WIN_CLAIM (recovery, 800p)", "no_zone_proxy"),
 ("XAU-J12-20260615","SHORT","2026-06-15T09:40:01",(4339.0,4345.0),4360.0,[4334.0,4329.0,4319.0],
  ("2026-06-15T09:15","2026-06-15T11:30"),
  [("50 pips","2026-06-15T09:45:07",50),("BE-stop, up 50-60","2026-06-15T10:58:14",None)],
  "WIN_CLAIM_SCRATCH", None),
 ("XAU-J13-20260615","LONG","2026-06-15T14:04:10",(4350.0,4355.0),4330.0,[4364.0,4372.0,4390.0],
  ("2026-06-15T13:45","2026-06-15T14:45"),
  [("tp1 hit","2026-06-15T14:06:19",None),("BE-stop after 100p","2026-06-15T14:14:02",100)],
  "WIN_CLAIM (100p scalp)", None),
 ("XAU-J14-20260615","LONG","2026-06-15T14:35:08",(4348.0,4358.0),4330.0,[],
  ("2026-06-15T14:30","2026-06-15T15:15"),
  [("BE-stop after 100p again","2026-06-15T15:01:48",100)],
  "WIN_CLAIM (100p scalp)", None),
 ("XAU-J15-20260615","LONG","2026-06-15T15:06:22",(4346.0,4356.0),4330.0,[],
  ("2026-06-15T15:00","2026-06-15T15:45"),
  [("BE-stop ('4 scalps')","2026-06-15T15:34:03",None)],
  "WIN_CLAIM_SCRATCH", None),
 ("XAU-J16-20260615","LONG","2026-06-15T15:37:15",(4340.0,4350.0),4330.0,[4364.0,4370.0,4390.0],
  ("2026-06-15T15:30","2026-06-15T16:50"),
  [("BE-stop again","2026-06-15T16:42:35",None)],
  "SCRATCH_CLAIM", None),
 ("XAU-J17-20260615","LONG","2026-06-15T16:42:35",(4330.0,4339.0),4318.0,[],
  ("2026-06-15T16:40","2026-06-15T20:30"),
  [("SL WAS HIT ('6 trades, 1 loss')","2026-06-15T19:51:42",None)],
  "LOSS_CLAIM (full SL)", "loss"),
 ("XAU-J18-20260616","SHORT","2026-06-16T09:40:22",(4346.0,4356.0),4372.0,[],
  ("2026-06-16T09:15","2026-06-16T10:15"),
  [("tp1 / out 50-60p","2026-06-16T09:52:28",50)],
  "WIN_CLAIM (50-60p)", None),
 ("XAU-J19-20260616","SHORT","2026-06-16T10:10:08",(4346.0,4356.0),4375.0,[],
  ("2026-06-16T09:45","2026-06-16T13:15"),
  [("tp1","2026-06-16T10:35:52",None),("100 pips tp2","2026-06-16T11:18:08",100),
   ("BE-stop after 130p","2026-06-16T12:48:02",130)],
  "WIN_CLAIM (130p)", None),
 ("XAU-J20-20260617","LONG","2026-06-17T08:57:07",(4315.0,4323.0),4295.0,[4328.0,4332.0,4345.0],
  ("2026-06-17T08:30","2026-06-17T12:30"),
  [("100 pips tp2","2026-06-17T09:26:57",100),("tp1-2 hit","2026-06-17T09:29:33",None),
   ("BE-stop after tp2","2026-06-17T11:57:13",None)],
  "WIN_CLAIM", None),
 ("XAU-J21-20260618","SHORT","2026-06-18T10:18:39",(4269.0,4280.0),4300.0,[],
  ("2026-06-18T10:00","2026-06-18T12:00"),
  [("tp1","2026-06-18T10:23:15",None),("'just missed my sl'","2026-06-18T10:52:35",None),
   ("110 pips tp2","2026-06-18T10:53:20",110),("200 pips","2026-06-18T11:02:57",200)],
  "WIN_CLAIM (200p, near-SL drama)", None),
 ("XAU-J22-20260618","LONG","2026-06-18T11:12:51",(4231.0,4241.0),4218.0,[],
  ("2026-06-18T11:00","2026-06-18T12:15"),
  [("tp1","2026-06-18T11:14:32",None),("BE-stop on the BUY","2026-06-18T11:51:13",None)],
  "WIN_CLAIM_SCRATCH (SL posted 4318 = typo; testing 4218)", None),
 ("XAU-J23-20260619","LONG","2026-06-19T09:35:25",(4154.0,4164.0),4135.0,[],
  ("2026-06-19T09:00","2026-06-19T13:30"),
  [("take some profit","2026-06-19T12:10:58",None),("closed all, count as loss","2026-06-19T12:44:09",None)],
  "LOSS_CLAIM (manual, mixed closes)", "loss"),
]

results = []
for sid, direction, signal, zone, sl, tps, window, claims, claimed, special in SETUPS:
    sig = iso(signal)
    w0, w1 = iso(window[0]), iso(window[1])
    win = [b for b in bars if w0 <= b[0] <= w1]
    r = {"setup_id": sid, "direction": direction, "signal_utc": fmt(sig),
         "bars_in_window": len(win), "claimed": claimed, "precision": "5m_fallback",
         "intrabar_ambiguity": []}
    if not win:
        r.update({"status": "INSUFFICIENT_DATA", "reason": "no bars in window"})
        results.append(r)
        continue
    short = direction == "SHORT"
    post = [b for b in win if b[0] >= sig - 300]
    sig_bar = max((b for b in win if b[0] <= sig), key=lambda b: b[0], default=None)
    r["signal_bar_close"] = sig_bar[4] if sig_bar else None

    if zone is None:
        # special handling: J10 (SL-touch test only), J11 (proxy entry from signal close)
        if special == "no_zone_sl_test":
            sl_bar = next((b for b in post if b[3] <= sl), None)
            r["sl"] = sl
            r["sl_touched_utc"] = fmt(sl_bar[0]) if sl_bar else None
            r["min_low_after_signal"] = min(b[3] for b in post)
            r["note"] = "no numeric entry zone; testing only whether SL traded before the recovery trade"
        elif special == "no_zone_proxy":
            proxy = sig_bar[4]
            sl_bar = next((b for b in post if b[3] <= sl), None)
            best_fill = min(b[3] for b in post)  # best long fill after signal
            r["sl"] = sl
            r["proxy_entry_signal_close"] = proxy
            r["sl_touched_utc"] = fmt(sl_bar[0]) if sl_bar else None
            r["best_possible_fill_low"] = best_fill
            snaps = []
            for label, cts, pips in claims:
                ct = iso(cts)
                upto = [b for b in post if b[0] <= ct]
                hi = max(b[2] for b in upto)
                snaps.append({"claim": label, "at_utc": cts,
                              "max_pips_from_proxy": round((hi - proxy) / 0.1),
                              "max_pips_from_best_fill": round((hi - best_fill) / 0.1),
                              "claimed_pips": pips})
            r["claim_snapshots"] = snaps
        results.append(r)
        continue

    zone_lo, zone_hi = zone
    entry_bar = next((b for b in post if b[2] >= zone_lo and b[3] <= zone_hi), None)
    r["entry_zone"] = f"{zone_lo}-{zone_hi}"
    r["sl"] = sl
    r["entry_zone_touched_utc"] = fmt(entry_bar[0]) if entry_bar else None
    if entry_bar is None:
        r.update({"status": "INSUFFICIENT_DATA", "reason": "entry zone never touched in window"})
        results.append(r)
        continue
    after = [b for b in win if b[0] >= entry_bar[0]]
    if short:
        sl_bar = next((b for b in after if b[2] >= sl), None)
        fav, adv = min(b[3] for b in after), max(b[2] for b in after)
        mfe, mae = round(zone_hi - fav, 2), round(adv - zone_hi, 2)
        tp_hits = [{"level": tp, "touched_utc": next((fmt(b[0]) for b in after if b[3] <= tp), None)} for tp in tps]
    else:
        sl_bar = next((b for b in after if b[3] <= sl), None)
        fav, adv = max(b[2] for b in after), min(b[3] for b in after)
        mfe, mae = round(fav - zone_lo, 2), round(zone_lo - adv, 2)
        tp_hits = [{"level": tp, "touched_utc": next((fmt(b[0]) for b in after if b[2] >= tp), None)} for tp in tps]
    r["sl_touched_utc"] = fmt(sl_bar[0]) if sl_bar else None
    r["favourable_extreme"], r["adverse_extreme"] = fav, adv
    r["mfe_usd_from_best_zone_fill"], r["mae_usd_from_best_zone_fill"] = mfe, mae
    r["mfe_pips01"] = round(mfe / 0.1)
    r["tp_touches"] = tp_hits
    # intrabar ambiguity: TP and SL first-touched in the SAME 5m bar
    if sl_bar:
        for th in tp_hits:
            if th["touched_utc"] == fmt(sl_bar[0]):
                r["intrabar_ambiguity"].append(f"TP {th['level']} and SL first touch share one 5m bar")
        if entry_bar[0] == sl_bar[0]:
            r["intrabar_ambiguity"].append("entry touch and SL touch share one 5m bar")
    snaps = []
    for label, cts, pips in claims:
        ct = iso(cts)
        upto = [b for b in after if b[0] <= ct]
        if not upto:
            snaps.append({"claim": label, "at_utc": cts, "note": "before entry touch (5m)"})
            continue
        if short:
            best_ach = min(max(b[2] for b in upto), zone_hi)
            ach = round((best_ach - min(b[3] for b in upto)) / 0.1)
        else:
            best_ach = max(min(b[3] for b in upto), zone_lo)
            ach = round((max(b[2] for b in upto) - best_ach) / 0.1)
        snap = {"claim": label, "at_utc": cts, "max_achievable_pips01": ach}
        if pips:
            snap["claimed_pips"] = pips
            snap["supported"] = ach >= pips
        snaps.append(snap)
    r["claim_snapshots"] = snaps
    results.append(r)

with open(OUT, "w", encoding="utf-8") as fh:
    json.dump({"matcher": "day5 deterministic 5m fallback (pip=$0.10, achievable-fill, intrabar guards)",
               "source_csv": SRC.split("\\")[-1],
               "coverage_utc": "2026-05-18 03:30 .. 2026-07-10 20:50 (5m)",
               "results": results}, fh, indent=2)

for r in results:
    keep = {k: r[k] for k in ("setup_id","status","entry_zone_touched_utc","sl_touched_utc",
                              "mfe_pips01","mae_usd_from_best_zone_fill","intrabar_ambiguity") if k in r}
    print(json.dumps({**{"id": r["setup_id"]}, **keep,
                      "claims": r.get("claim_snapshots"), "tp": r.get("tp_touches")}, default=str))
print(f"\nwritten: {OUT}")
