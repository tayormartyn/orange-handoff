# Human Review Batch 001 — Consolidated Summary

**Mode: post-human-review synthesis. Observation-only; candidate-only.** No trade instruction, order intent,
broker route, lot size, account ID or risk sizing anywhere. `NOT_INTEGRATION_READY` unchanged.

**Batch:** the 3 outcome-matched Gate G shadow candidates (2026-07-09, XAUUSD 1m,
PEPPERSTONE_TradingView_export), all reviewed against corrected TradingView screenshots (1m / 3m / true-15m
/ Jul-9 1h, chart tz **UTC+1** confirmed). **Queue status: 3 / 3 REVIEWED.**

---

## Per-candidate outcomes

### HR-0001 — ALIGNED_CHOCH_TO_A — **SHADOW_CANDIDATE_LOW** / REVIEWED
- LONG, anchor 2026-07-09T04:12:01Z, entry 4063.96, outcome **MIXED** (early −6.8 heat, then +25.56 close /
  +35.49 peak @120m).
- **Reason:** human review **overturned the machine on structure** — the indicator drew a real Asia-Low
  **sweep → OB + BPR + FVG + CHoCH** cluster that the machine proxies **under-detected** (no OB proxy;
  displacement 1.91× sat just under the 2.0× gate). Provisionally MEDIUM, then **reverted to LOW** once the
  corrected 1h confirmed **HTF (multi-day downtrend) OPPOSES the LONG** (counter-trend). Ungraded, n=1.
- The only candidate with a favourable-ish outcome, but still capped and **not trade-ready**.

### HR-0002 — SWEEP_TO_CHOCH_CONTEXT — **WATCH** / REVIEWED
- LONG, anchor 2026-07-09T00:03:01Z, entry 4080.83, outcome **UNFAVOURABLE** (brief +8.87 then faded to
  −5.38 close, MAE −18.57).
- **Reason:** structure present but weak — real sweep of the ~4030 low but **entered late** (~45 pts above
  it), **CHoCH minor-in-chop**, the "fresh" **OB (4076.28–4076.89) was breached** on the fade (low ≈ 4062),
  displacement only moderate, and the valid **1h HTF does NOT support the LONG**. **Reverted one notch down**
  from the machine's provisional SHADOW_CANDIDATE_LOW → WATCH. Not trade-ready.

### HR-0003 — BPR_TO_A_CONTEXT — **REJECT** / REVIEWED
- SHORT, anchor 2026-07-09T05:42:01Z, entry 4074.97, outcome **UNFAVOURABLE** (never worked — MFE +1.15,
  MAE −36.16, close −34.75 @120m).
- **Reason:** the short fired **at a reversal low into a strong bullish impulse**; the bearish **OB
  (4071.48–4072.05) was spent/mitigated and traded straight through**; displacement was **bullish (against
  the short)**; FVGs bullish; the anchor **bounced off the Asia Low** → immediate bias opposed the SHORT.
  The short thesis was **invalidated**, not merely weak → REJECT. Worst of the three.

---

## Common failure patterns

1. **HTF was against the trade in all three.** HR-0001 & HR-0002 were LONGs into a multi-day 1h downtrend;
   HR-0003 was a SHORT into an intraday bullish reversal. **No candidate was HTF-aligned.**
2. **Material adverse excursion on all three** (−6.8 / −18.6 / −36.2). Even the "best" (HR-0001) required
   surviving real early heat.
3. **Entries were late or at contra-points** — into congestion (HR-0002), above the swept low (HR-0002),
   or at a reversal (HR-0003).
4. **The order block never did clean work:** under-detected but real (HR-0001), fresh-but-breached
   (HR-0002), spent/traded-through (HR-0003).
5. **Session unconfirmed for all three** (Asia; corpus TZ unresolved — UTC+1 observed but not declared).

## Methodology lessons learned

- **HTF alignment is the strongest differentiator observed.** All three traded against HTF and none was
  trade-ready. A confirmed HTF-supportive setup is the single most valuable missing ingredient.
- **The machine methodology score did NOT rank by quality or outcome.** HR-0002 scored highest (0.69) yet
  landed at WATCH; HR-0001 scored lowest (0.375) yet was the best (LOW, MIXED outcome). **Confluence-coverage
  ≠ trade quality** — treat the score as coverage, not edge.
- **A spent/mitigated OB with price displacing *through* it is a strong disqualifier** (HR-0003).
- **A breached OB post-entry invalidates the "fresh OB" premise** (HR-0002).
- **Human structural reads can beat crude proxies** (HR-0001) — but only lift a label within caps; they do
  not create trade-readiness.

## What the machine proxies OVER-detected

- **HTF bias from the 15m fallback** (HR-0002 read "bullish — agrees LONG") that the **real 1h contradicted**
  — the insufficient-data 1h fallback over-called a supportive bias.
- **OB "presence"** where it didn't matter — flagged a fresh OB that failed (HR-0002) and an OB that was
  already spent (HR-0003).
- **Context candidates** (SWEEP_TO_CHOCH, BPR_TO_A) promoted by the detector that visual review knocked down
  to WATCH / REJECT.

## What the machine proxies UNDER-detected

- **A real indicator-drawn OB / FVG cluster** at HR-0001 (displacement 1.91× fell just under the 2.0× gate)
  — the crude ATR-gated proxy missed genuine structure. → recommend liquidity-sweep context + adaptive/lower
  displacement threshold (observation-only; **no invented numbers**).
- **The real HTF** — the 1h proxy was `NEUTRAL_OR_INSUFFICIENT_DATA` (needed ≥22 bars in an ~11.6h window),
  so it under-resolved a bias the screenshots later clarified.

## Is anything trade-ready?

**No.** Final labels: 1× SHADOW_CANDIDATE_LOW, 1× WATCH, 1× REJECT. **Zero shadow candidates survive as
trade-ready.** Evidence threshold **3 / 30 across ≥5 sessions — NOT MET** (and a REJECT does not count).
`NOT_INTEGRATION_READY` unchanged. Observation continues.
