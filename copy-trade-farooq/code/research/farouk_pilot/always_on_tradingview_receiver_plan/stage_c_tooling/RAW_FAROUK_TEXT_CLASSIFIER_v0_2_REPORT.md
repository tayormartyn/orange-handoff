# RAW FAROUK TEXT CLASSIFIER v0.2 — Report

**Mode:** OFFLINE CLASSIFIER v0.2 BUILD. v0.2 is a **copy** of v0.1 (v0.1 left intact) with one faithful
improvement. No R2 read, no deploy, no TradingView touch, no broker/QST/execution.

## Files

- `raw_farouk_text_classifier_v0_2.py` — the v0.2 module (v0.1 preserved separately).
- `test_raw_farouk_text_classifier_v0_2.py` — tests.

## What changed vs v0.1

**Only** instrument extraction. Everything else (families, types, direction hints, safety flags,
raw-text preservation) is identical.

- `on <SYM> <TF>` → instrument + timeframe (unchanged).
- **NEW:** `on <SYM>` with **no trailing number** (the Sweep alert format) → instrument extracted,
  `timeframe` stays `null`, warning **`TIMEFRAME_MISSING`** added. Timeframe is still **never guessed**.
- Confidence: sweep rows now score 0.9 (family + instrument known; missing TF is the alert's own format,
  not a parse failure) instead of 0.6.

Handled sweep forms (all → `instrument: XAUUSD`, `timeframe: null`, warning `TIMEFRAME_MISSING`):
`Sweep low (bullish) on XAUUSD`, `Sweep high (bearish) on XAUUSD`, `Sweep low on XAUUSD`,
`Sweep high on XAUUSD`.

## Test results — ✅ PASS

- `python test_raw_farouk_text_classifier_v0_2.py` → **20 tests, OK.**
  (14 preserved v0.1 behaviours + 6 new sweep/flag cases: instrument-only for all four sweep forms,
  `TIMEFRAME_MISSING` present, sweep-with-TF still parses the full pair, execution flags stay false.)
- `python test_raw_farouk_text_classifier_v0_1.py` → **16 tests, OK** (v0.1 unchanged).

## v0.2 replay over Gate G (74 events)

- **74 / 74 classified, 0 unknown.**
- **All 10 Sweep captures now extract `instrument: XAUUSD`** with `timeframe: null` +
  `TIMEFRAME_MISSING` (v0.1 had returned instrument null for these).
- Confidence: **74/74 at 0.9** (v0.1 had 10 at 0.6 — the sweep gap is now closed).

## Safety confirmations

- **Raw text is the source of truth** — returned verbatim; matched on a local copy only.
- **All outputs candidate-only** — `candidate_only=true`;
  `execution_allowed=broker_execution_allowed=qst_allowed=false` (hard-wired; asserted in tests).
- **No execution field / broker route / lot size / account ID / risk sizing / permit / lease / order.**
- **No I/O:** no network, no broker/cTrader/QST import, no R2, no deploy.
- **`NOT_INTEGRATION_READY` unchanged.**

## Status

v0.2 — implemented, tested (20/20), offline. v0.1 retained unchanged.
