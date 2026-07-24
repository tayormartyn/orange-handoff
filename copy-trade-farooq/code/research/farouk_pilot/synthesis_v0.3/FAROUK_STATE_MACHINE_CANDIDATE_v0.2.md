# FAROUK STATE-MACHINE CANDIDATE — v0.2 (proposal)

**PROPOSAL ONLY.** Does NOT overwrite `FAROUK_STATE_MACHINE_SPEC_v0.1`. No code; not connected to QST; no
execution/risk change. Extends v0.1 to ingest **untrusted TradingView alert events**.

## Architecture (preserved + extended)
- **Hierarchical + orthogonal regions** from v0.1 retained: SESSION_CONTEXT, VALUE_LOCATION, LIQUIDITY_EVENT,
  ORB_EVENT (concurrent) + STRUCTURAL_SETUP, QUALIFICATION (per-setup-instance) + CAMPAIGN_LIFECYCLE
  (reference-only, outside the Alpha detector).
- **NEW ingestion region — ALERT_INTAKE** (untrusted): `ALERT_RECEIVED → OBSERVATION_VALIDATED →
  EVENT_DEDUPLICATED` feeds the primitive-event layer. **TradingView events are UNTRUSTED observations**, not
  authorised signals.
- **Multiple setup-family branches** (Layer-4 families) — each with its own guards; no shared guard chain.
- **Primitive events separated from composite grades**: A+++/A+ grades are recorded as INDICATOR_MECHANIC
  observations, NOT as qualification logic (the formula is unknown).
- **Setup lifecycle separated from campaign lifecycle** (campaign management stays reference-only, outside Alpha).

## Proposed states (this delta)
| State | Meaning | Notes |
|---|---|---|
| `ALERT_RECEIVED` | a TradingView alert() event arrived | UNTRUSTED; schema/source unknown until validated |
| `OBSERVATION_VALIDATED` | envelope valid (symbol/tf/bar-close-time/source) | drop malformed |
| `EVENT_DEDUPLICATED` | not a duplicate/stale repeat | dedupe by (family, level, bar_close_time); drop stale |
| `FAMILY_ADJUDICATED` | routed to the family whose guards match | no-match → discard |
| `QUALIFICATION_PENDING` | family context+location+events satisfied | fail-closed on any UNKNOWN |
| `QUALIFIED_CANDIDATE` | trigger + required confluence true (closed-bar) | **terminal Alpha state; emits an OBSERVATION only; NOT a trade** |
| `INVALIDATED` | invalidation event / repaint mutation | terminal |

## Fail-closed unknown handling
Any UNKNOWN required input (confluence count, displacement/mitigation threshold, POC-window, repaint status,
timezone authority, alert payload) **BLOCKS** the transition (fail-closed). Confidence may degrade on
non-terminal context transitions only; never on `→ QUALIFIED_CANDIDATE`.

## Untrusted-event handling (new)
- **Dedup + stale**: an alert is accepted once per (family, level, bar_close_time); repeats and out-of-order/
  late events are dropped and logged.
- **Repaint guard**: if a previously-validated event's underlying value mutates after the bar, the associated
  candidate is `INVALIDATED`. (Repaint behaviour is UNKNOWN → this path is BLOCKED_BY_LIVE_VALIDATION.)
- **A+++ ≠ trade**: an `A+++ setup` alert is an observation feeding QUALIFICATION_PENDING at most; it never
  auto-reaches an executable state, and never leaves the Alpha boundary.

## Transitions
See `STATE_TRANSITION_EVIDENCE_MATRIX_v0.2.csv` — each transition lists supporting evidence, objective guard,
family scope, unresolved dependency, failure path, and confidence.

## Invariants carried from v0.1 (unchanged)
Registration-before-qualification; no confirmation on an unclosed candle (unless future evidence permits);
immutable setup origin; no resurrection without a new identity; **no Alpha transition creates risk/size/broker
instructions**; campaign risk external; execution gates irrelevant to detector progression; **no probability
model** (Boolean/veto/data/confidence/family-class only).

## Feasibility snapshot
Deterministic-now: OBSERVATION_VALIDATED (envelope), EVENT_DEDUPLICATED, INVALIDATED (close-through). Blocked:
FAMILY_ADJUDICATED/QUALIFICATION (thresholds + confluence count), repaint guard (live), and the whole intake
(alert payload/timing UNKNOWN). **Not final; not connected to QST.**
