# Jul-10 XAUUSD 1m OHLC — Import Instructions (for Martyn)

**The Jul-10 offline pipeline is BLOCKED at outcome matching: no Jul-10 OHLC is present.** The only file in
`price_data/` (`XAUUSD_1M_2026-07-08_2026-07-09_IMPORT_HERE.csv`) covers **2026-07-08T16:12Z →
2026-07-09T12:18Z** and does **not** reach Jul 10. Outcomes are **not guessed**. Observation-only.

## What is needed

A cleaned **XAUUSD · Pepperstone · 1-minute** OHLC export in **UTC**, covering at least:

- **2026-07-10 00:30Z → 2026-07-10 09:30Z** (a couple of hours of padding either side is ideal, e.g.
  2026-07-09 23:00Z → 2026-07-10 11:00Z), so the verified Jul-10 captures can be outcome-matched with full
  120-minute forward windows:
  - H2 CHoCH-down @ 01:39Z, 03:51Z, 07:09Z
  - H1 A+ @ 04:57Z

## Exact file to create

Save as: `stage_c_tooling/price_data/XAUUSD_1M_2026-07-10_IMPORT_HERE.csv`

**Header (must match exactly — same schema as the Jul 8–9 file):**

```
timestamp_utc,open,high,low,close,source,timeframe
```

- `timestamp_utc`: UTC. Either ISO-8601 (`2026-07-10T04:57:00Z`) or a Unix epoch — the matcher accepts both;
  **UTC is required** (the TradingView export uses Unix-epoch = true UTC even when the chart clock shows
  UTC+1).
- `open,high,low,close`: numeric price (USD/oz).
- `source`: e.g. `PEPPERSTONE_TradingView_export`.
- `timeframe`: `1m`.
- 1-minute candles, ascending time, no gaps across the window if possible.

## Do NOT

- Do not fabricate or interpolate candles. Missing coverage → the matcher returns `NO_DATA` (not estimates).
- No account/broker/personal info in the file.

## After you drop the file in

Tell me and I will resume the Jul-10 cycle: outcome-match the A+ and CHoCH-down captures, run the
methodology scorer and the Farouk Campaign State Machine v0.1 with resolved evidence, append any
outcome-matched candidates to the shadow observation journal, and populate review batch 002. Still
observation-only — no broker/QST/execution, no gate change.
