"""
Sprint Day 4 — deterministic June XAUUSD outcome matcher (observation-only, offline).
Generalised LONG/SHORT semantics; pip = $0.10; achievable-fill logic as Day 2.
Authority: this deterministic matching. Covered days only (export starts 2026-06-21 22:01Z).
"""
import csv, json, sys, io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = r"C:\Users\Marty\signal-terminal\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling"
SRC = BASE + r"\price_data\XAUUSD_1M_PEPPERSTONE_2026-06-21_to_2026-07-10_FULL_EXPORT.csv"
OUT = BASE + r"\SPRINT_DAY4_JUNE_XAU_OUTCOME_MATCHING_v1.json"

def iso(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()

def fmt(t):
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

bars = []
with open(SRC, newline="", encoding="utf-8-sig") as fh:
    for r in csv.DictReader(fh):
        bars.append((int(r["time"]), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])))
bars.sort()
COVER_START = bars[0][0]

# the 7 setups on covered days (numeric params from the Day-3 ledger; J24 has no entry zone)
SETUPS = [
    {"setup_id": "XAU-J24-20260623", "direction": "SHORT", "signal_utc": "2026-06-23T10:20:43",
     "zone": None, "sl": None, "tps": [],
     "window": ("2026-06-23T08:00", "2026-06-23T13:30"),
     "claims": [("70 pips tp1", "2026-06-23T10:43:25", 70), ("100 pips tp2", "2026-06-23T10:57:09", 100),
                ("170 pips", "2026-06-23T12:14:10", 170)],
     "claimed": "WIN_CLAIM (entry msg missing; sellzone ~4140 per 45014)"},
    {"setup_id": "XAU-J25-20260623", "direction": "SHORT", "signal_utc": "2026-06-23T13:55:42",
     "zone": (4138.0, 4155.0), "sl": 4180.0, "tps": [4130.0],
     "window": ("2026-06-23T13:00", "2026-06-23T18:00"),
     "claims": [("50 pips", "2026-06-23T13:57:28", 50), ("100 pips", "2026-06-23T14:27:27", 100),
                ("130 pips", "2026-06-23T14:28:51", 130), ("tp3 170 pips", "2026-06-23T14:34:48", 170)],
     "claimed": "WIN_CLAIM"},
    {"setup_id": "XAU-J26-20260624", "direction": "SHORT", "signal_utc": "2026-06-24T14:32:13",
     "zone": (4030.0, 4045.0), "sl": 4130.0, "tps": [],
     "window": ("2026-06-24T13:30", "2026-06-24T19:30"),
     "claims": [("100 pips tp1", "2026-06-24T14:39:53", 100), ("120 pips", "2026-06-24T14:42:10", 120),
                ("200 pips tp4", "2026-06-24T14:47:14", 200), ("300 pips", "2026-06-24T15:13:09", 300),
                ("650 pips 90% off", "2026-06-24T18:04:15", 650)],
     "claimed": "WIN_CLAIM"},
    {"setup_id": "XAU-J27-20260625", "direction": "LONG", "signal_utc": "2026-06-25T14:42:30",
     "zone": (4006.0, 4016.0), "sl": 3970.0, "tps": [4022.0, 4027.0, 4040.0, 4065.0],
     "window": ("2026-06-25T13:40", "2026-06-25T18:00"),
     "claims": [("300 pips", "2026-06-25T15:24:17", 300)],
     "claimed": "WIN_CLAIM"},
    {"setup_id": "XAU-J28-20260626", "direction": "SHORT", "signal_utc": "2026-06-26T13:58:29",
     "zone": (4078.0, 4092.0), "sl": 4120.0, "tps": [],
     "window": ("2026-06-26T13:00", "2026-06-26T16:00"),
     "claims": [("100 pips sl-to-entry", "2026-06-26T14:01:12", 100)],
     "claimed": "WIN_CLAIM_SCRATCH (then 'SL got hit again' = BE stops)"},
    {"setup_id": "XAU-J29-20260626", "direction": "SHORT", "signal_utc": "2026-06-26T14:12:55",
     "zone": (4084.0, 4094.0), "sl": 4120.0, "tps": [],
     "window": ("2026-06-26T13:45", "2026-06-26T17:00"),
     "claims": [("90 pips", "2026-06-26T14:31:55", 90), ("100+ pips", "2026-06-26T14:35:17", 100),
                ("150 pips", "2026-06-26T14:38:44", 150)],
     "claimed": "WIN_CLAIM"},
    {"setup_id": "XAU-J30-20260629", "direction": "LONG", "signal_utc": "2026-06-29T08:59:32",
     "zone": (4035.0, 4045.0), "sl": 4010.0, "tps": [4050.0, 4055.0, 4062.0, 4080.0, 4090.0],
     "window": ("2026-06-29T08:00", "2026-06-29T15:00"),
     "claims": [("tp1 hit", "2026-06-29T09:04:34", None), ("170 pips 50% off", "2026-06-29T12:03:34", 170),
                ("200 pips", "2026-06-29T12:04:28", 200), ("240 pips", "2026-06-29T12:12:08", 240)],
     "claimed": "WIN_CLAIM"},
]

UNCOVERED = ["XAU-J01-20260602","XAU-J02-20260602","XAU-J03-20260602","XAU-J04-20260603",
             "XAU-J05-20260603","XAU-J06-20260603","XAU-J07-20260604","XAU-J08-20260604",
             "XAU-J09-20260611","XAU-J10-20260611","XAU-J11-20260611","XAU-J12-20260615",
             "XAU-J13-20260615","XAU-J14-20260615","XAU-J15-20260615","XAU-J16-20260615",
             "XAU-J17-20260615","XAU-J18-20260616","XAU-J19-20260616","XAU-J20-20260617",
             "XAU-J21-20260618","XAU-J22-20260618","XAU-J23-20260619"]

results = []
for s in SETUPS:
    sig = iso(s["signal_utc"])
    w0, w1 = iso(s["window"][0]), iso(s["window"][1])
    win = [b for b in bars if w0 <= b[0] <= w1]
    r = {"setup_id": s["setup_id"], "direction": s["direction"], "signal_utc": fmt(sig),
         "bars_in_window": len(win), "claimed": s["claimed"]}
    if s["zone"] is None:
        r.update({"status": "INSUFFICIENT_DATA",
                  "reason": "entry message not captured — no numeric zone/SL to test (OHLC present)"})
        # still record MFE potential around the claim times from the referenced sellzone 4140
        results.append(r)
        continue
    if not win:
        r.update({"status": "INSUFFICIENT_DATA", "reason": "no OHLC bars in window"})
        results.append(r)
        continue

    zone_lo, zone_hi = s["zone"]
    short = s["direction"] == "SHORT"
    best_fill_bound = zone_hi if short else zone_lo   # best fill: sell high / buy low
    post = [b for b in win if b[0] >= sig - 60]
    entry_bar = next((b for b in post if b[2] >= zone_lo and b[3] <= zone_hi), None)
    r["entry_zone"] = f"{zone_lo}-{zone_hi}"
    r["sl"] = s["sl"]
    r["entry_zone_touched_utc"] = fmt(entry_bar[0]) if entry_bar else None
    if entry_bar is None:
        r.update({"status": "INSUFFICIENT_DATA", "reason": "entry zone never touched in window"})
        results.append(r)
        continue

    after = [b for b in win if b[0] >= entry_bar[0]]
    if short:
        sl_bar = next((b for b in after if b[2] >= s["sl"]), None)
        fav_extreme = min(b[3] for b in after)
        adv_extreme = max(b[2] for b in after)
        mfe = round(best_fill_bound - fav_extreme, 2)
        mae = round(adv_extreme - best_fill_bound, 2)
        tp_hits = [{"level": tp, "touched_utc": next((fmt(b[0]) for b in after if b[3] <= tp), None)}
                   for tp in s["tps"]]
    else:
        sl_bar = next((b for b in after if b[3] <= s["sl"]), None)
        fav_extreme = max(b[2] for b in after)
        adv_extreme = min(b[3] for b in after)
        mfe = round(fav_extreme - best_fill_bound, 2)
        mae = round(best_fill_bound - adv_extreme, 2)
        tp_hits = [{"level": tp, "touched_utc": next((fmt(b[0]) for b in after if b[2] >= tp), None)}
                   for tp in s["tps"]]
    r["sl_touched_utc"] = fmt(sl_bar[0]) if sl_bar else None
    r["favourable_extreme"] = fav_extreme
    r["adverse_extreme"] = adv_extreme
    r["mfe_usd_from_best_zone_fill"] = mfe
    r["mae_usd_from_best_zone_fill"] = mae
    r["mfe_pips01"] = round(mfe / 0.1)
    r["tp_touches"] = tp_hits

    snaps = []
    for label, cts, pips in s["claims"]:
        ct = iso(cts)
        upto = [b for b in after if b[0] <= ct]
        if not upto:
            snaps.append({"claim": label, "at_utc": cts, "note": "before entry touch"})
            continue
        if short:
            best_ach = min(max(b[2] for b in upto), zone_hi)
            best_so_far = min(b[3] for b in upto)
            ach = round((best_ach - best_so_far) / 0.1)
        else:
            best_ach = max(min(b[3] for b in upto), zone_lo)
            best_so_far = max(b[2] for b in upto)
            ach = round((best_so_far - best_ach) / 0.1)
        snap = {"claim": label, "at_utc": cts, "max_achievable_pips01": ach}
        if pips:
            snap["claimed_pips"] = pips
            snap["supported"] = ach >= pips
        snaps.append(snap)
    r["claim_snapshots"] = snaps
    results.append(r)

for sid in UNCOVERED:
    results.append({"setup_id": sid, "status": "INSUFFICIENT_DATA",
                    "reason": "no OHLC coverage — export begins 2026-06-21 22:01Z"})

with open(OUT, "w", encoding="utf-8") as fh:
    json.dump({"matcher": "day4 deterministic v1 (pip=$0.10, achievable-fill, LONG+SHORT)",
               "source_csv": SRC.split("\\")[-1],
               "coverage_utc": "2026-06-21 22:01 .. 2026-07-10 20:54",
               "results": results}, fh, indent=2)

for r in results[:7]:
    print(json.dumps(r, indent=1))
print(f"\ntotal records={len(results)} written: {OUT}")
