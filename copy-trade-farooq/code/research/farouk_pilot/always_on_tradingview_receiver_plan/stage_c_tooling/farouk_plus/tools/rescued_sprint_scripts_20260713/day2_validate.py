"""Day 2 step 1: validate the TradingView export and check per-window coverage. Read-only."""
import csv, sys, io
from datetime import datetime, timezone, timedelta

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SRC = r"C:\Users\Marty\Downloads\XAUUSD_1M_2026-06-30_1300_to_2026-07-01_0400_UTC.csv.csv"

def ts(s):
    return datetime.fromtimestamp(int(s), tz=timezone.utc)

rows = []
with open(SRC, newline="", encoding="utf-8-sig") as fh:
    rdr = csv.DictReader(fh)
    print("columns:", rdr.fieldnames)
    for r in rdr:
        rows.append((int(r["time"]), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])))

rows.sort()
print(f"rows={len(rows)}")
print(f"first={ts(rows[0][0])}  last={ts(rows[-1][0])}")

# timeframe check: modal delta
from collections import Counter
deltas = Counter(rows[i+1][0]-rows[i][0] for i in range(len(rows)-1))
print("top deltas (sec: count):", deltas.most_common(5))

# gaps > 5 min
gaps = [(rows[i][0], rows[i+1][0]) for i in range(len(rows)-1) if rows[i+1][0]-rows[i][0] > 300]
print(f"\ngaps >5min: {len(gaps)}")
for a, b in gaps:
    print(f"  {ts(a)} -> {ts(b)}  ({(b-a)/60:.0f} min)")

WINDOWS = [
    ("W1 S1", "2026-06-30T13:00", "2026-07-01T04:00"),
    ("W2 S2", "2026-07-07T10:00", "2026-07-07T16:00"),
    ("W3 S3", "2026-07-08T11:00", "2026-07-08T16:30"),
    ("W4 S4", "2026-07-10T11:30", "2026-07-10T22:00"),
]
print()
for name, a, b in WINDOWS:
    ta = datetime.fromisoformat(a).replace(tzinfo=timezone.utc).timestamp()
    tb = datetime.fromisoformat(b).replace(tzinfo=timezone.utc).timestamp()
    inw = [r for r in rows if ta <= r[0] <= tb]
    expect = int((tb - ta) / 60) + 1
    if inw:
        wgaps = sum(1 for i in range(len(inw)-1) if inw[i+1][0]-inw[i][0] > 300)
        print(f"{name}: bars={len(inw)}/{expect} ({100*len(inw)/expect:.1f}%) "
              f"first={ts(inw[0][0]).strftime('%m-%d %H:%M')} last={ts(inw[-1][0]).strftime('%m-%d %H:%M')} gaps>5m={wgaps}")
    else:
        print(f"{name}: NO BARS")
