# Next Chart-Context Collection Plan

**Observation-only roadmap** to strengthen the chart-context proxies toward validated context — still
**no trading, no broker, no execution, no invented thresholds.** `NOT_INTEGRATION_READY` unchanged.

## Priority order (each separately approved, all offline)

1. **Resolve the session timezone (highest value).** Establish and validate the real chart→UTC mapping so
   `session_context` can move from `*_UTC_PROXY` to a confirmed session (London 08:00Z / NY 13:30–15:00Z).
   Until validated, keep TIMEZONE_POLICY_UNCONFIRMED. Deliver a small, tested session-tagger.
2. **Order-block proxy (conservative).** Build an OB detector: last opposing candle before a displacement
   proxy, leaving an FVG proxy, first-tap tracking. Mark every output `NEEDS_HUMAN_REVIEW`; do not claim a
   confirmed OB. Only then can the scorer's `order_block` factor be (tentatively) populated.
3. **HTF bias context.** Import/derive 4H and Daily bias + a trend-EMA proxy (observation) to replace
   `MISSING_HTF_DATA`. Needs additional OHLC timeframes (read-only import, same schema).
4. **BPR overlap proxy.** Once FVG proxies exist on both directions, detect overlap zones → `bpr_candidate`
   geometry (currently only the BPR *event type* is seen).
5. **Threshold calibration (evidence-driven, never invented).** For displacement size and FVG fill, record
   the measured values across many windows and only later propose thresholds *from the data*, flagged until
   corpus-validated.
6. **Validate proxies against human review.** Periodically have a human confirm/deny a sample of
   `*_candidate` proxies (FVG/displacement/structure) to measure proxy precision before any reliance.

## Integration (offline only)

Each new proxy becomes a populated `context` field for `farouk_methodology_scorer_v0_1` via the existing
offline adapter — never a live pipeline. Candidates rise above `SHADOW_CANDIDATE_LOW` **only** when the
evidence genuinely supports it; the ceiling stays `METHODOLOGY_ALIGNED_SHADOW` (observation-only).

## Sequencing

Run alongside the **Next-30 Observation Plan** (accumulate ≥30 outcome-matched candidates) and the
**Next Methodology Data-Collection Plan**. All three feed the (still unmet)
`NO_TRADE_TO_DEMO_EVIDENCE_THRESHOLDS` review — which only permits a governance *discussion* about a
demo/paper study.

## Hard stops (unchanged)

No broker/cTrader/QST; no permits/leases/orders; no execution-gate or risk-policy change; no invented
thresholds; no order intent/sizing. Everything descriptive/proxy.

## Status

Plan defined. All items observation-only and separately gated. Nothing trade-ready.
