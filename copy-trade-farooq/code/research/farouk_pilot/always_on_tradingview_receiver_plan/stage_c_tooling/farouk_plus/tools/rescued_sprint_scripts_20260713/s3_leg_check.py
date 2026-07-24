"""
Step 8D-A — deterministic S3 hold-best leg check (1m Pepperstone data; observation-only).

S3 = SHORT posted 2026-07-08T12:14:29Z, zone 4072-4083, hard SL 4125.
Instruction 45553 'close worst hold best sl entry' at 13:01:19Z.
Near-edge leg (Model B baseline): fill 4072 @12:14, BE-scratched 12:28 (+25 banked).
This script resolves the FAR-EDGE (hold-best) leg at 4083.
"""
import csv, json, sys, io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BASE = r"C:\Users\Marty\signal-terminal\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling"
SRC = BASE + r"\price_data\XAUUSD_1M_PEPPERSTONE_2026-06-21_to_2026-07-10_FULL_EXPORT.csv"

def iso(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()

def fmt(t):
    return datetime.fromtimestamp(t, tz=timezone.utc).strftime("%H:%M")

bars = []
with open(SRC, newline="", encoding="utf-8-sig") as fh:
    for r in csv.DictReader(fh):
        bars.append((int(r["time"]), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])))
bars.sort()

SIG = iso("2026-07-08T12:14:29")
INSTR = iso("2026-07-08T13:01:19")          # close worst / hold best / sl entry
FULL_TP_MSG = iso("2026-07-08T15:32:31")
FILL = 4083.0
SL_HARD = 4125.0
W1 = SIG + 6 * 3600
win = [b for b in bars if SIG - 60 <= b[0] <= W1]

fill_bar = next(b for b in win if b[2] >= FILL)
after = [b for b in win if b[0] > fill_bar[0]]           # strictly after the fill bar

# BE-return checks (high >= 4083) after the fill bar
be_returns = [b for b in after if b[2] >= FILL]
be_pre_instr = [b for b in be_returns if b[0] < INSTR]
be_post_instr = [b for b in be_returns if b[0] >= INSTR]

# hard SL / MFE / MAE from the far-edge fill
sl_bar = next((b for b in after if b[2] >= SL_HARD), None)
mfe = round((FILL - min(b[3] for b in after)) / 0.1)
mae = round((max(b[2] for b in after) - FILL) / 0.1)
tp1_bar = next((b for b in after if FILL - b[3] >= 5.0), None)     # +50p
tp2_bar = next((b for b in after if FILL - b[3] >= 10.0), None)    # +100p

# literal tranche playbook on this leg: 50% @+50p, 25% @+100p, runner 25%
banked = 0.0
if tp1_bar: banked += 25.0
if tp2_bar: banked += 25.0
runner_exit = None
if be_post_instr and tp1_bar and be_post_instr[0][0] > tp1_bar[0]:
    runner_exit = ("BE_RETURN", be_post_instr[0][0], 0.0)
elif be_post_instr and not tp1_bar:
    runner_exit = ("BE_RETURN_PRE_ARM", be_post_instr[0][0], 0.0)
if runner_exit is None:
    last = after[-1]
    runner_exit = ("WINDOW_END", last[0], 0.25 * (FILL - last[4]) / 0.1)
leg_pips = banked + runner_exit[2]

# reference exits at his claim moments (for context)
def px_at(ts):
    b = max((x for x in win if x[0] <= ts), default=None, key=lambda x: x[0])
    return b[4] if b else None

res = {
 "check_id": "s3_hold_best_leg_check_v0_1", "generated_on": "2026-07-11",
 "setup_id": "XAU-S3-20260708", "direction": "SHORT", "posted_zone": "4072-4083",
 "hard_sl": SL_HARD, "instruction_45553_utc": "2026-07-08T13:01:19Z",
 "far_edge_leg": {
   "fill_level": FILL,
   "fill_bar_utc": fmt(fill_bar[0]), "fill_bar_high": fill_bar[2],
   "fill_confirmed": True,
   "be_returns_after_fill_bar": len(be_returns),
   "first_be_return_pre_instruction": fmt(be_pre_instr[0][0]) if be_pre_instr else None,
   "first_be_return_post_instruction": fmt(be_post_instr[0][0]) if be_post_instr else None,
   "hard_sl_touched": bool(sl_bar),
   "mfe_pips": mfe, "mae_pips": mae,
   "tp1_plus50_reached_utc": fmt(tp1_bar[0]) if tp1_bar else None,
   "tp2_plus100_reached_utc": fmt(tp2_bar[0]) if tp2_bar else None,
   "runner_exit": {"reason": runner_exit[0], "utc": fmt(runner_exit[1]), "runner_pips_weighted": round(runner_exit[2], 1)},
   "leg_supported_pips_literal_playbook": round(leg_pips, 1),
 },
 "context_prices": {"at_full_tp_msg_15:32": px_at(FULL_TP_MSG), "window_end_close": after[-1][4],
                     "window_end_utc": fmt(after[-1][0])},
}
print(json.dumps(res, indent=1))
with open(BASE + r"\farouk_plus\s3_hold_best_leg_check_v0_1.json", "w", encoding="utf-8") as fh:
    json.dump(res, fh, indent=2)
print("written")
