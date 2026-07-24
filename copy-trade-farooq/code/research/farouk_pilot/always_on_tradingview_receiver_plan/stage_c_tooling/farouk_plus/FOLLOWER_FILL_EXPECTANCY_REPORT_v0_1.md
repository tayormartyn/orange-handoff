# Follower-Fill Expectancy Report v0.1 (Step 8)

**Mode: FOLLOWER EXPECTANCY TABLE ONLY. Observation-only / review-only / analytic-only.** Deterministic
OHLC facts (Day-2/4/5 matchers + J24 rematch) are the only price authority; no new OHLC walk; no AI call;
no execution surface (output passed the ai_review forbidden-key sweep). Units: pips = 0.1 USD.
`NOT_INTEGRATION_READY` unchanged. Date 2026-07-11.

**Central question:** *is the edge capturable from the posted information alone?*

## Method (lane-4 deterministic approximation — full spec in `build_follower_expectancy_table_v0_1.py`)

Follower fill = **posted-zone MEDIAN** (zone mid; Day-2 top/bottom MFEs averaged; Day-4/5 best-fill rows
adjusted down by the zone halfwidth). Management applied literally: SL hit before TP → full loss from median
fill; TP1 touched → 50% banked at TP1, runner **scratched to 0 when "sl to entry" was posted** (per R6
J24/J30 modelling), else runner to TP2 / last claim-snapshot achievable; manual-close setups → last
claim-snapshot achievable capped at median MFE. Farouk private fills are used **only in the lane-1
comparison, never as follower fills**; the single exception-flagged case is **J24 (POST_TIME_PROXY — no
entry post ever existed)**.

## Aggregate results (34 matched sprint setups)

| metric | value |
|---|---|
| setups analysed | **34** (30 June + 4 July) |
| with follower expectancy computable | **32** (UNAVAILABLE: J10 — loss row lacks zone detail; J11 — no zone posted) |
| follower outcomes | **22 WIN / 7 PARTIAL / 1 SCRATCH (J24) / 2 LOSS (J17 −165p, S2 −310p)** |
| mean follower achievable | **+132.3p** |
| median follower achievable | **+115.5p** |
| total follower achievable | **+4,234.5p** |
| total divergence vs headline claims (22 claim-cases) | **+699p claimed that followers could NOT capture** |
| inflation_ratio > 1.25 | **6 setups** (J27 2.22, J30 2.13, S1 2.06, S3 1.79, J28 1.47, S4 1.27) |

### Three-lane comparison

| lane | picture |
|---|---|
| raw Farouk verified (deterministic claim-status) | 21 W / 3 L / 10 PARTIAL — strongly positive |
| headline claims | inflated: +699p of claimed pips (across 22 cases) not capturable from posted info; 6 setups >1.25× |
| realistic follower (this table, lane 4) | **22 W / 7 P / 1 S / 2 L, median +115.5p — still clearly positive** |

### Biggest divergence cases (claim − follower)

`S1 −513.5p (1000+ claimed / 486.5 follower)` · `S3 −220.5p` · `J24 −170p (his +170 vs follower scratch 0
— the defining case: no entry post + literal sl-to-entry cost the entire move)` · `J27 −165p` ·
`J30 −127.5p` · `S4 −42.5p`.

### Known Farouk-fill vs follower (lane 1 vs lane 4)

- **J24:** his +170p (fill 4132.02, widgets) vs follower **0p scratch** — divergence −170p.
- **J30:** his true 240p (fill 4027.37, below the posted zone) vs follower **112.5p** — divergence −127.5p.
- **J11:** his realised 629p vs claim 800p (ratio 1.27); follower post-time ≈ his fill (no zone posted;
  UNAVAILABLE in the deterministic table).

## Is the edge capturable from posted information alone?

**YES — MODERATE confidence.** After stripping claim inflation, applying median-zone fills, and modelling
literal sl-to-entry scratches, follower expectancy remains strongly positive (median +115.5p, 22/32 wins,
only 2 full losses). It is **MODERATE, not STRONG**, because: (a) June rows are mostly 5m-precision with a
halfwidth adjustment, not tick fills; (b) the runner model is an approximation (scratch-assumed where
sl-to-entry was posted — conservative on winners, but J24 shows it can also delete a whole move); (c) the
usable set excludes **J10, a VERIFIED_LOSS** (no zone detail) — including it would subtract one more loss
(~−200p order) without changing the sign; (d) n=32, one-month, one poster. **Not trade-ready; review-only.**

## Which rules protect follower expectancy most?

| rule | effect on mean follower pips | verdict |
|---|---|---|
| **R2b first-attempt-only** | 132.3 → **142.9** (+10.6; removes losses J08/J10/J17 at cost of 3 modest winners) | **MODERATE protector — largest single improvement** |
| **R4b no-entries-≥15:30Z** | 132.3 → **141.9** (+9.6; removes J03/J17 losses, cost J06 ~53p) | **MODERATE protector** |
| R2 attempt-cap ≤2 | subset of R2b effect (J17 attempt-5 removal dominates) | MODERATE (via R2b) |
| **R6 claim discount** | does not change follower pips (they're computed, not claimed) but **removes +699p of illusory claim pips**; 6 setups >1.25× would route to HUMAN_REVIEW | **essential for honest accounting; does NOT flip the sign — WEAK effect on expectancy, STRONG effect on claim hygiene** |
| caution_language / reason_stated | not recomputed here (flags not in the matched rows) | **INSUFFICIENT_DATA** |

Overlap note: R2b+R4b combined = same set as R2b alone in this sample (J17 in both; J03/J06 tiny) —
**R2b is the binding rule.**

## Conclusion strength labels (no overclaim)

- Follower edge positive after adjustment: **MODERATE** (32 setups, approximations documented, J10 gap).
- Claims systematically inflated vs follower-capturable: **STRONG** (deterministic on 22 claim-cases; +699p).
- R2b/R4b improve follower expectancy: **MODERATE** (clear in-sample; adopted rules remain provisional
  pending ≥15 forward trades per Day-6 thresholds).
- sl-to-entry instruction as a follower-outcome destroyer: **MODERATE** (J24 defining case + scratch
  modelling; needs forward instruction-timing evidence).
- caution_language / reason_stated protection: **INSUFFICIENT_DATA**.

## Safety confirmation

No broker/QST/cTrader/nano/copy/demo/live execution built; no permits/leases/orders; gates
`PAPER/PREVIEW/False/False`; listener PID 87988 running/untouched; no TradingView/Worker/R2/secret action;
AI output not used (deterministic arithmetic only); nothing promoted to trade-ready.
`NOT_INTEGRATION_READY` unchanged.

## Next step

Feed `follower_achievable_pips` + `inflation_ratio` into the forward scoring workflow (Cycle 002+): every
new XAU-F record gets the lane-4 computation at outcome-matching time, and inflation_ratio > 1.25 routes to
HUMAN_REVIEW. Optional refinements: recover J10's zone detail (completes the loss side), and a
sensitivity run (runner-always-0 vs runner-always-TP2 bounds) to bracket the approximation.
