"""
Sprint Day 2 — deterministic XAUUSD outcome matcher (observation-only, offline).

Authority: this deterministic OHLC matching, not AI. No execution surface.
SELL semantics: entry zone touch = bar intersects [zone_lo, zone_hi] after signal time;
SL touch = bar.high >= SL; TP touch = bar.low <= TP. MFE/MAE from zone-top (best) and
zone-bottom (worst) reference entries. pip primary convention: 1 pip = $0.10 (alt $0.01 noted).
"""
import csv, json, sys, io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SRC = r"C:\Users\Marty\signal-terminal\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\price_data\XAUUSD_1M_PEPPERSTONE_2026-06-29_to_2026-07-10_FULL_EXPORT.csv"
OUT = r"C:\Users\Marty\signal-terminal\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\SPRINT_DAY2_XAU_OUTCOME_MATCHING_v1.json"

def iso(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()

def fmt(t):
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

bars = []
with open(SRC, newline="", encoding="utf-8-sig") as fh:
    for r in csv.DictReader(fh):
        bars.append((int(r["time"]), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])))
bars.sort()

SETUPS = [
    {
        "setup_id": "XAU-S1-20260630", "direction": "SELL",
        "signal_utc": "2026-06-30T14:25:23", "zone": (4060.0, 4075.0), "sl": 4100.0,
        "tp_levels": [],
        "window": ("2026-06-30T13:00", "2026-07-01T04:00"),
        "claims": [("60 pips tp1", "2026-06-30T14:30:07", 60),
                   ("100 pips", "2026-06-30T14:37:45", 100),
                   ("150 pips (close 0.5)", "2026-06-30T14:39:37", 150),
                   ("180 pips", "2026-06-30T14:53:59", 180),
                   ("200 pips (50% off)", "2026-06-30T14:58:54", 200),
                   ("1000+ pips close fully", "2026-07-01T02:35:07", 1000)],
        "claimed_result": "WIN_CLAIM",
    },
    {
        "setup_id": "XAU-S2-20260707", "direction": "SELL",
        "signal_utc": "2026-07-07T11:29:34", "zone": (4144.0, 4154.0), "sl": 4180.0,
        "tp_levels": [4135.0, 4130.0, 4120.0, 4115.0, 4110.0, 4105.0],
        "window": ("2026-07-07T10:00", "2026-07-07T16:00"),
        "claims": [("Trade failed", "2026-07-07T13:43:47", None),
                   ("stopped out by 0.60 cents", "2026-07-08T14:18:17", None)],
        "claimed_result": "LOSS_CLAIM",
    },
    {
        "setup_id": "XAU-S3-20260708", "direction": "SELL",
        "signal_utc": "2026-07-08T12:14:29", "zone": (4072.0, 4083.0), "sl": 4125.0,
        "tp_levels": [4020.0],
        "window": ("2026-07-08T11:00", "2026-07-08T16:30"),
        "claims": [("take tp1", "2026-07-08T13:01:59", None),
                   ("take 50% off", "2026-07-08T13:24:49", None),
                   ("200+ pips", "2026-07-08T14:16:20", 200),
                   ("close 90% leave 10% for 4020", "2026-07-08T14:40:01", None),
                   ("500 pips", "2026-07-08T14:46:13", 500),
                   ("full tp hit", "2026-07-08T15:32:31", None)],
        "claimed_result": "WIN_CLAIM",
    },
    {
        "setup_id": "XAU-S4-20260710", "direction": "SELL",
        "signal_utc": "2026-07-10T12:43:32", "zone": (4102.0, 4115.0), "sl": 4152.0,
        "tp_levels": [4077.0, 4055.0],
        "window": ("2026-07-10T11:30", "2026-07-10T22:00"),
        "claims": [("100 pips", "2026-07-10T13:25:16", 100),
                   ("200 pips", "2026-07-10T13:30:11", 200)],
        "claimed_result": "WIN_CLAIM_PARTIAL",
    },
]

results = []
for s in SETUPS:
    sig = iso(s["signal_utc"])
    w0, w1 = iso(s["window"][0]), iso(s["window"][1])
    win = [b for b in bars if w0 <= b[0] <= w1]
    zone_lo, zone_hi = s["zone"]

    sig_bar = max((b for b in win if b[0] <= sig), key=lambda b: b[0], default=None)
    post = [b for b in win if b[0] >= sig - 60]  # include signal bar

    # entry zone touch
    entry_bar = next((b for b in post if b[2] >= zone_lo and b[3] <= zone_hi), None)
    zone_top_fill_bar = next((b for b in post if b[2] >= zone_hi), None)  # best SELL fill
    r = {
        "setup_id": s["setup_id"],
        "signal_utc": fmt(sig),
        "signal_bar_close": sig_bar[4] if sig_bar else None,
        "bars_in_window": len(win),
        "entry_zone": f"{zone_lo}-{zone_hi}",
        "sl": s["sl"],
        "entry_zone_touched_utc": fmt(entry_bar[0]) if entry_bar else None,
        "zone_top_filled_utc": fmt(zone_top_fill_bar[0]) if zone_top_fill_bar else None,
    }

    if entry_bar is None:
        r.update({"status": "INSUFFICIENT_DATA", "reason": "entry zone never touched in window"})
        results.append(r)
        continue

    after = [b for b in win if b[0] >= entry_bar[0]]
    sl_bar = next((b for b in after if b[2] >= s["sl"]), None)
    r["sl_touched_utc"] = fmt(sl_bar[0]) if sl_bar else None
    r["max_high_after_entry"] = max(b[2] for b in after)
    r["min_low_after_entry"] = min(b[3] for b in after)
    r["sl_overshoot_usd"] = round(max(b[2] for b in after) - s["sl"], 2) if sl_bar else None

    tp_hits = []
    for tp in s["tp_levels"]:
        tb = next((b for b in after if b[3] <= tp), None)
        tp_hits.append({"level": tp, "touched_utc": fmt(tb[0]) if tb else None,
                        "before_sl": (tb is not None and (sl_bar is None or tb[0] < sl_bar[0]))})
    r["tp_touches"] = tp_hits

    # MFE / MAE from zone-top (best) and zone-bottom (worst) SELL entries
    for label, e in (("zone_top", zone_hi), ("zone_bottom", zone_lo)):
        mfe = round(e - min(b[3] for b in after), 2)
        mae = round(max(b[2] for b in after) - e, 2)
        r[f"mfe_usd_from_{label}"] = mfe
        r[f"mae_usd_from_{label}"] = mae
        r[f"mfe_pips01_from_{label}"] = round(mfe / 0.1)   # pip=$0.10
    # MFE up to SL touch (if SL hit, favourable move before stop)
    if sl_bar:
        pre_sl = [b for b in after if b[0] <= sl_bar[0]]
        r["mfe_usd_before_sl_from_zone_top"] = round(zone_hi - min(b[3] for b in pre_sl), 2)

    # claim-time snapshots
    snaps = []
    for label, cts, pips in s["claims"]:
        ct = iso(cts)
        cbar = max((b for b in win if b[0] <= ct), key=lambda b: b[0], default=None)
        if cbar is None:
            snaps.append({"claim": label, "at_utc": cts, "bar_close": None})
            continue
        min_low_so_far = min(b[3] for b in after if b[0] <= ct) if after and after[0][0] <= ct else None
        snap = {"claim": label, "at_utc": cts, "bar_close": cbar[4]}
        if min_low_so_far is not None:
            snap["implied_pips01_from_zone_top_best_so_far"] = round((zone_hi - min_low_so_far) / 0.1)
            snap["implied_pips01_from_zone_bottom_best_so_far"] = round((zone_lo - min_low_so_far) / 0.1)
        if pips:
            snap["claimed_pips"] = pips
        snaps.append(snap)
    r["claim_snapshots"] = snaps
    results.append(r)

with open(OUT, "w", encoding="utf-8") as fh:
    json.dump({"matcher": "day2 deterministic v1 (pip=$0.10 primary)",
               "source_csv": SRC.split("\\")[-1],
               "results": results}, fh, indent=2)

for r in results:
    print(json.dumps(r, indent=2))
