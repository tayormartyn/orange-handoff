# Sprint Day 4 — June XAUUSD OHLC Import + Deterministic Outcome Matching

**Mode: DAY 4 JUNE OUTCOME MATCHING ONLY.** Observation-only. Date 2026-07-11.
Listener **PID 87988 running/untouched**. Deterministic OHLC matching is the authority; no AI output used
for adjudication. No broker/cTrader/QST; no permit/lease/order; gates `PAPER/PREVIEW/False/False`; no
TradingView/Worker/R2/secret action; nothing promoted to trade-ready. `NOT_INTEGRATION_READY` unchanged.

## 1. Import + validation — CRITICAL COVERAGE FINDING

Both Downloads files (`XAUUSD_1M_2026-06-01_to_2026-06-15.csv.csv`,
`XAUUSD_1M_2026-06-15_to_2026-06-30.csv.csv`) are **byte-identical** (sha256 `2e0d565d…b53af`,
1,401,508 B) — one TradingView full-chart export saved twice, same pattern as Day 2. Format valid
(TradingView raw export, epoch-seconds UTC, 1m confirmed — 20,408 of 20,421 deltas = 60 s; only market
closes as gaps; Pepperstone-consistent prices). Copied once to
`price_data/XAUUSD_1M_PEPPERSTONE_2026-06-21_to_2026-07-10_FULL_EXPORT.csv` (hash verified; originals
preserved).

**BUT the export spans only 2026-06-21 22:01 → 2026-07-10 20:54 (20,423 bars).** TradingView exports only
the bars currently *loaded* in the chart (~20k cap) — the chart wasn't scrolled back far enough, so
**June 1–21 is absent**. Coverage verdict per ledger day:

| days | setups | coverage |
|---|---|---|
| Jun 23, 24, 25, 26, 29 | J24–J30 (7) | **FULL** (00:00–23:59 each; Jun-26 to 20:54) |
| Jun 2, 3, 4, 11, 15, 16, 17, 18, 19 | J01–J23 (23) | **NONE** — INSUFFICIENT_DATA |

## 2. Results (matcher: Day-2 semantics generalised to LONG+SHORT; pip = $0.10; achievable-fill logic)

**Statuses: 4 VERIFIED_WIN · 2 PARTIAL · 0 VERIFIED_LOSS · 0 CONTRADICTED (setup-level) · 24 INSUFFICIENT_DATA**
(23 uncovered + J24 which has no numeric entry to test). Full numbers:
`SPRINT_DAY4_JUNE_XAU_OUTCOME_MATCHING_v1.json`.

| setup | claim | independent result |
|---|---|---|
| J25 06-23 SELL 4138-55/SL4180 | 170p win | **VERIFIED_WIN** — SL never touched, TP 4130 hit 14:27Z, MFE 320p; claims supported ("50 pips" at 13:57 predates zone touch but matches a market fill at post time) |
| J26 06-24 SELL 4030-45/SL4130 | 650p win | **VERIFIED_WIN** — SL never touched, MFE **859p**; every claim incl. 650p supported (755p achievable at that moment) |
| J27 06-25 BUY 4006-16/SL3970 | 300p win | **VERIFIED_WIN** — SL never touched (MAE $0.91), TP1/2/3 hit, 300p supported (345p achievable) |
| J28 06-26 SELL 4078-92/SL4120 | scratch (BE stops) | **PARTIAL** — hard SL never touched, MFE 206p; "100 pips" matches a bottom-edge market fill (~96p); his BE-scratch outcome consistent, not independently provable |
| J29 06-26 SELL 4084-94/SL4120 | 150p win | **VERIFIED_WIN** — SL never touched, MFE 184p, 90/100/150p all supported; the "missed by 1 pip" retrace matches the 4096.04 adverse extreme |
| J30 06-29 BUY 4035-45/SL4010 | 240p win | **PARTIAL, magnitude CONTRADICTED** — "tp1 hit" 09:04 true for a market fill; but **170/200/240-pip claims overstated 33–56%** (max achievable 128p/128p/175p at those timestamps); runner BE-stopped ~13:59; **hard SL 4010 WAS touched 14:11–14:15** (low 4000.66) after his exit — holders of the original SL were stopped |
| J24 06-23 morning | 170p win | **INSUFFICIENT_DATA** — entry message never captured; price action (4140→~4123) directionally consistent but unverifiable |

## 3. "22 trades, 2 losers" after Day 4

**Still CONTRADICTED — unchanged from Day 3, but now nuanced:**

- The loss-count contradiction rests on his own posts (4 explicit admitted losses on Jun-02/04/15/19). **All
  4 admitted losses fall in the uncovered Jun-1–21 window**, so none could be deterministically confirmed or
  refuted today.
- The covered final week (Jun-23→29) claims "zero losses" (45239) — deterministic matching **agrees**:
  4 wins + 2 partials, 0 losses in that window.
- **New finding:** the sprint's first hard magnitude contradiction (J30: 240p claimed vs 175p max
  achievable), beyond Day 2's mild S1 overstatement (1000+p vs 922p). Pattern: direction/win-loss honesty
  holds; headline pip numbers inflate under momentum.

**Re-entry counting does NOT change the conclusion:** covered window = 7 strict setups / 6 grouped
campaigns (J28+J29 = one Jun-26 campaign); zero losses either way. For June overall, strict = 30 setups /
33 executions; grouped-campaign ≈ 24 — the "22 trades" figure stays plausible only under grouped counting,
and the "2 losers" figure stays understated (≥4 self-admitted) under every convention.

## 4. Cumulative sprint scoreboard (Days 2+4)

**10 XAU trades independently outcome-matched across 9 sessions** (Jun 23/24/25/26/29, Jun 30, Jul 7/8/10):
**6 VERIFIED_WIN, 1 VERIFIED_LOSS, 3 PARTIAL, 0 setup-level CONTRADICTED**; 2 magnitude issues (S1 mild,
J30 material). **The ≥10-trades / ≥5-sessions minimum-evidence threshold for an early sprint decision is
now MET** — though June 1–21 (23 setups incl. all 4 admitted losses) remains unmatched, which matters for
loss-rate estimation.

## 5. Missing / unclear evidence

- **June 1–21 OHLC** — the blocker. Export instructions for Martyn: in TradingView, **scroll/zoom the chart
  back until bars from June 1 are loaded** (the export only contains loaded bars, ~20k cap ≈ 3 trading
  weeks of 1m). Two exports: load Jun-01→Jun-11 and export (`XAUUSD_1M_2026-06-01_to_2026-06-11.csv`), then
  Jun-11→Jun-21 (`XAUUSD_1M_2026-06-11_to_2026-06-21.csv`). Alternative: one 5m export covering all June
  (~6k bars) would allow coarse-grained matching of the 23 remaining setups at reduced precision.
- J24 entry message (not in gold-trades; likely posted elsewhere or deleted).
- J28's scratch outcome and all "SL-to-entry" results depend on his private stop placement — only
  consistency, not proof, is possible.
- Single price source (Pepperstone-TV); fills may differ ~$0.1–0.6.

## 6. Safety confirmation

Listener PID 87988 verified running before and after (start 2026-07-10 21:54:45 unchanged). Downloads
originals preserved. No broker/QST/cTrader/execution; no permits/leases/orders; gates unchanged; no
TradingView-alert/Worker/R2/secret action; no methodology scoring; no demo/shadow execution; nothing
trade-ready. AI output not used for adjudication (deterministic matcher only; Day-3 ledger extractions were
already validator-stamped). `NOT_INTEGRATION_READY` unchanged.

## Next step

Two options, Martyn's call: (a) export **June 1–21 1m OHLC** (two chunks as above) → Day 5 matches the
remaining 23 setups, deterministically testing all 4 admitted losses; or (b) since the ≥10/≥5 threshold is
met, proceed to the **sprint interim decision report** (CONTINUE / COLLECT_MORE / REJECT /
DEMO_READINESS_RESEARCH_ONLY) on current evidence, flagging the June-1–21 gap. Recommended: (a) then (b) —
the loss-rate estimate is the weakest number and the missing window contains every admitted loss.
