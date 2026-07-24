# Next Methodology Data-Collection Plan

**Observation-only roadmap** to close the methodology gaps by *deriving* the missing context from data we
can legitimately obtain offline (OHLC + captured alerts). **No trading, no broker, no execution, no
invented thresholds.** `NOT_INTEGRATION_READY` unchanged.

## Principle

Enrich the evidence, not the claims. Every new field is descriptive and feeds only the scorer's
`missing_evidence`/confluence — never an order path. Where the corpus marks a threshold UNKNOWN, we
compute the geometry but leave the *decision threshold* flagged until it's validated from evidence.

## Workstreams (each separately approved, all observation-only)

1. **Session mapping (unblock session_context).** Resolve the chart/Discord timezone to UTC; validate
   against known London 08:00Z / NY 13:30–15:00Z behaviour. Deliver a small offline session-tagger.
2. **OHLC-derived structure (BOS/CHoCH close-confirmation).** From imported 1m OHLC, compute
   close-beyond-level BOS and swing structure — descriptive, to complement the alert's CHoCH type.
3. **FVG detector (offline).** Implement the 3-candle FVG geometry from OHLC; track fill. Leave the
   fill-size threshold as a flagged parameter (corpus UNKNOWN) until validated.
4. **Order-block detector (offline).** Identify last-opposing-candle-before-impulse zones; track taps and
   freshness. Threshold-flagged.
5. **Displacement measure (offline).** A descriptive impulse metric from OHLC; do **not** hard-code a
   magnitude — record the value and mark the decision threshold UNKNOWN.
6. **BPR overlap (offline).** Once FVG exists, detect bullish/bearish FVG overlap zones.
7. **HTF bias context.** Derive 4H/Daily bias + trend-EMA alignment from OHLC (observation).
8. **Grade capture (not derivation).** Let the **H1 A+ mirror** capture real A+/A+++ alerts; log the raw
   grade literally. Never infer the grade formula.
9. **Alert↔channel integrity check.** Optionally reconcile captured alerts with the Farouk channel
   (integrity/provenance, not a trade signal).

## Feeding the scorer

As each workstream lands, its output becomes a populated `context` field for
`farouk_methodology_scorer_v0_1` (session_context, displacement, fvg, order_block, …). More positively
present factors → candidates can rise above `SHADOW_CANDIDATE_LOW` **only** when the evidence genuinely
supports it. The ceiling stays `METHODOLOGY_ALIGNED_SHADOW` (observation-only).

## Sequencing vs the evidence threshold

Run these alongside the **Next-30 Observation Plan** (accumulate ≥30 outcome-matched candidates). Both
must mature before the `NO_TRADE_TO_DEMO_EVIDENCE_THRESHOLDS` review — which itself only permits a
*governance discussion* about a demo/paper study.

## Hard stops (unchanged)

No broker/cTrader/QST; no permits/leases/orders; no execution-gate or risk-policy change; no invented
thresholds; no order intent/sizing. Outcome & derived numbers stay descriptive.

## Status

Plan defined. All items observation-only and separately gated. Nothing trade-ready.
`NOT_INTEGRATION_READY` remains until a future governance decision explicitly lifts it.
