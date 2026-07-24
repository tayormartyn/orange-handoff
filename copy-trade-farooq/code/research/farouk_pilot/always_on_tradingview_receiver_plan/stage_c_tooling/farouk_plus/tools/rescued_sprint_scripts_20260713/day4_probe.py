"""Probe pre-entry price action for the three timing anomalies (J25, J28, J30)."""
import csv, sys, io
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
SRC = r"C:\Users\Marty\signal-terminal\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\price_data\XAUUSD_1M_PEPPERSTONE_2026-06-21_to_2026-07-10_FULL_EXPORT.csv"

def iso(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()

bars = []
with open(SRC, newline="", encoding="utf-8-sig") as fh:
    for r in csv.DictReader(fh):
        bars.append((int(r["time"]), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])))
bars.sort()

PROBES = [
    ("J25 signal->claim1", "2026-06-23T13:54", "2026-06-23T14:01"),
    ("J28 signal->claim1", "2026-06-26T13:57", "2026-06-26T14:05"),
    ("J30 signal->tp1claim", "2026-06-29T08:58", "2026-06-29T09:36"),
    ("J30 around 12:00-12:15", "2026-06-29T11:58", "2026-06-29T12:15"),
    ("J30 around BE-stop 14:00-14:20", "2026-06-29T13:59", "2026-06-29T14:20"),
]
for name, a, b in PROBES:
    ta, tb = iso(a), iso(b)
    print(f"--- {name} ---")
    for t, o, h, l, c in bars:
        if ta <= t <= tb:
            print(f"{datetime.fromtimestamp(t, tz=timezone.utc).strftime('%H:%M')} O{o} H{h} L{l} C{c}")
