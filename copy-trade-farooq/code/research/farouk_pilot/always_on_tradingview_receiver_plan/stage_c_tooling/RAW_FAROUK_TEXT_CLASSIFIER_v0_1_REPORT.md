# RAW FAROUK TEXT CLASSIFIER v0.1 — Report

**Mode:** OFFLINE PARSER / CLASSIFIER BUILD ONLY. Built from existing captured Gate G examples.
No R2 read, no Worker deploy, no TradingView touch, no broker/QST/execution.

## Files

- `raw_farouk_text_classifier_v0_1.py` — the classifier module (pure function, no I/O).
- `test_raw_farouk_text_classifier_v0_1.py` — unit tests.

## What it classifies

Input: `raw_text` (+ optional `received_at_utc`, `r2_object_key` passthroughs).
Output: a candidate-descriptor dict (`parse_version: raw_farouk_text_classifier_v0_1`).

| Raw pattern | event_family | event_type | direction |
|---|---|---|---|
| A LONG | A_SIGNAL | A_LONG | LONG |
| A SHORT | A_SIGNAL | A_SHORT | SHORT |
| CHoCH UP | STRUCTURE | CHOCH_UP | LONG_HINT |
| CHoCH DOWN | STRUCTURE | CHOCH_DOWN | SHORT_HINT |
| Bullish Engulfing | ENGULFING | BULLISH_ENGULFING | LONG_HINT |
| Bearish Engulfing | ENGULFING | BEARISH_ENGULFING | SHORT_HINT |
| BPR tapped | BPR | BPR_TAPPED | — |
| BPR formed | BPR | BPR_FORMED | — |
| Sweep high | LIQUIDITY_SWEEP | SWEEP_HIGH | SHORT_HINT |
| Sweep low | LIQUIDITY_SWEEP | SWEEP_LOW | LONG_HINT |
| A+ / A+ or better | A_PLUS | A_PLUS / A_PLUS_OR_BETTER | (opt) |
| A+++ | A_TRIPLE_PLUS | A_TRIPLE_PLUS | — |
| (none) | UNKNOWN | null | null |

- **Instrument/timeframe** extracted from `on <SYM> <TF>` (e.g. `on XAUUSD 3` → `XAUUSD`, `3`).
  Absent pattern → both `null` + a warning (never guessed).
- **Ordering guard:** A+++ / A+ patterns are checked *before* the bare `A LONG`/`A SHORT` rule, so
  `A+ LONG` classifies as `A_PLUS`, not `A_SIGNAL`.
- **`direction` for hints** is `LONG_HINT`/`SHORT_HINT` for structure/engulfing/sweep — a directional
  *bias descriptor*, explicitly NOT an order side.
- **`confidence`** is a description-quality heuristic (0.9 with instrument+TF, 0.6 without, 0.0 for
  UNKNOWN) — **not** a trade-quality or conviction score.

## Test results — ✅ PASS

`python test_raw_farouk_text_classifier_v0_1.py` → **Ran 16 tests, OK (0 failures).**

Covered: all 9 observed families (A LONG/SHORT, CHoCH UP/DOWN, Bull/Bear Engulfing, BPR tapped,
Sweep high/low) + BPR formed + the two not-yet-observed grades (A+ or better, A+++) + unknown text +
malformed/no-instrument + the A+/A-LONG ordering guard + passthrough fields. Every test also asserts
the safety invariants below on the output.

## Limitations

- Pattern/keyword based (regex), not a semantic parser. Novel indicator wording → `UNKNOWN` (by design;
  flagged in `warnings`, never force-fit).
- Trained only on the observed Gate G vocabulary. A+ / A+++ rules are from the spec, **not** yet seen in
  real captures — verify against a real A+ capture when H1 fires before trusting those branches.
- Timeframe is captured as the literal trailing chart number (`"3"`), not a validated duration.
- No timezone reconciliation here (that stays in the normalisation rules doc); `received_at_utc` is a
  verbatim passthrough.
- Direction hints are descriptive bias only and carry **no** execution meaning.

## Safety confirmations

- **Raw text remains the source of truth** — returned verbatim as `raw_text`, never overwritten or
  normalised away. The module matches on a local copy only.
- **All output is candidate-only** — `candidate_only` is hard-wired `True`;
  `is_trade_signal_candidate` is a *label a human might look at*, never a permission.
- **No execution fields / broker route / lot size / account ID / permit / lease / order are created.**
  `execution_allowed`, `broker_execution_allowed`, `qst_allowed` are hard-wired `False`. A test
  asserts none of `{order, order_intent, broker_route, route, lot, lot_size, position_size,
  account_id, account, risk, risk_sizing, permit, lease, sl, tp, stop_loss, take_profit}` appear in any
  output.
- **No I/O:** no network, no broker/cTrader/QST import, no R2 access, no Worker deploy. Pure function.
- **`NOT_INTEGRATION_READY` unchanged** — this is a read-only string classifier; it enables no path.

## Status

v0.1 — implemented, tested (16/16), offline. Feeds the observation/evidence base only.
