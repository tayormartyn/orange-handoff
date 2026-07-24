# Methodology Gaps Before Trading v0.1

**What evidence is missing before any trading discussion may even begin.** Observation-only; grants
nothing. `NOT_INTEGRATION_READY` unchanged.

## Headline

Our alert-only pipeline observes a **small slice** of Farouk's documented methodology. The
**highest-weight confluence factors are exactly the ones we cannot see**, so the scorer correctly caps
every real candidate at `SHADOW_CANDIDATE_LOW`/`WATCH`. Closing these gaps is a prerequisite even to reach
the observation ceiling — let alone to discuss trading.

## Gap register

| Factor | Status | Why it's missing | What's needed (observation-only) |
|---|---|---|---|
| **Session context** | ❌ blocker | Chart timezone unresolved (platform UTC+2, Discord TZ unknown); session guard fail-closes | Establish & validate a UTC session mapping (London 08:00Z, NY 13:30–15:00Z) |
| **Displacement** | ❌ blocker | No numeric magnitude defined in corpus ("do NOT invent"); not in alert text | Price-derived impulse measure from OHLC (descriptive), plus a corpus-validated threshold |
| **FVG** | ❌ blocker | 3-candle gap geometry + fill threshold unknown; not captured | Compute FVG geometry from OHLC (offline), define fill rule from corpus |
| **Order block** | ❌ blocker | "Last opposing candle before impulse", tap-count, freshness not captured | Derive OB zones from OHLC + track taps (observation) |
| **BPR (geometry)** | ⚠️ partial | We see BPR tapped/formed *event*, not the FVG-overlap geometry/tolerance | Overlap detection from FVG pairs once FVG exists |
| **Grade A+/A+++** | ⚠️ partial | Indicator emits grades but the **confluence formula is not exposed**; 0 seen so far | Capture real A+/A+++ alerts (H1 mirror); never infer the grade |
| **Direction/HTF bias** | ⚠️ partial | Only intra-sequence bias; no 4H/Daily or trend-EMA feed | Add HTF bias context from OHLC (observation) |
| **Telegram/Discord confirmation** | n/a | Corpus: delivery target, **not** a confluence factor | Optional cross-check that captured alerts match the channel (integrity, not a signal) |
| **Sample size / outcomes** | ❌ blocker | n=3, one session; outcomes mixed-to-poor | Accumulate ≥30 outcome-matched candidates across ≥5 sessions (see thresholds) |

## Corpus reality check (do NOT invent)

The methodology corpus explicitly marks displacement magnitude, FVG size/fill, BPR tolerance, OB
mitigation/tap-count, the **grade formula**, the confluence minimum, and the session timezone as
**BLOCKED/UNKNOWN**. Any of these must be resolved from evidence, never fabricated. Until then the scorer
keeps them as `missing_evidence`.

## What clearing the gaps unlocks (and does not)

- **Unlocks:** the *possibility* of reaching `METHODOLOGY_ALIGNED_SHADOW` on real candidates, and a richer
  evidence base for the (still unmet) `NO_TRADE_TO_DEMO_EVIDENCE_THRESHOLDS`.
- **Does NOT unlock:** trading, broker/cTrader/QST, orders, sizing, or any gate/risk change. Those remain
  separately governed. `METHODOLOGY_ALIGNED_SHADOW` is an observation ceiling, not a green light.

## Status

Gaps catalogued. Nothing trade-ready. Next: begin observation-only enrichment (OHLC-derived
structure/FVG/OB/session) — see `NEXT_METHODOLOGY_DATA_COLLECTION_PLAN.md`.
