import csv, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

FILES = [
    r"C:\Users\Marty\signal-terminal\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\price_data\XAUUSD_1M_2026-07-08_2026-07-09_IMPORT_HERE.csv",
    r"C:\Users\Marty\signal-terminal\research\farouk_pilot\always_on_tradingview_receiver_plan\stage_c_tooling\price_data\XAUUSD_1M_2026-07-10_IMPORT_HERE.csv",
]
for f in FILES:
    with open(f, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    print(f.split("\\")[-1])
    print(f"  rows={len(rows)} header={rows[0] if rows else None}")
    if len(rows) > 2:
        print(f"  first={rows[1]}")
        print(f"  last ={rows[-1]}")
    print()
