# XAUUSD OHLC Import Schema v0.1

Schema for the price CSV the offline outcome matcher reads. **Reference/research data only —
this is not a broker feed and authorises no execution.**

## Required columns (exact header, in this order)

```
timestamp_utc,open,high,low,close,source,timeframe
```

| Column | Type | Notes |
|---|---|---|
| `timestamp_utc` | ISO8601 UTC | Candle OPEN time, e.g. `2026-07-09T04:12:00Z` or `...:00.000Z`. Must be UTC. |
| `open` | float | Candle open price |
| `high` | float | Candle high |
| `low` | float | Candle low |
| `close` | float | Candle close |
| `source` | string | Where the data came from (e.g. `TradingView_export`, `Dukascopy`, `broker_history_export`). Free text; for provenance only. |
| `timeframe` | string | `1m`, `3m`, or `5m` |

## Timeframe preference

1. **1m** — preferred (tightest excursion resolution).
2. **3m** — acceptable (matches the Farouk chart interval).
3. **5m** — fallback only.

## Coverage required for the Gate G candidates

- **Window:** `2026-07-08T22:00:00Z` → `2026-07-09T10:30:00Z` (covers all 3 candidates + a 120m
  look-ahead past the latest anchor at ~09:51Z... the latest candidate anchor is 05:42Z, so 22:00Z→08:00Z
  is the strict minimum, but capture the full range to be safe).
- Continuous candles (no missing bars) across that window. Gaps are flagged as `PARTIAL`/warnings, never
  filled.

## Rules

- **UTC only.** If your export is in another timezone, convert to UTC before import (do not guess).
- **Do not fabricate or interpolate** missing bars. Leave gaps; the matcher flags them.
- One row per candle. Header row exactly as above.
- File encoding UTF-8, comma-separated.

## Target file

Place the populated CSV at:
`stage_c_tooling/price_data/XAUUSD_1M_2026-07-08_2026-07-09_IMPORT_HERE.csv`
(replace the header-only placeholder). See `PRICE_DATA_IMPORT_INSTRUCTIONS.md`.
