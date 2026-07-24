"""Day 4 step 1: validate the June export, check coverage on the 14 active days."""
import csv, sys, io
from datetime import datetime, timezone
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
SRC = r"C:\Users\Marty\Downloads\XAUUSD_1M_2026-06-01_to_2026-06-15.csv.csv"

def ts(s):
    return datetime.fromtimestamp(int(s), tz=timezone.utc)

rows = []
with open(SRC, newline="", encoding="utf-8-sig") as fh:
    rdr = csv.DictReader(fh)
    print("columns:", rdr.fieldnames)
    for r in rdr:
        rows.append((int(r["time"]), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"])))
rows.sort()
print(f"rows={len(rows)} first={ts(rows[0][0])} last={ts(rows[-1][0])}")

deltas = Counter(rows[i+1][0]-rows[i][0] for i in range(len(rows)-1))
print("top deltas:", deltas.most_common(4))

# per active day coverage (UTC day -> bar count + first/last)
ACTIVE = ["2026-06-02","2026-06-03","2026-06-04","2026-06-11","2026-06-15","2026-06-16",
          "2026-06-17","2026-06-18","2026-06-19","2026-06-23","2026-06-24","2026-06-25",
          "2026-06-26","2026-06-29"]
byday = {}
for t, *_ in rows:
    d = ts(t).strftime("%Y-%m-%d")
    byday.setdefault(d, []).append(t)
for d in ACTIVE:
    v = byday.get(d)
    if v:
        print(f"{d}: bars={len(v)} {ts(min(v)).strftime('%H:%M')}-{ts(max(v)).strftime('%H:%M')}")
    else:
        print(f"{d}: NO BARS")
