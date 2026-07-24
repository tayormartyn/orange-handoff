# Chart Context Extractor v0.1 — Report

**Mode:** OFFLINE CHART-CONTEXT EXTRACTOR. Reads OHLC and produces **candidate-only / proxy** context
around a shadow candidate's anchor. **Never claims a real Farouk OB / FVG / BPR / displacement.** No R2,
no deploy, no TradingView, no broker/QST. `NOT_INTEGRATION_READY` unchanged.

## Files

- `chart_context_extractor_v0_1.py` — the extractor (pure compute; read-only CSV helper).
- `test_chart_context_extractor_v0_1.py` — tests (synthetic OHLC).
- `CHART_CONTEXT_SESSION_CONFIG_v0_1.md` — tentative UTC session buckets (proxy).

## Output (per anchor)

extractor_version, anchor/lookback/forward, `session_context` (+`session_warning`
TIMEZONE_POLICY_UNCONFIRMED), local_swing_high/low, `liquidity_sweep_candidate`,
`structure_shift_candidate`, `displacement_candidate` + `displacement_measure` (ratio + NEEDS_HUMAN_REVIEW),
`fvg_candidate`/`fvg_direction`/`fvg_bounds` (NEEDS_HUMAN_REVIEW), `bpr_candidate`,
`order_block_candidate` (+`order_block_warning` MISSING_ORDER_BLOCK_DETECTOR), `htf_bias_available`
(+`htf_bias_warning` MISSING_HTF_DATA), `context_confidence` (*_PROXY), `missing_evidence`, `warnings`,
and the hard-wired safety block (candidate_only=true; execution/broker/qst/order_intent/risk_sizing=false).

## Proxy discipline (the important rule)

- **No confirmed primitives.** Everything is `*_candidate` / `*_proxy`. FVG and displacement carry
  `NEEDS_HUMAN_REVIEW` (corpus thresholds UNKNOWN — "do NOT invent"). Session is `*_UTC_PROXY` with
  `TIMEZONE_POLICY_UNCONFIRMED`. HTF is `MISSING_HTF_DATA`.
- **Order block is NOT claimed** at v0.1 — `order_block_candidate=false`, `MISSING_ORDER_BLOCK_DETECTOR`.
- **No fabrication:** missing/short OHLC or unparseable anchor → warnings + null fields,
  `context_confidence=NONE`.

## Methods (all proxies)

- **Displacement proxy:** window max candle range vs rolling avg true range over the previous 20 candles;
  `displacement_candidate` when max range ≥ 2.0× ATR (conservative, documented default; NEEDS_HUMAN_REVIEW).
- **FVG proxy:** 3-candle imbalance (bullish `c1.high<c3.low` / bearish `c1.low>c3.high`); prefers the
  most recent imbalance completed at/before the anchor; returns bounds.
- **Structure/sweep proxies:** close-beyond-prior-swing (crude BOS/CHoCH) and wick-beyond-then-close-back
  (sweep). Do **not** override the raw TradingView CHoCH alert.
- **Swings:** local high/low over the window.

## Test results — ✅ PASS

`python test_chart_context_extractor_v0_1.py` → **10 tests, OK.** Covers: session proxy + unconfirmed
warning; displacement detected on expansion; no displacement on calm candles; bullish & bearish FVG
proxies (with NEEDS_HUMAN_REVIEW); MISSING_HTF_DATA present; order block not claimed; malformed/empty
OHLC → warning not fake; unparseable anchor → warning; all safety flags false.

## Safety confirmations

- All outputs candidate-only; no execution / order / broker / lot / account / risk / permit / lease field.
- Offline; read-only CSV; no broker/cTrader/QST; no deploy.
- **`NOT_INTEGRATION_READY` unchanged.**

## Status

v0.1 — implemented, tested (10/10). Applied to the 3 Gate G candidates (see replay + rescoring reports).
