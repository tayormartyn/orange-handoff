# Orange Pre-Mark Retrospective Report v0.1 (Lane 6)

**Mode: STEP 8 LANE-6 RETROSPECTIVE.** Observation-only, research-only. Date 2026-07-11.
Anti-leakage held throughout: the only pre-mark sources used are **his own advance-level posts** (message
timestamps precede everything computed); the mechanical SL (far zone edge ± $10) was documented before
computation; no post-dated evidence touched. Data: `orange_pre_mark_retrospective_v0_1.json` (also carries
the Model-B filter table). Labels emitted only from the allowed set. No execution surface.
Gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged.

## 1. Evidence availability — the honest headline

Of 34 matched setups, **31 have NO leak-free pre-post level evidence** in captured data
(`PRE_MARK_INSUFFICIENT_CONTEXT`): the TV alert lane only began Jul-7, and June intraday structure exists
only as OHLC — constructing OB/FVG/BPR levels from raw OHLC without his charts would be a new research
project, not a retrospective. **Three genuine advance-level posts existed** and were computed:

| pre-mark | zone (his own advance post) | vs his later setup | outcome |
|---|---|---|---|
| PM-45284 (Jun-29 12:43Z) | SELL 4070–4080 | **level-matched S1** (4060–4075, overlap 4070–4075) | **PRE_MARK_EXPIRED — never filled**: price never traded 4070+ again before/through S1's window. His own S1 zone-top 4075 also never traded — he market-filled ~4060. |
| PM-45097 (Jun-24 14:50Z) | SELL 4070–4080 (re-entry plan) | **level-matched J28** (4078–4092, overlap) | Filled 4070 at Jun-26 13:56Z — **2 minutes before his J28 post** — then **stopped −200p at 14:16Z** by the 4096.04 adverse spike (mechanical SL 4090; his actual posted SL was 4120, but that knowledge is post-dated and unusable). MFE before stop: 31p. |
| PM-44877 (Jun-18 22:13Z) | SELL 4250–4260 | no matching setup (Jun-19 was a BUY far below) | **PRE_MARK_EXPIRED — never touched.** |

## 2. Lane-6 aggregate

- sufficient pre-post evidence: **3 / 34** · PRE_MARK_INSUFFICIENT_CONTEXT: 31
- level-match rate vs his later posted zones: **2 of 3** (encouraging for the "his levels are
  constructible" hypothesis — n far too small)
- fills: 1 · profitable fills: **0** · expired unfilled: 2 · hypothetical pips: **−200**
- **Lane 6 vs Lane 4 uplift: NEGATIVE / not demonstrated** — the single filled pre-mark lost while
  lane-4 followers of the same campaign made +25 and Farouk's own campaign won.

## 3. What the n=3 actually teaches (marked honestly)

1. **Level anticipation looks feasible** (2/3 zone overlap with his later posts — including one fill 2
   minutes before his post). WEAK evidence, right direction.
2. **Risk parameterisation is the unsolved half**: the pre-mark died to a $10 mechanical stop where his
   posted stop was $40+ wide. Getting the level right without his SL width converts anticipation into
   losses. Any future lane-6 iteration must derive stop width from pre-post evidence too (e.g. his
   historical SL-width distribution — itself learnable from the ledger without leakage).
3. **Early fills eat the pre-post adverse move** (the exact MAE his own timing avoids) — consistent with
   every other finding about his private edge being timing + management, not just levels.

**Lane-6 classification: NEEDS_FORWARD_EVIDENCE** (unchanged from design; now with its first 3 data
points). Forward Cycle 002+ may write `PRE_MARK_CANDIDATE` records at alert-context time, which is where
the real test lives — the TV alert lane provides exactly the pre-post structure evidence June lacked.

## 4. Conclusion strength

- "Orange can mark his levels in advance": **WEAK** (2/3, n=3).
- "Pre-marking improves expectancy": **NOT DEMONSTRATED** (0/1 filled profitably; −200p).
- "Stop-width, not level, is the binding constraint": **MODERATE** (deterministic on the one fill;
  consistent with fill-divergence evidence).

## 5. Safety confirmation

Research-only; leak-free by construction; labels restricted to the allowed five; no
broker/QST/cTrader/nano/copy/demo/live execution; no permits/leases/orders; no limit orders or order
intent; gates unchanged; listener PID 87988 running/untouched; no TradingView/Worker/R2/secret action.
`NOT_INTEGRATION_READY` unchanged.

## Next step

Forward lane-6: PRE_MARK_CANDIDATE records from alert-context (Jul-7+ capture), with pre-post-derived stop
widths; retrospective lane-6 against the July alert archive as a follow-up study once forward cycles are
running.
