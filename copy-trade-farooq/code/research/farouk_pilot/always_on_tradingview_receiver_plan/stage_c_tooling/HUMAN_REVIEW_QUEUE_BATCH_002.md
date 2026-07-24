# Human Review Queue — Batch 002

**Observation-only; candidate-only.** Seeds from the Jul-10 (and later) offline pipeline. Machine copy:
`human_review_queue_batch_002.csv`. `NOT_INTEGRATION_READY` unchanged.

## Status: 0 candidates — Jul-10 OHLC imported, event-characterisation only

As of 2026-07-10, no candidates are enqueued.

**Why (Jul-10 run, OHLC now imported):**
- Verified Jul-10 captures processed: H1 A+ @ 04:57Z (`A+ or better setup`) and H2 CHoCH-down @ 01:39Z /
  03:51Z / 07:09Z (`CHoCH down (bearish)`).
- **Classifier:** 4/4 classified — 3× `CHOCH_DOWN` (SHORT_HINT), 1× `A_PLUS_OR_BETTER` (no direction).
- **Detector:** **0 shadow-candidate sequences** — the A+ is a grade with no direction, and the CHoCH-downs
  are not followed by a directional A within the window, so no `ALIGNED_CHOCH_TO_A` / `SWEEP_TO_CHOCH` /
  `BPR_TO_A` sequence forms.
- **Outcome matcher (event characterisation, NOT candidates):** ran against the imported Jul-10 OHLC
  (`price_data/XAUUSD_1M_2026-07-10_IMPORT_HERE.csv`, 2026-07-09T18:01Z→07-10T08:09Z). EVT-01 bearish FAILED
  (−11.02), EVT-02 bearish WORKED (+7.50), EVT-03 A+ ~flat (−1.78), EVT-04 PARTIAL (data ends 08:09Z). See
  `JUL_10_OFFLINE_PIPELINE_RUN_REPORT.md`.
- **Scorer / state machine:** not fed — no campaign sequence exists (no fabrication).

## Enqueue rule

Only candidates whose Farouk Campaign State Machine v0.1 state is `WATCH_ONLY`, `SHADOW_CANDIDATE_LOW`, or
`SHADOW_CANDIDATE_MEDIUM` are enqueued here. `SHADOW_REJECTED` candidates are **journalled but not enqueued**.

## Queue (0 PENDING)

_(none yet.)_

### LIVE012 A-only time-box (2026-07-10 ~10:15–10:24Z) — 0 candidates

The time-boxed directional-A fallback **worked**: **A SHORT** (10:15Z, key `a989c821…`) and **A LONG**
(10:21Z, key `0cc9cb88…`) were captured (the previously-missing events), plus one `CHoCH up` (10:24Z). But
the detector formed **0 sequences** — a **CONTRADICTORY_CLUSTER** (A_SHORT + A_LONG opposite, 6 min apart) and
the CHoCH_up fired *after* the A_LONG (wrong order). **No candidate fabricated.** 0 non-A noise events to
ignore in this window. See `BATCH_002_TIMEBOX_CLOSE_VERIFICATION_REPORT.md`.

### LIVE012 EXTENDED window (2026-07-10 10:27–18:03Z) — 0 candidates

LIVE012 over-ran (~7.5h). R2 90→103 (window +10): **SWEEP_HIGH ×5, SWEEP_LOW ×3, CHOCH_UP ×2 — 0 A_LONG,
0 A_SHORT** (no Engulfing/BPR/A+). Detector **0 candidates, 2 disqualified clusters**; no directional A →
nothing terminates; no `SWEEP_LOW→CHOCH_UP` within 30m either. **No candidate fabricated.** See
`BATCH_002_EXTENDED_TIMEBOX_CLOSE_VERIFICATION_REPORT.md`.
