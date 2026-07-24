# Next: Shadow-Observation Readiness

**Mode:** OFFLINE READINESS NOTE. Candidate-only, design-only. **Authorises nothing** — no execution,
no broker, no order, no gate/risk change. Describes the next *observation* work now that one window has
been outcome-matched. Still capture-only. `NOT_INTEGRATION_READY` unchanged.

## Where we are

First full loop is closed for one session: capture → classify (v0.2) → shadow candidates (v0.1) →
outcome match (v0.1, real 1m OHLC). Result across n=3: **1 directional hit (with early drawdown), 1 fade,
1 miss.** Not an edge — but the pipeline now works end-to-end and produces honest, measurable outcomes.

## What raises observational confidence (each separately approved, all observation-only)

1. **More windows.** The single biggest gap is sample size. Keep the always-on capture lane running and
   let the H1/H2 low-volume mirrors gather the rare families (A+, CHoCH DOWN) across many sessions.
2. **Outcome-match each new window** with the same matcher (import OHLC per the schema, re-run). Build a
   growing table of candidate → excursion outcomes.
3. **Per-candidate-type aggregates.** Once there are enough instances (target: dozens per type, not 1),
   compute hit-rate, median MFE vs MAE, and drawdown-before-follow-through — descriptively.
4. **Drawdown characterisation.** The MEDIUM CHoCH→A only worked after ~−6.8 adverse heat; quantify how
   often "eventual hits" require surviving adverse excursion first (matters for any future study design).
5. **Contradictory-cluster filter test.** Check whether excluding candidates that sit inside a
   contradictory cluster improves the descriptive hit-rate.

## Explicit non-goals (still prohibited)

- No broker/cTrader/QST connection; no order/permit/lease; no execution-gate or risk-policy change; no
  position sizing or PnL framing. Outcome numbers stay descriptive price stats.
- No promotion of any candidate to a signal — not even the one that hit. n=1 per type.

## Readiness verdict

**Observation-only, continue.** The pipeline is validated; the *evidence* is not. Next concrete step:
accumulate more outcome-matched windows before any aggregate is meaningful. A written shadow-observation
spec (KPIs, sample-size targets, still no execution) should precede any larger study.

## Status

Design-only readiness note. No implementation beyond the existing offline tools. Enables no trading.
