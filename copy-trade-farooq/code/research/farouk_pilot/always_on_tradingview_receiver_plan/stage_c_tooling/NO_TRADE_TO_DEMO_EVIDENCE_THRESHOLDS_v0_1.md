# No-Trade → Demo: Evidence Thresholds v0.1

**Conservative gate BEFORE any future demo-broker discussion may even begin.** This document sets the
evidence bar; it **grants nothing**. Meeting every item does **not** authorise trading — it only makes a
future *governance discussion* about a demo/paper study permissible. `NOT_INTEGRATION_READY` stays until
a separate, explicit governance decision lifts it.

## Current status: ⛔ NOT MET — 3 / 30 observations

## Minimum thresholds (ALL required)

1. **≥ 30 outcome-matched candidates** in the shadow observation journal (currently 3).
2. **Spread across multiple days / sessions** — not one window (currently 1). Target ≥ 5 distinct
   sessions so a single regime can't dominate.
3. **Cleaned by candidate type** — evaluated per type (ALIGNED_CHOCH_TO_A, SWEEP_TO_CHOCH_CONTEXT,
   BPR_TO_A_CONTEXT, …), each with enough instances to be non-anecdotal (target ≥ 10 per type before any
   type is even discussed).
4. **No reliance on the ANY_ALERT composite alone** — candidates must come from specific low-volume
   families, not the noisy composite stream.
5. **Adverse excursion measured** for every observation (MAE at 15/30/60/120m) and reviewed — a
   favourable close that required surviving large drawdown is not "clean."
6. **False-positive review** — for each candidate type, how often the hint was wrong (like SOJ-0003).
7. **Missed-signal review** — moves that happened with **no** candidate (was the detector blind?).
8. **Telegram / Discord confirmation where applicable** — cross-check that captured alerts correspond to
   what Farouk's channel actually signalled (guards against capture artefacts).
9. **Manual review before any approval workflow** — a human reads the aggregate and signs off; no
   auto-promotion from data to decision.
10. **Zero automatic broker path** — no code path exists that could route an observation to an order.
    Any future demo would be a separate, manually-built, explicitly-gated component.
11. **`NOT_INTEGRATION_READY` remains** until explicitly lifted by a future governance decision — never
    by a script, a threshold being met, or this document.

## What meeting the bar unlocks (and does NOT)

- **Unlocks:** permission to *hold a governance discussion* about designing a **demo/paper** observation
  study (still no live money, still no auto-execution).
- **Does NOT unlock:** live trading, broker/cTrader/QST connection, order intent, sizing, or any change
  to gates/risk. Those remain out of scope and separately gated.

## Anti-goals (never acceptable as "evidence")

- A single favourable case (n=1) for a type. Cherry-picked windows. Ignoring adverse heat. Counting the
  ANY_ALERT composite as a signal. Any PnL/"would-have-made" framing.

## Status

Thresholds defined. 3/30. No trade, no demo, no broker. Continue observation.
