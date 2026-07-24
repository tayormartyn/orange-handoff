# Sprint Day 2 — XAUUSD OHLC Import + Independent Outcome Matching

**Mode: DAY 2 OHLC IMPORT + OUTCOME MATCHING ONLY.** Observation-only. Date 2026-07-11.
Listener **PID 87988 running/untouched**. Deterministic OHLC matching is the authority; no AI extraction was
used for adjudication (this report's narrative is review-only commentary). No broker/cTrader/QST; no
permit/lease/order; gates `PAPER/PREVIEW/False/False`; no TradingView/Worker/R2/secret action; nothing
promoted to trade-ready. `NOT_INTEGRATION_READY` unchanged.

## 1. Import + validation

**Found in Downloads:** all four expected files —
`XAUUSD_1M_2026-06-30_1300_to_2026-07-01_0400_UTC.csv.csv`, `XAUUSD_1M_2026-07-07_1000_to_1600_UTC.csv.csv`,
`XAUUSD_1M_2026-07-08_1100_to_1630_UTC.csv.csv`, `XAUUSD_1M_2026-07-10_1130_to_2200_UTC.csv.csv`
(originals preserved, untouched).

**Finding: all four are byte-identical** (sha256
`a2b28119ba1827510629629eb4c3955e14a0b59890145f5463bed0498d295966`, 862,245 B each) — one full-chart
TradingView export saved four times. This is fine: the single export spans **2026-06-29 14:27 →
2026-07-10 20:54 UTC (12,551 bars)** and covers **all four required windows**. Copied once into
`stage_c_tooling/price_data/XAUUSD_1M_PEPPERSTONE_2026-06-29_to_2026-07-10_FULL_EXPORT.csv`
(hash verified after copy) rather than as four misleading duplicate window-named files.

**Validation** — format: TradingView raw export, columns `time,open,high,low,close,Bull Engulf,Bear
Engulf,Volume,CRSI`; `time` = Unix epoch seconds **UTC** (timezone unambiguous); OHLC parseable floats;
modal bar spacing 60 s (12,541 of 12,550 deltas) → **1m confirmed**; symbol per filename/values consistent
with **PEPPERSTONE:XAUUSD** (price levels match the Day-1 message levels throughout). The only gaps are the
standard daily futures-style maintenance break (~20:59→22:01 UTC each day) and the Jul-4/5 weekend — market
closures, not data defects.

| window | required (UTC) | bars present | coverage verdict |
|---|---|---|---|
| W1 / S1 | 06-30 13:00 → 07-01 04:00 | 839/901 (93.1%) | **SUFFICIENT** (only the 20:58→22:01 daily close missing) |
| W2 / S2 | 07-07 10:00 → 16:00 | 361/361 (100%) | **SUFFICIENT** |
| W3 / S3 | 07-08 11:00 → 16:30 | 331/331 (100%) | **SUFFICIENT** |
| W4 / S4 | 07-10 11:30 → 22:00 | 565/631 (89.5%), last bar 20:54 | **SUFFICIENT** (Friday close ~21:00; 20:55–20:59 tail absent, not material — no level in play then) |

## 2. Matching method (deterministic, SELL semantics)

Entry-zone touch = first bar after the signal message whose range intersects the zone. SL touch =
`bar.high ≥ SL`. TP touch = `bar.low ≤ TP`. MFE/MAE computed from zone-top and zone-bottom reference fills
**and** from the *achievable best fill* (highest traded price after zone touch, capped at zone top) — zone
tops that never traded are not credited. Pip convention: **1 pip = $0.10** (Farouk's usage is consistent
with this throughout; his "0.60 cents" = $0.60). Full numbers:
`stage_c_tooling/SPRINT_DAY2_XAU_OUTCOME_MATCHING_v1.json`.

## 3. Results

### XAU-S1-20260630 — **VERIFIED_WIN** (claim SUPPORTED; final magnitude overstated)

Entry zone 4060–4075 touched at signal bar 14:25Z (close 4059.15 — only the 4060–4062.43 bottom of the zone
ever traded; zone top never filled). **SL 4100 never touched — MAE $2.43** from zone bottom. Price fell to
**3970.20** (07-01 Asia). Every intermediate claim was achievable at its timestamp from real fills:
60p→max 89p · 100p→139p · 150p→176p · 180p→188p · 200p→238p. Final claim **"1000+ pips close fully"
(07-01 02:35Z): max achievable was 922 pips** (4062.43 best fill → 3970.20 low) — short of 1000 by ~78p
(~8% exaggeration; 1000+ required a 4075 fill that never traded on this feed). A ~900-pip winner is
nonetheless fully confirmed.

### XAU-S2-20260707 — **VERIFIED_LOSS** (claim SUPPORTED, remarkably precisely)

Entry zone 4144–4154 touched 11:29Z; zone top filled 11:58Z. **No TP level was ever reached** — best move
after entry was $14.68 from zone top (4139.32; TP1 4135 never traded, even after the stop). **SL 4180
touched 13:42Z** — one minute before the "Trade failed unfortunately" message (13:43:47Z). Max high
**4180.52 = $0.52 overshoot** vs his "stopped out by 0.60 cents" (Pepperstone-TV vs his broker feed
difference plausible). Loss claim independently confirmed in timing, level, and magnitude.

### XAU-S3-20260708 — **VERIFIED_WIN** (claim SUPPORTED; one interim figure marginal)

Entry zone 4072–4083 touched 12:14Z; zone top filled 12:47Z. **SL 4125 never touched — MAE $3.61** from zone
top (max high 4086.61). Price fell to **4021.65**. "200+ pips" (14:16Z): max achievable 314p — supported.
"500 pips" (14:46Z): max achievable **477p at that moment** (23p short); the 500p level *was* exceeded
~30 min later (613p max by the 15:32Z "full tp hit" message). "Full tp hit" is not checkable to a numeric
level (TP1 was never stated); the residual 10% target **4020 was missed by $1.65** inside the window. Net:
a large verified winner; interim figures directionally accurate with minor rounding-up.

### XAU-S4-20260710 — **PARTIAL** (claims SUPPORTED as far as they go; final outcome unadjudicable)

Entry zone 4102–4115 touched 12:48Z (signal 12:43Z, close 4099.58). **SL 4152 never touched** (max high
after entry 4120.18). "100 pips" (13:25Z): max achievable 108p — supported. "200 pips" (13:30Z): 213p —
supported. **TP2 4077 touched 14:33Z** (before SL; consistent with the conditional plan). TP3 4055 never
reached (min low 4072.64). Price then rallied back into the zone (zone top re-traded 16:30Z) into the
Friday close — with "sl to entry" management the residual would have scratched ~breakeven, but **no close
message exists in the capture**, so the final position outcome is unverifiable → PARTIAL, not
VERIFIED_WIN. The partial win claims themselves are supported.

## 4. Scoreboard (claimed vs independent)

| setup | claimed | independent | claim verdict |
|---|---|---|---|
| S1 06-30 | WIN "1000+ pips" | **VERIFIED_WIN**, max 922p achievable | SUPPORTED (final figure ~8% overstated) |
| S2 07-07 | LOSS "stopped out by 0.60c" | **VERIFIED_LOSS**, overshoot $0.52 | SUPPORTED (precise) |
| S3 07-08 | WIN "500 pips… full tp" | **VERIFIED_WIN**, 613p max | SUPPORTED (477p at the 500p claim moment; 4020 residual missed by $1.65) |
| S4 07-10 | WIN partial (100/200 pips) | **PARTIAL** (claims supported; TP2 hit; no close msg) | SUPPORTED as far as claimed |

**3 of 4 setups fully adjudicated; 0 CONTRADICTED.** Direction, SL behaviour, and loss admission all check
out; the pattern of exaggeration is mild and one-directional (rounding pips up ~5–10% at claim moments).
Evidence toward the sprint threshold: **4 XAU trades independently matched across 4 sessions** (target ≥10
across ≥5 sessions before any CONTINUE/REJECT decision).

## 5. Missing / unclear evidence

- S4 final close message (none captured — forward listener will catch future ones; claim window simply ended).
- S3 "full tp" has no numeric TP1 to check against; residual 4020 target missed by $1.65 in-window.
- S1/S3 screenshots still uncaptured binaries (backfillable via copied session, optional).
- Single price source (Pepperstone-TradingView export); his fills/feed may differ by ~$0.1–0.6 (S2 suggests ≤$0.1 level agreement).

## 6. Safety confirmation

Listener PID 87988 verified running before and after; never touched; no second listener. Downloads originals
preserved. No broker/QST/cTrader/execution; no permits/leases/orders; gates unchanged
(`PAPER/PREVIEW/False/False`); no TradingView/Worker/R2/secret action; no methodology scoring run (not needed
for this report); no demo/shadow execution; nothing promoted to trade-ready; AI output review-only (none used
for adjudication). `NOT_INTEGRATION_READY` unchanged.

## Next step

Sprint Day 3: authorised **bounded copied-session backward fetch of June gold-trades history**
(offset ~2026-06-01 → 2026-06-29, message-count-capped) to reconstruct the June ledger ("22 trades, 2
losers" claim) and extend the independently-matched sample toward ≥10 trades / ≥5 sessions; plus continue
forward daily capture (listener already running) and same-day OHLC export for any new XAU setup.
