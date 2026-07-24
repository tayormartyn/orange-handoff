# Next: Human-Review Workflow Plan

**Observation-only roadmap** to turn the machine PROXIES (FVG / displacement / OB / structure / session)
into human-confirmed or human-denied evidence. **No trading, no broker, no execution, no invented
thresholds.** `NOT_INTEGRATION_READY` unchanged.

## Why this is next

The pipeline now emits a proxy for every reachable factor, but each is `*_proxy` / `NEEDS_HUMAN_REVIEW`
and none is corpus-confirmed. The bottleneck is no longer detection — it is **validation**. A human must
confirm/deny proxies against the actual chart before any of them can count as real evidence.

## Proposed workflow (offline, human-in-the-loop)

1. **Review queue.** For each shadow candidate, assemble its proxies (chart context, session, HTF, OB) +
   outcome stats + raw alerts into one review record (extend `FAROUK_SHADOW_CAMPAIGN_EVIDENCE_SCHEMA`).
2. **Human verdict per proxy.** Martyn opens the chart at the anchor and marks each proxy:
   `CONFIRMED` / `DENIED` / `UNSURE`, with a short note. (FVG real? OB fresh or spent? displacement real?
   session correct once TZ known?)
3. **Record verdicts** in a `shadow_review_journal` (append-only; who/when/note). Never overwrite a proxy;
   add the verdict alongside.
4. **Re-score with confirmed evidence only.** Feed **only `CONFIRMED`** factors to the methodology scorer
   (proxies alone stay LOW). This is the first path by which a candidate could exceed
   `SHADOW_CANDIDATE_LOW` — and even then it stays observation-only.
5. **Proxy precision tracking.** Over many reviews, measure how often each proxy is CONFIRMED vs DENIED —
   this tells us which detectors to trust and which to fix.

## Guardrails

- Human review confirms **evidence**, not trades. A `CONFIRMED` OB is still not an order.
- No proxy is auto-promoted; confirmation is manual and logged.
- Corpus-UNKNOWN thresholds stay UNKNOWN until validated from data — human review does not invent them.
- The scorer ceiling stays `METHODOLOGY_ALIGNED_SHADOW` (observation-only). Reaching it requires
  CONFIRMED session + OB + favourable outcomes across enough samples — and still authorises nothing.

## Sequencing

Runs with: Next-30 Observation Plan (volume), Session timezone validation (unblock session), Methodology
& Chart-Context collection plans. All feed the (unmet) `NO_TRADE_TO_DEMO_EVIDENCE_THRESHOLDS` — which only
permits a governance *discussion* about a demo/paper study.

## Hard stops (unchanged)

No broker/cTrader/QST; no permits/leases/orders; no execution-gate or risk-policy change; no invented
thresholds; no order intent/sizing.

## Status

Plan defined. Observation-only, separately gated. Nothing trade-ready.
