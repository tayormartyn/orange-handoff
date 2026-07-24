# Human Review Result — HR-0001

**Candidate:** ALIGNED_CHOCH_TO_A-0000 · anchor 2026-07-09T04:12:01Z · hint LONG.
**Mode:** HR-0001 human visual review. **Observation-only; candidate-only; NOT trade-ready.**
`NOT_INTEGRATION_READY` unchanged.

## FINAL label: **SHADOW_CANDIDATE_LOW** (reverted from provisional MEDIUM) — **not trade-ready**
## Review status: **REVIEWED** — closed; all four valid screenshots present (1m/3m/true-15m/Jul-9 1h)

> **Update (corrected screenshots supplied):** the true 15m (TF=15) and correct Jul-9 1h (TF=60) were
> validated. The 1h confirms a **multi-day downtrend into the anchor** → **HTF opposes the LONG
> (counter-trend)**. Combined with the **MIXED** outcome, ungraded setup and n=1, the provisional
> `SHADOW_CANDIDATE_MEDIUM` **reverts to `SHADOW_CANDIDATE_LOW`** (exactly the contingency flagged
> earlier). Observation-only — **not trade-ready, not demo-ready, not permission to trade.**

## Screenshots reviewed

| File | Actual content | Covers anchor? |
|---|---|---|
| HR-0001_1m.png | 1m, ~00:30–08:30 UTC (chart shows 01:30–09:30 @ UTC+1) | ✅ yes |
| HR-0001_3m.png | 3m, Jul 8 ~20:00 → Jul 9 ~18:00 UTC | ✅ yes |
| HR-0001_15m.png | **true 15m** (TF=15), Jul 8–14 (corrected) | ✅ yes |
| HR-0001_1h.png | **1h** (TF=60), late-Jun → late-Jul, crosshair Jul 09 04:00 (corrected) | ✅ yes |

**Chart timezone = UTC+1** (footer "15:56:47 UTC+1"). The OHLC export uses Unix epochs (true UTC), so the
04:12Z anchor / entry 4063.96 remain correct; only the on-screen clock is +1h.

## What the charts show at the anchor

With the UTC+1 offset applied, the CHoCH UP (04:00Z) and A LONG (04:12Z) coincide with a **sweep of the
Asia Low** followed by an indicator-drawn **order block + BPR + FVG + CHoCH** cluster. Price dipped to
sweep the low just after the anchor (the ~−6.76 early adverse heat), then reversed and ground higher
(+12.07 @60m, **+25.56 close / +35.49 peak @120m**). This is a plausible **Farouk POI / OB sweep-reversal**
shape — not pure alert noise.

## Checklist answers

1. **Real structure shift?** Yes — CHoCH at Asia Low within a sweep-reversal. `CONFIRMED`.
2. **CHoCH UP meaningful?** Yes, at a real level (Asia Low), not mid-range.
3. **Displacement obvious or weak?** Moderate — created FVGs (indicator drew them); machine ratio 1.91×
   sat just under the 2.0× proxy threshold, so the proxy **missed** it. `CONFIRMED` (moderate).
4. **Meaningful FVG?** Yes — indicator FVGs drove the rally. `CONFIRMED`.
5. **Credible order block?** Yes — indicator OB at the sweep low. **Machine proxy found none — human
   review overturns** (crude displacement gate under-detected). `CONFIRMED_FRESH`.
6. **OB absent / unclear / mitigated?** Present and fresh at entry (not the spent case seen in HR-0003).
7. **Direction contradicted?** At the anchor, no contradictory A-cluster (`ABSENT`). **HTF unconfirmed** —
   the 1h screenshot is the wrong date range; the machine 15m proxy read bearish (unverified).
8. **Early adverse excursion too large?** No — ~−6.76 is consistent with a sweep of Asia Low before the
   reversal; not excessive for a sweep-reversal.
9. **Later move setup-driven or delayed/noisy?** **Setup-driven** — the rally followed the sweep + OB/FVG,
   though it was a moderate grind rather than a violent impulse.
10. **Farouk methodology or noise?** Looks like a genuine methodology setup (Asia-Low sweep → OB/FVG →
    CHoCH → continuation), **not** ANY_ALERT noise.

## Corrected 15m + 1h review (the deciding evidence)

- **True 15m (TF=15):** confirms the anchor sits at a clean **Asia-Low sweep-reversal** with an
  OB/BPR/FVG/CHoCH cluster — the anchor structure is real (as suspected from the 1m/3m).
- **Correct Jul-9 1h (TF=60):** shows a **multi-day downtrend into the anchor** (~4200 on Jul 3 → ~4050 on
  Jul 9). So the **HTF bias is BEARISH and OPPOSES the LONG** — the entry was **counter-trend**. This
  matches the machine's bearish HTF proxy.

## Why LOW (reverted from provisional MEDIUM)

- **HTF now confirmed OPPOSING** the LONG (counter-trend on the 1h) — a strong methodology negative
  (strong-OB wants trend alignment).
- **Outcome only MIXED** — favourable only after real adverse heat; not a clean result.
- **Grade absent** (ungraded, not A+); **n=1**; session policy still corpus-unresolved (UTC+1 observed).
- Per decision rules: HTF-against + not-favourable outcome cap the label; the confirmed anchor structure
  keeps it a genuine shadow candidate but at **`SHADOW_CANDIDATE_LOW`** — observation-only.

## Value added by the human review

The machine pipeline (crude ATR-gated proxies) **under-detected** this setup: no OB proxy, sub-threshold
displacement. The visual review confirms an indicator-drawn OB/FVG/BPR/CHoCH sweep-reversal at the anchor.
**Lesson for the tooling:** the OB/displacement proxies should incorporate liquidity-sweep context and a
lower/adaptive displacement threshold (a future, observation-only improvement — do not invent numbers).
Also: **chart tz = UTC+1** is a concrete data point toward resolving the session-timezone blocker (still
corpus-conflicted; not declared resolved).

## Standing missing evidence (non-blocking; noted for the shadow record)

- **Grade** (ungraded); **Telegram/Discord** confirmation (not checked); **larger sample** (n=1).
- Optional: Martyn countersign of the OB/FVG read on a marked-up screenshot.

## Trade-ready? — **NO**

Final `SHADOW_CANDIDATE_LOW` is observation-only — **not trade-ready, not demo-ready, not permission to
trade.** No order/entry/size/broker anywhere. Demo discussion remains blocked (threshold 3/30 — NOT MET).
Review **closed (REVIEWED)**.

## Safety confirmations

- Candidate-only; execution / broker / qst / order_intent / risk_sizing = false.
- No TradingView alert touched; no broker/cTrader/QST; no deploy; Worker pure logging-only.
- **`NOT_INTEGRATION_READY` unchanged.**
