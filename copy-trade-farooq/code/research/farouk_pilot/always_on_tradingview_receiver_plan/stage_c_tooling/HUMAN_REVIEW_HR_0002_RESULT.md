# Human Review Result — HR-0002

**Candidate:** SWEEP_TO_CHOCH_CONTEXT-0000 · anchor 2026-07-09T00:03:01Z · hint LONG.
**Mode:** HR-0002 human visual review. **Observation-only; candidate-only; NOT trade-ready.**
`NOT_INTEGRATION_READY` unchanged.

## FINAL label: **WATCH** (reverted down from provisional SHADOW_CANDIDATE_LOW) — **not trade-ready**
## Review status: **REVIEWED** — closed; all four screenshots valid and on the correct Jul 8→9 session

> **Corrected screenshots validated:** the re-captured **1m** (midnight axis "Thu 09 Jul '26 00:04",
> price ~4080, TF=1) and **3m** (window ~4020–4140, anchor region ~4050–4085, swept low ~4030, TF=3) are
> now the **correct Jul 8→9 overnight** — replacing the earlier wrong-night (Jul 9→10, ~4122) versions. The
> **15m** and **1h** were already valid and were **not** replaced.

## Screenshot validation (final)

| File | Content | Valid TF | Correct window? |
|---|---|---|---|
| HR-0002_1m.png | TF=1, "**Thu 09 Jul '26 00:04**", ~4050–4090 | ✅ | ✅ Jul 8→9 (corrected) |
| HR-0002_3m.png | TF=3, ~4020–4140, anchor ~4050–4085, swept low ~4030 | ✅ | ✅ Jul 8→9 (corrected) |
| HR-0002_15m.png | TF=15, ~Jul 8→14 | ✅ | ✅ covers anchor |
| HR-0002_1h.png | TF=60, UTC+1, ~Jul 3→9 | ✅ | ✅ covers Jul 9 |

## What the corrected charts show at the anchor

- **3m:** a real **sweep of the Jul 8 late-session low (~4030)** → reversal/rally to ~4090, then a **choppy
  range 4070–4085** where the anchor sits. FVG/BPR/OB boxes are drawn around the low and the range.
- **1m:** confirms the date/price and the anchor micro-structure — a minor sweep (ST ~4065) and CHoCH-up
  near 4076–4080, a brief push to ~4089, then a roll-over and decline to ~4050–4062 by ~04:00 local.
- The anchor LONG (entry 4080.83) is taken **late** — ~45 pts above the major swept low, **into congestion**,
  on a **minor CHoCH within a chop**, with a **counter-HTF** backdrop.

## Outcome (real XAUUSD 1m, descriptive price stats — NOT PnL)

| Horizon | MFE | MAE | close Δ |
|---|---|---|---|
| 15m | +8.87 | −3.50 | **+3.94** |
| 30m | +8.87 | −6.87 | −2.29 |
| 60m | +8.87 | −14.28 | −12.81 |
| 120m | +8.87 | **−18.57** | −5.38 |

Brief early pop (peak MFE +8.87 by 15m), then rolled over, **breached the OB zone (low ≈ 4062 < 4076–4077)**
and ran adverse to −18.57, closing −5.38 at 120m. (Price rose again later on Jul 9 daytime, beyond the
tracked window.)

## Per-factor findings (visual, final)

1. **Sweep real or noise?** **Real (moderate)** — genuine sweep of the ~4030 low with reversal; but the
   anchor entry is far above it (late).
2. **CHoCH meaningful?** **Weak** — a CHoCH-up prints, but inside a cluster of repeated CHoCH up/down in a
   4070–4085 chop; low conviction.
3. **OB credible / fresh or spent?** **Present but breached/failed** — the "fresh" OB (4076.28–4076.89) sits
   in congestion and was **traded through** on the fade (low ≈ 4062). Not a respected OB.
4. **Displacement obvious?** **Moderate** — strong displacement was the earlier 4030→4090 rally, not the
   anchor CHoCH itself.
5. **Meaningful FVG/BPR?** **Present but low specificity** — many overlapping boxes.
6. **HTF/session support or oppose the LONG?** **Opposes / does not support** — valid 1h shows a multi-day
   downtrend into Jul 9. Session ASIA; tz UTC+1 confirmed but corpus-unresolved → `SESSION_UNCONFIRMED`.
7. **Why did the outcome fade?** A **late, counter-HTF long into chop** on a **minor CHoCH** with a
   **weak/breached OB**: it popped +8.87 then rolled over, breached the OB, and faded to −18.57 MAE. The
   implied support failed and HTF was against it.
8. **Genuinely Farouk-like or failed weak-context?** **Failed weak-context** — methodology elements exist
   (sweep, FVG/BPR, OB) but assembled weakly and against HTF; it failed within the window.

## Decision

- **Final label: `WATCH`** — reverted one notch from `SHADOW_CANDIDATE_LOW`. Structure exists (more than
  `CONTEXT_ONLY` noise, not a hard `REJECT`), but counter-HTF + breached OB + minor CHoCH + unfavourable
  outcome place it **below a shadow candidate**.
- **Status: `REVIEWED`** — closed.

## Trade-ready? — **NO**

Observation-only — not trade-ready, not demo-ready, not permission to trade. Demo discussion blocked
(threshold 3/30 — NOT MET). No order/entry/size/broker/account anywhere.

## Safety confirmations

- Candidate-only; execution / broker / qst / order_intent / risk_sizing = false.
- No TradingView alert touched; no broker/cTrader/QST; no deploy; Worker/R2 not touched; H1/H2 untouched;
  Telegram PREVIEW listener PID 16608 untouched and still running.
- **`NOT_INTEGRATION_READY` unchanged.**
