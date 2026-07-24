# Next: Outcome-Matching Readiness

**Mode:** OFFLINE READINESS NOTE. Candidate-only, design-only. **Authorises nothing** — no execution,
no broker, no order, no gate change. Describes the next *observation* step: pairing candidates with what
price actually did, to test the direction hints. Still capture-only.

## Why outcome matching is the natural next step

The shadow-candidate detector produces *sequences* but cannot say whether a direction hint was "right" —
there is no price/outcome data attached. Outcome matching would overlay subsequent price movement onto
each candidate, turning "CHoCH_UP→A_LONG happened" into "…and price moved +X / −X over the next N
minutes." This remains **observation only** — measuring, not trading.

## Inputs it would need (all read-only)

1. **The classified candidates** (already produced: `gateg_shadow_candidates` + replay report).
2. **Historical XAUUSD/3m price** for the candidate windows — from a **read-only** market-data source
   (e.g. a historical bars export). **No broker connection**; a data feed is not an execution surface.
   *(Choosing/adding that source is a separate, explicitly-approved step.)*

## What it would compute (observation metrics only)

- Per candidate: price at `window_start` vs price at +5/+15/+30/+60 min; max favourable / adverse
  excursion; did the move agree with `direction_hint`?
- Aggregate hit-rate of `direction_hint` per candidate_type (descriptive only).
- **No** SL/TP, position size, PnL-as-instruction, or "would have made $X" framing that implies trading.

## Hard constraints (must hold in any future build)

- Read-only; no broker/cTrader/QST; no order/permit/lease; no execution-gate or risk-policy change.
- Metrics are descriptive statistics, never trade instructions or sizing.
- Price data is reference input; it authorises no path.
- `NOT_INTEGRATION_READY` remains unchanged.

## Readiness verdict

**Not built, not scheduled.** Prerequisites: (a) a read-only historical price source is chosen and
approved, (b) more candidate windows accumulate (H1/H2 mirrors gathering rare families), (c) a written
outcome-matching spec is reviewed. Until then, continue capture-only observation.

## Status

Design-only readiness note. No implementation. Observation-only roadmap; enables no trading.
