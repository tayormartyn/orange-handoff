# Next Observation Cycle Plan

**Mode: observation-only.** Everything below is capture / offline analysis / documentation. **No** broker,
QST, cTrader, execution, permit, lease, order, gate change, or Worker deploy. `NOT_INTEGRATION_READY`
unchanged. Follows on from `HUMAN_REVIEW_BATCH_001_SUMMARY.md` (3/3 reviewed: LOW / WATCH / REJECT — none
trade-ready) and `NEXT_30_OBSERVATION_PLAN.md`.

## Where we are

- **Human-review queue: COMPLETE (3/3 REVIEWED).** No new candidates awaiting review.
- **Evidence bar: 3 / 30 outcome-matched candidates across ≥5 sessions — NOT MET** (single session so far; a
  REJECT does not count toward the bar).
- **Standing capture lane:** H1 `LIVE004_APLUS_MIRROR_GATE_H1` (A+) and H2 `LIVE005_CHOCH_DOWN_MIRROR_GATE_H2`
  (CHoCH down) both **armed / not fired / untouched**; cloud Worker pure logging-only; Telegram PREVIEW
  listener PID 16608 running.

## The cycle (repeat until the evidence bar is met)

1. **Keep H1 and H2 armed** — do not touch, re-URL, or duplicate them. Wait for a **natural A+ (H1)** or
   **CHoCH-down (H2)** trigger. No new alerts created by Claude.
2. **On an H1/H2 fire → verify R2 FIRST** (this is the only R2 check permitted): use the temporary
   secret-gated **read-only list branch** to confirm the object landed, then **revert the Worker to pure
   logging-only**. Confirm the capture, then move on. (If nothing fired, **do not** check R2.)
3. **After enough events are captured, import the next session's OHLC** — a cleaned XAUUSD 1m CSV (UTC,
   PEPPERSTONE export) into `price_data/`, following `XAUUSD_OHLC_IMPORT_SCHEMA_v0_1.md` /
   `PRICE_DATA_IMPORT_INSTRUCTIONS.md`. **Never fabricate price data** — no data → NO_DATA, not estimates.
4. **Re-run the offline pipeline** on the new session (all pure functions, stdlib, no I/O to broker/QST):
   `raw_farouk_text_classifier_v0_2` → `shadow_candidate_detector_v0_1` → `outcome_matcher_v0_1` →
   `farouk_methodology_scorer_v0_1` (+ chart-context / session / HTF / OB-proxy resolvers as context).
5. **Append new outcome-matched candidates** to `SHADOW_OBSERVATION_JOURNAL_v0_1.md` / `.csv`, then **enqueue
   them** in `HUMAN_REVIEW_QUEUE_v0_1.md` / `.csv` as PENDING for the next review batch (batch 002).
6. **Review each new candidate** with corrected screenshots (1m / 3m / true-15m / Jul 1h; state chart tz),
   applying batch-001 lessons (below).
7. **Continue toward ≥30 outcome-matched candidates across ≥5 sessions** before any demo discussion. Track
   progress in the journal roll-up. The bar staying NOT MET keeps `NOT_INTEGRATION_READY` in force.

## Batch-001 lessons to apply next cycle

- **Prioritise HTF alignment.** All three batch-001 candidates traded against HTF and none was trade-ready;
  flag HTF-against candidates as low priority. Capture a **real Jul-day 1h** each time (the 1h proxy is
  often insufficient-data).
- **Do not trust the machine score as a quality rank** — it measures confluence coverage, not edge
  (0.69 → WATCH beat 0.375 → LOW-with-best-outcome). Keep human structural review in the loop.
- **Down-weight spent/mitigated OBs and OBs that get breached post-entry** (HR-0002/HR-0003 failure mode).
- **OB/displacement proxy improvement (observation-only, NO invented thresholds):** add liquidity-sweep
  context and a lower/adaptive displacement gate — HR-0001 showed the 2.0× ATR gate misses real
  indicator-drawn OBs at ~1.9×. Log as a tooling recommendation; do not hard-code magic numbers.

## Hard guardrails (unchanged)

- Observation-only; candidate-only; all exec flags false. No TradingView alert touched; no broker / cTrader
  / QST; no permit / lease / order; no gate change; gates stay `PAPER/PREVIEW/False/False`; 1.0% risk cap
  unchanged; Worker pure logging-only; Telegram listener PID 16608 left running. **R2 read only on an H1/H2
  fire, then revert.** `NOT_INTEGRATION_READY` unchanged until governance lifts it.
