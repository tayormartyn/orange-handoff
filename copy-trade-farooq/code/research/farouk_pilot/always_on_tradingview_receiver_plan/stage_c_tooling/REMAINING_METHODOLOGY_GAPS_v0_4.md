# Remaining Methodology Gaps v0.4

Update after adding the order-block proxy. **Observation-only; grants nothing.** `NOT_INTEGRATION_READY`
unchanged.

## Status of each factor

| Factor | v0.3 | v0.4 status |
|---|---|---|
| FVG | ⚠️ proxy | ⚠️ proxy (unchanged) |
| Displacement | ⚠️ proxy | ⚠️ proxy (unchanged) |
| Local structure/swings | ⚠️ proxy | ⚠️ proxy (unchanged) |
| Session | ⚠️ proxy, unconfirmed | ⚠️ proxy, unconfirmed (unchanged) |
| HTF bias | ⚠️ proxy, not scored | ⚠️ proxy, not scored (unchanged) |
| **Order block** | ❌ missing | ⚠️ **proxy now available** (LOW, requires_human_review; found for 2/3, one mitigated) — still NOT a confirmed OB |

## Every proxyable factor is now surfaced

The build-up (alert → chart-context → session/HTF → **OB proxy**) has now produced a proxy for **every**
factor our OHLC pipeline can reach. Result: **all 3 candidates remain `SHADOW_CANDIDATE_LOW`.** Proxies
raised scores (SWEEP to 0.69) but never a label — exactly as intended.

## What still HARD-blocks readiness

| Blocker | Why |
|---|---|
| **Confirmed session (timezone)** | Canonical TZ deliberately unresolved (BLOCKED); Asia window absent; DST unhandled. |
| **Reviewed (not proxy) order block** | OB is LOW-confidence proxy, human-review-required; FVG-left-behind / first-tap / HTF alignment unconfirmed; one candidate's OB already mitigated. |
| **Confirmed HTF bias** | No SMC EMA/bias rule in corpus; data-limited (1h insufficient). |
| **Grade formula** | Not exposed; 0 A+/A+++ observed. |
| **Confirmed FVG/displacement thresholds** | Sizes/fill UNKNOWN — proxies stay NEEDS_HUMAN_REVIEW. |
| **Sample size / outcomes** | n=3, one session, mixed-to-poor (1 hit-with-drawdown / 1 fade / 1 miss). |

## The gating shift

We have moved from **"can't see the factors"** to **"can see PROXIES for the factors, none reviewed or
corpus-confirmed."** The remaining work is therefore about **validation and volume**, not new detectors:
1. **Human review** of proxies (turn `*_proxy`/NEEDS_HUMAN_REVIEW into confirmed/denied) — see
   `NEXT_HUMAN_REVIEW_WORKFLOW_PLAN.md`.
2. **Timezone validation** (unblock session).
3. **More outcome-matched windows** (toward the ≥30 threshold).
4. Only corpus-validated thresholds may promote a proxy — never invention.

## Verdict

**Nothing trade-ready.** Best label `SHADOW_CANDIDATE_LOW`. Next: build the human-review workflow so
proxies can be confirmed/denied by a person, and keep accumulating outcome-matched windows.
