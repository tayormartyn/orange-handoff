"""
Step 6A — J24 deterministic rematch using the screenshot-recovered entry (observation-only).

Inputs: SELL fill 4132.02 (from MT5 widgets on msgs 45015/45017/45021; position existed by
10:20:43Z when msg 45014 was posted). No hard SL was ever posted; SL moved to entry at ~10:25Z
(msg 45015). Claims: 70 pips @10:43:25Z (widget 4124.99 = 70.3p), 100 pips tp2 @10:57:09Z,
170 pips @12:14:10Z (widget 4114.99 = 170.3p). 1m Pepperstone coverage exists for Jun-23.
Authority: this deterministic check. Append-only: Day-4/5 INSUFFICIENT records stay untouched;
this is a NEW revision-2 adjudication record.
"""
import csv, json, sys, io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BASE = r"C:\Users\Marty\signal-terminal\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling"
SRC = BASE + r"\price_data\XAUUSD_1M_PEPPERSTONE_2026-06-21_to_2026-07-10_FULL_EXPORT.csv"
OUT = BASE + r"\farouk_plus\j24_deterministic_rematch_v1.json"

def iso(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()

def fmt(t):
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

bars = []
with open(SRC, newline="", encoding="utf-8-sig") as fh:
    for r in csv.DictReader(fh):
        bars.append((int(r["time"]), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])))
bars.sort()

FILL = 4132.02
T_EVIDENT = iso("2026-06-23T10:20:43")     # position provably open by here
T_BE = iso("2026-06-23T10:25:04")          # SL moved to entry
W0, W1 = iso("2026-06-23T08:00:00"), iso("2026-06-23T13:55:00")   # to J25 signal
win = [b for b in bars if W0 <= b[0] <= W1]

# fill plausibility: bars whose range contains 4132.02 before 10:20:43
fill_bars = [b for b in win if b[0] <= T_EVIDENT and b[3] <= FILL <= b[2]]
fill_window = (fmt(fill_bars[0][0]), fmt(fill_bars[-1][0])) if fill_bars else None

after = [b for b in win if b[0] >= (fill_bars[0][0] if fill_bars else T_EVIDENT)]

CLAIMS = [("70 pips tp1 (msg 45017)", "2026-06-23T10:43:25", 4124.99, 70.3),
          ("100 pips tp2 (msg 45018)", "2026-06-23T10:57:09", 4132.02 - 10.0, 100.0),
          ("170 pips (msg 45021)", "2026-06-23T12:14:10", 4114.99, 170.3)]
snaps = []
for label, cts, level, pips in CLAIMS:
    ct = iso(cts)
    upto = [b for b in after if b[0] <= ct]
    touched = next((fmt(b[0]) for b in upto if b[3] <= level), None)
    min_low = min(b[3] for b in upto) if upto else None
    snaps.append({"claim": label, "at_utc": cts, "level_required": round(level, 2),
                  "level_touched_by_claim_time_utc": touched,
                  "min_low_by_claim_time": min_low,
                  "achieved_pips_from_fill": round((FILL - min_low) / 0.1, 1) if min_low else None,
                  "claimed_pips": pips,
                  "supported": bool(touched)})

mfe_low = min(b[3] for b in after)
mae_high = max(b[2] for b in after)
be_ret = next((b for b in after if b[0] > T_BE and b[2] >= FILL), None)

res = {
 "rematch_id": "j24_deterministic_rematch_v1", "generated_on": "2026-07-11",
 "setup_id": "XAU-J24-20260623", "revision": 2,
 "append_only_note": "Day-4 and Day-5 INSUFFICIENT_DATA records are preserved untouched; this revision-2 record supersedes them for reporting based on NEW screenshot-recovered evidence.",
 "entry_source": "MT5 position widgets (msgs 45015/45017/45021, sha256-addressed) — NOT a posted zone; fill_divergence noted (his 'sellzone 4140' vs actual fill 4132.02)",
 "direction": "SHORT", "fill": FILL, "hard_sl": "never posted (sellzone-note only); SL moved to entry ~10:25:04Z",
 "precision": "1m (Pepperstone export, Jun-23 fully covered)",
 "fill_plausibility": {"bars_containing_4132.02_before_10:20:43Z": len(fill_bars),
                        "first_last": fill_window},
 "claim_checks": snaps,
 "mfe_usd_from_fill": round(FILL - mfe_low, 2), "mfe_pips": round((FILL - mfe_low) / 0.1),
 "mae_usd_from_fill": round(mae_high - FILL, 2), "mae_pips": round((mae_high - FILL) / 0.1),
 "favourable_extreme": mfe_low, "adverse_extreme": mae_high,
 "be_stop_after_1025Z": {"price_returned_to_fill": bool(be_ret),
                          "first_return_utc": fmt(be_ret[0]) if be_ret else None},
 "window_utc": "2026-06-23 08:00 .. 13:55 (to the J25 signal)",
}
print(json.dumps(res, indent=1))

# status decision printed for the report; embed after review
with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(res, fh, indent=2)
print("written:", OUT)
