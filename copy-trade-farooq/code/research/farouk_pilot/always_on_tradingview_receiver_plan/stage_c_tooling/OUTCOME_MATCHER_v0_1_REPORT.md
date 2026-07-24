# OUTCOME MATCHER v0.1 — Report

**Mode:** OFFLINE OUTCOME-MATCHING PREP + SCAFFOLD. Measures (descriptively) whether price moved
favourably/adversely after a candidate sequence. **Research-only, candidate-only.** No R2, no deploy, no
TradingView, no broker/QST, no live download.

## Files

- `outcome_matcher_v0_1.py` — the matcher (pure compute; CSV reader is the only file access, read-only).
- `test_outcome_matcher_v0_1.py` — tests (synthetic OHLC only).
- `XAUUSD_OHLC_IMPORT_SCHEMA_v0_1.md` — the CSV schema.
- `price_data/XAUUSD_1M_2026-07-08_2026-07-09_IMPORT_HERE.csv` — header-only import target (no data).

## What it computes (per candidate)

Anchor = `window_end_utc` (the confirming event). `entry_reference_price` = close of the first candle
at/after the anchor. Then, over horizons **15 / 30 / 60 / 120 min**, oriented to the candidate's
`direction_hint`:

- `max_favourable_excursion_{h}m` — best move **in** the hinted direction (price units, ≥0).
- `max_adverse_excursion_{h}m` — worst move **against** the hinted direction (price units, ≤0).
- `final_close_delta_{h}m` — close at the horizon minus entry, oriented to the hint.
- `data_quality` ∈ {FULL, PARTIAL, NO_DATA}; `warnings`.

Plus the hard-wired safety block: `candidate_only=true`,
`execution_allowed=broker_execution_allowed=qst_allowed=order_intent=risk_sizing_allowed=false`.

**These are descriptive PRICE statistics in price units — NOT PnL, NOT position sizing, NOT SL/TP, NOT a
trade instruction.**

## Honesty guarantees

- **Never fabricates.** No OHLC → `NO_DATA`, metrics `None`, warning. Anchor beyond data range →
  `NO_DATA`. A horizon the data doesn't span → that horizon left `None` (not taken from an earlier
  candle) + warning.
- Anchor picks the **first candle at/after** the candidate time.
- confidence/interpretation is left to the reader; the matcher only measures.

## Test results — ✅ PASS

`python test_outcome_matcher_v0_1.py` → **8 tests, OK.** Covers: LONG favourable-high/adverse-low; SHORT
favourable-low/adverse-high; missing OHLC → warning not fake; anchor = first candle at/after; anchor past
all data → NO_DATA; partial coverage flagged with uncovered horizons left null; all safety flags false /
no order-risk-broker fields; match_all shape.

## Real-data run status — ✅ COMPLETE

XAUUSD 1m OHLC was imported (1145 candles, UTC, `PEPPERSTONE_TradingView_export`) and the matcher was run
over all 3 Gate G shadow candidates. **All 3 returned `data_quality: FULL`, no warnings**, all safety
flags false. Results in `GATE_G_SHADOW_CANDIDATE_OUTCOME_MATCHING_v0_1.md`. Summary: 1 of 3 agreed with
its direction hint at the 120m close (the MEDIUM CHoCH→A, after early adverse heat); the two LOW context
candidates faded or reversed. **No candidate trade-ready.** The earlier empty-CSV run confirmed the
no-fabrication path (`NO_DATA`).

## Safety confirmations

- All outputs candidate-only; no execution / order / broker / lot / account / risk / permit / lease
  field anywhere.
- Offline; read-only CSV access only; no broker/cTrader/QST; no live download.
- **`NOT_INTEGRATION_READY` unchanged.**

## Status

v0.1 scaffold — implemented, tested (8/8). Awaiting price data to produce real outcomes.
