# Price Data Import Instructions (XAUUSD OHLC)

For **research/observation only**. This is reference price data, **not** a broker connection and
**not** an execution path. Importing it changes nothing about `NOT_INTEGRATION_READY`.

## What to provide

XAUUSD OHLC candles covering **2026-07-08T22:00:00Z → 2026-07-09T10:30:00Z** (UTC), timeframe **1m**
preferred (3m acceptable, 5m fallback), matching `XAUUSD_OHLC_IMPORT_SCHEMA_v0_1.md`:

```
timestamp_utc,open,high,low,close,source,timeframe
2026-07-08T22:00:00Z,4001.20,4002.10,4000.80,4001.55,TradingView_export,1m
...
```

Save/replace the file at:
`stage_c_tooling/price_data/XAUUSD_1M_2026-07-08_2026-07-09_IMPORT_HERE.csv`

## Option A — TradingView export (no broker needed)

1. Open a **XAUUSD** chart on the **1-minute** timeframe (same feed you use, e.g. PEPPERSTONE).
2. Scroll so the range 2026-07-08 22:00 → 2026-07-09 10:30 **UTC** is loaded. (Note your chart's
   timezone; if it's not UTC you must convert — see "Timezone" below.)
3. Export bars: **chart menu → Export chart data** (TradingView paid plans allow CSV export of the
   visible series). Choose CSV.
4. Open the CSV; ensure columns map to `timestamp_utc, open, high, low, close`. Add a `source` column
   (e.g. `TradingView_export`) and a `timeframe` column (`1m`).
5. Convert timestamps to **UTC ISO8601** (e.g. `2026-07-09T04:12:00Z`) if not already.

## Option B — Public historical data (no broker, no live feed)

1. Use a public historical FX/metals source that offers XAUUSD 1-minute history (e.g. a Dukascopy-style
   historical export). Download only the required date range.
2. Reformat to the schema columns above. Set `source` to the provider name.
3. Ensure UTC.

*(Both options are read-only historical data. Do NOT use a broker trading API, cTrader, or QST to pull
this — a live trading connection is out of scope and prohibited here.)*

## Timezone (critical)

- `timestamp_utc` **must be UTC**. TradingView often displays exchange/local time.
- Convert explicitly; do **not** guess an offset. If unsure of your chart's timezone, note it and I can
  help convert during import.
- The Gate G alert times are already UTC (`received_at_utc`), so UTC candles line up directly.

## Anchors the matcher will use (for your reference)

| Candidate | Anchor (UTC) | Needs candles through |
|---|---|---|
| ALIGNED_CHOCH_TO_A (LONG) | 2026-07-09T04:12:01Z | ~06:12Z (anchor +120m) |
| SWEEP_TO_CHOCH_CONTEXT (LONG) | 2026-07-09T00:03:01Z | ~02:03Z |
| BPR_TO_A_CONTEXT (SHORT) | 2026-07-09T05:42:01Z | ~07:42Z |

So the **minimum** useful range is 2026-07-09T00:00Z → 07:45Z; the requested 22:00Z→10:30Z is a safe
superset.

## After import

Tell me "price data imported" and I will re-run `outcome_matcher_v0_1` over the 3 candidates and write
the real outcome report. **No trading, no broker, no order** — measurement only.

## Do NOT

- Do not fabricate or interpolate missing candles.
- Do not use a broker/cTrader/QST live connection.
- Do not paste the file contents into chat if large — just save it to the path above.
