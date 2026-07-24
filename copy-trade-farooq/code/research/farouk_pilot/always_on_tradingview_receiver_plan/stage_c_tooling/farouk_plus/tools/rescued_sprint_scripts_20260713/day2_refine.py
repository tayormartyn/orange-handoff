"""Refinement: achievable best SELL fill (max high) from entry-touch up to each claim time."""
import csv, sys, io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
SRC = r"C:\Users\Marty\signal-terminal\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\price_data\XAUUSD_1M_PEPPERSTONE_2026-06-29_to_2026-07-10_FULL_EXPORT.csv"

def iso(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()

bars = []
with open(SRC, newline="", encoding="utf-8-sig") as fh:
    for r in csv.DictReader(fh):
        bars.append((int(r["time"]), float(r["high"]), float(r["low"])))
bars.sort()

CASES = [
    ("S1", "2026-06-30T14:25:23", 4075.0, [
        ("60p @14:30", "2026-06-30T14:30:07", 60),
        ("100p @14:37", "2026-06-30T14:37:45", 100),
        ("150p @14:39", "2026-06-30T14:39:37", 150),
        ("180p @14:53", "2026-06-30T14:53:59", 180),
        ("200p @14:58", "2026-06-30T14:58:54", 200),
        ("1000p @07-01 02:35", "2026-07-01T02:35:07", 1000)]),
    ("S3", "2026-07-08T12:14:29", 4083.0, [
        ("200p @14:16", "2026-07-08T14:16:20", 200),
        ("500p @14:46", "2026-07-08T14:46:13", 500),
        ("full tp @15:32", "2026-07-08T15:32:31", None)]),
    ("S4", "2026-07-10T12:43:32", 4115.0, [
        ("100p @13:25", "2026-07-10T13:25:16", 100),
        ("200p @13:30", "2026-07-10T13:30:11", 200)]),
]

for name, sig, zone_hi, claims in CASES:
    t0 = iso(sig)
    seq = [b for b in bars if b[0] >= t0 - 60]
    for label, cts, claimed in claims:
        ct = iso(cts)
        upto = [b for b in seq if b[0] <= ct]
        if not upto:
            continue
        best_fill = min(max(b[1] for b in upto), zone_hi)  # capped at zone top
        min_low = min(b[2] for b in upto)
        pips = round((best_fill - min_low) / 0.1)
        ok = "SUPPORTED" if claimed is None or pips >= claimed else f"SHORT by {claimed - pips}p"
        print(f"{name} {label}: best_achievable_fill={best_fill:.2f} min_low_so_far={min_low:.2f} "
              f"-> max {pips}p (claimed {claimed}) [{ok}]")
    print()
