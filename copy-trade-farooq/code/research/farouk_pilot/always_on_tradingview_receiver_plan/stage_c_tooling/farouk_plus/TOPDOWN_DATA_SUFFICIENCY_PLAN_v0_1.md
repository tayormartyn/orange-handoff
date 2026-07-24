# Top-Down Data-Sufficiency Plan v0.1 — corrected (2026-07-15)

Corrects the earlier "one 07-11→07-15 1m export" claim. Four days of 1m → four Daily candles is NOT
D1 top-down. Provider fixed = **PEPPERSTONE:XAUUSD**, UTC. Observation/research only.

## Task 1 — Existing PEPPERSTONE:XAUUSD inventory (all TradingView epoch-UTC exports; causal, revision-safe)
| TF | best coverage (file) | earliest | latest | completeness | gaps | causal/rev-safe |
|---|---|---|---|---|---|---|
| **H1 (60M)** | `price_data/XAUUSD_60M…` + `Downloads/PEPPERSTONE_XAUUSD, 60.csv` (1996 bars) | 2026-03-10 16:00Z | **2026-07-10 20:00Z** | ~4 months contiguous | none intra; **stops 07-10** | yes |
| **M15** | `price_data/XAUUSD_15M…` (8057) | 2026-03-09 20:15Z | **2026-07-10 20:45Z** | ~4 months | stops 07-10 | yes |
| **M5** | `price_data/XAUUSD_5M…FULL_EXPORT` (10842) | 2026-05-18 | **2026-07-10 20:50Z** | ~8 weeks | stops 07-10 | yes |
| **M1** | `price_data/XAUUSD_1M_…06-21_to_07-10` (20423) + June partials + 07-08/09/10 partials | 2026-06-21 | **2026-07-10 20:54Z** | contiguous 06-21→07-10 | **07-11→07-14 missing** except… | yes |
| **M1 (campaign day)** | `price_data/…2026-07-14_0730_to_1629_PARTIAL` (540) | 2026-07-14 07:30Z | 2026-07-14 16:29Z | 9h only | **before 07:30 & after 16:29 missing** | yes |
| **D1** | *(none native)* — resample from H1 only | (03-10) | (07-10) | **~4 months only** | **12–18mo history absent** | n/a |
| **H4** | *(none native)* — resample from H1 | (03-10) | (07-10) | ~4 months | stops 07-10 | n/a |

Other gold assets present but NOT price sources: FP-CAMPAIGN-00x-input.zip (campaign text packs),
Trading Journal xlsx, dukascopy_adapter (delayed non-Pepperstone, unused). No canonical OHLC store.

## Task 2 — Minimum defensible history per timeframe (for the 14 July context)
| TF | purpose | default lookback | HAVE? | verdict |
|---|---|---|---|---|
| D1 | major swings, bias, external liquidity, premium/discount, daily OB, mitigation history | 12–18 mo | ~4 mo (resampled) | **INSUFFICIENT — native D1 18-mo needed** |
| H4 | refinement, displacement, FVGs, fresh/mitigated, competing zones | 3–6 mo | 4 mo (from H1) + gap 07-11→07-14 | **PARTIAL — covered once the recent 1m tail lands** |
| H1 | internal/major structure, BOS/CHoCH, level construction, session | 4–8 wk | through 07-10 | **PARTIAL — need 07-11→07-14 tail** |
| M15 | sweep/trigger/confirmation, LTF rejection | 1–2 wk | through 07-10 | **PARTIAL — need 07-11→07-14 tail** |
| M5 | sweep/trigger/entry-confirm | 3–5 d | 07-09/10 have, 07-11→14 gap | **PARTIAL — need tail** |
| M1 | actionability/fills/management/outcome | campaign day + lead-in + follow-through | 07-14 07:30–16:29 only | **PARTIAL — need lead-in + follow-through** |

## Task 3 — Export strategy = **C. Hybrid** (native D1 + one recent 1m; NOT a giant 1m history)
- Native **D1** carries 18 months in ~390 bars — the efficient way to get daily structure; resampling 1m
  for that is absurd.
- A single recent **1m** for 2026-07-11→07-15 (~5–6k bars) resamples cleanly to **M5/M15/H1/H4** for the
  immediate context — so no separate M5/M15/H1/H4 recent exports are needed.
- Existing H1 (03-10→07-10) already supplies the **H4 3–6-month** context; existing M15/M5 supply their
  older context. So only the **two gaps** need filling.

## Task 4 — Exact smallest export pack for Martyn (**2 files**)
**File 1 — Daily history**
- Symbol: `PEPPERSTONE:XAUUSD` · Timeframe: **1D**
- Start: **2025-01-13** · End: **2026-07-15** (≈18 months)
- Filename: `XAUUSD_1D_PEPPERSTONE_2025-01-13_to_2026-07-15.csv`
- May contain later bars? **Yes** (D1 history; the causal split happens at replay time, not export).

**File 2 — Recent intraday context + campaign day**
- Symbol: `PEPPERSTONE:XAUUSD` · Timeframe: **1 minute**
- Start: **2026-07-11 00:00 UTC** · End: **2026-07-15 00:00 UTC**
- Filename: `XAUUSD_1M_PEPPERSTONE_2026-07-11_to_2026-07-15_UTC.csv`
- May contain later bars? **Yes** — export the whole window; the replay firewall (Task 5) splits it at
  each signal time, so post-signal bars are used only for adjudication.

**Click steps (both files):** open a `PEPPERSTONE:XAUUSD` chart → set the timeframe (1D, then 1m) → set the
chart timezone to **UTC** (right-click axis → Timezone → UTC) → scroll/zoom so the full date range is
loaded (drag left edge back to the start date) → **⋯ / chart menu → Export chart data… → CSV → Export** →
save with the filename above → drop both into `Downloads`. Then tell me "export pack ready".

## Task 5 — Causal / pre-signal firewall (replay design)
- **PRE_SIGNAL_RESEARCH_DATA** = every bar with `ts < signal_ts` (F001 2026-07-14T08:38:06Z; F002
  13:26:21Z) across D1/H4/H1/M15/M5/M1. The forming D1/H4/H1 candle at the signal is EXCLUDED (only
  completed prior candles); LTF uses 1m strictly before the signal.
- **POST_SIGNAL_OUTCOME_DATA** = bars with `ts >= signal_ts`, used ONLY by the deterministic adjudicator
  (fills/management/outcome) — never by the top-down blind hypothesis.
- Enforcement reuses the existing causal guard (`smc_features._causal(bars, signal_ts)` already filters
  `ts < signal_ts`) and the chronological firewall; the auto-hypothesis generator only ever reads a frozen
  PRE_TRADE_SNAPSHOT. Post-signal leakage is structurally impossible in the blind path.

## Task 6 — BTC video classification (confirmed)
The .mov (`FP-CAMPAIGN-BREAKDOWN-20260714`, ~90% BTC) is tagged **BTC_RETROSPECTIVE_METHODOLOGY_EVIDENCE**
(in addition to RETROSPECTIVE_EXPLANATION). It MAY seed a future BTC evidence corpus but MUST NOT: modify
XAU methodology rules, enter Gold expectancy, activate a BTC Constitution, or create BTC trading rules from
one video. No BTC rule/constitution/expectancy exists or is created here.

## Task 7 — Deterministic top-down replay to run AFTER import (spec; build later)
1. **D1 context** (File 1, completed daily candles < signal): major swings (fractal), bias
   (BOS/CHoCH on D1 closes), external liquidity (prior D/W highs-lows), premium/discount (range 50%),
   daily OB/FVG, prior mitigation — all `ts < signal`, forming day excluded.
2. **H4 refinement** (existing H1→H4 resample + File 2): displacement, fresh vs mitigated FVG/OB,
   competing candidate zones in the D1-biased direction.
3. **H1 ranking**: internal/major structure, BOS/CHoCH, precise zone boundaries, session — rank candidate
   zones by the existing deterministic features (freshness, confluence count); **ranking weights UNKNOWN →
   fail closed** (emit ranked candidates + an explicit "ranking unsupported" flag, never a fabricated score).
4. **M15/M5 trigger**: sweep (DR-204), 1h-close/confirmation, LTF rejection.
5. **Primary + alternative zones** emitted with evidence, all causal.
6. **Compare vs Farouk's published zone** (F001 4007–4019 / F002 4084–4094): MATCH / NEAR / DISJOINT +
   distance; this is the ranking-function test.
7. **Explicit UNKNOWN** wherever ranking is unsupported — research-only; cannot touch the strict follower.

## Safety
Planning + audit only; no build. Live processes (13172/29868/37656/39508) untouched; Constitution/scorers/
pre-marks/gates frozen; NOT_INTEGRATION_READY unchanged; no broker/demo/execution/smart-entry added.
