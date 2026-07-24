# Next: Order-Block Research Plan

**Observation-only roadmap** for the highest-value remaining gap — an **order-block (OB) proxy** — plus
the timezone-validation work. **No trading, no broker, no execution, no invented thresholds.**
`NOT_INTEGRATION_READY` unchanged.

## Why OB is next

Order-block retest is Farouk's **highest-supported entry family** in the corpus (C001/C003 wins). Our
pipeline currently does not claim OB at all (`MISSING_ORDER_BLOCK_DETECTOR`), so it's the single change
that could most raise a candidate's *methodology* confluence — if built honestly as a proxy.

## OB proxy design (offline, from OHLC)

Per corpus (`FAROUK_LEVEL_CONSTRUCTION_SPEC_v0.2.md` §C; OB Quality Model): OB = **last opposing candle
before a strong impulsive move**. Proxy steps (all `NEEDS_HUMAN_REVIEW`):

1. Detect a **displacement** proxy leg (reuse `chart_context_extractor` displacement).
2. The **last opposite-colour candle** immediately before that leg = OB proxy zone (body high/low).
3. **Freshness / tap-count:** count later touches of the zone; first-tap = strongest, mitigated/multiply-
   tapped = degraded (mark, don't discard).
4. **FVG-left-behind:** confirm a displacement-created FVG proxy near the OB (strong-OB precondition).
5. **Trend alignment:** compare to the HTF bias **proxy** (weak — not corpus-confirmed).

Output: `order_block_candidate` + zone bounds + freshness + `NEEDS_HUMAN_REVIEW`. **Do not claim a
confirmed OB.** Leave numeric thresholds (impulse size, mitigation) flagged UNKNOWN until validated.

## Timezone validation (unblock session)

Parallel track: resolve the chart→UTC mapping (corpus evidence conflicts — UTC+1 video vs UTC+2 edu vs
Europe/Berlin indicator vs unknown Discord). Only a **validated** mapping lets `session_context` move off
`SESSION_UNCONFIRMED`. Do **not** invent an offset; gather evidence (e.g. compare a known 13:30Z NY event
to the chart clock) before asserting.

## Integration (offline only)

Each new proxy becomes a populated `context` field for `farouk_methodology_scorer_v0_1` via the existing
offline adapter. Candidates rise above `SHADOW_CANDIDATE_LOW` **only** when evidence genuinely supports it;
ceiling stays `METHODOLOGY_ALIGNED_SHADOW` (observation-only).

## Sequencing

Runs alongside the Next-30 Observation Plan, the Methodology Data-Collection Plan, and the Chart-Context
Collection Plan. All feed the (unmet) `NO_TRADE_TO_DEMO_EVIDENCE_THRESHOLDS` review — which only permits a
governance *discussion* about a demo/paper study.

## Hard stops (unchanged)

No broker/cTrader/QST; no permits/leases/orders; no execution-gate or risk-policy change; no invented
thresholds; no order intent/sizing. Everything descriptive/proxy.

## Status

Plan defined. Observation-only, separately gated. Nothing trade-ready.
