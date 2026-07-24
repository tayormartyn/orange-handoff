# Human Ratification Record v0.1 (Recovery Item 1B)

**Date 2026-07-11. Ratifier: Martyn (via Recovery-Item-1B instruction). Scope: the three
NEEDS_HUMAN_REVIEW items from `farouk_plus_rule_merge_queue_v0_1.json`.** Review-only; nothing herein
creates or authorises execution; gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged.
Machine-readable: `human_ratification_record_v0_1.json`.

| # | item | decision | binding consequence |
|---|---|---|---|
| 1 | **BOS candle-close contradiction** (EDU-016 "required" vs EDU-021 "preferred"; Fable proposal from video-002 live usage) | **RATIFIED: candle-close = +confidence feature, NOT a hard gate** | unblocks R-BOS-CANDLECLOSE as `bos_candle_close_confirmed` (+confidence, LOW weight) in detector v0.3 / Lane-6 confidence; EDU-016's "required" reading is retired for scoring purposes |
| 2 | **All-boxes veto vs graded confluence stack** (Playbook-internal contradiction #6) | **RATIFIED: graded confluence stack, NOT all-boxes hard veto** | detector v0.2's graded scoring posture is now explicit policy; no all-or-nothing veto will be implemented; grades remain review labels capped at SHADOW_CANDIDATE_MEDIUM |
| 3 | **2R finding** (docs teach ≥2R; 34-trade sample shows tranche-1 far below 2R) | **RATIFIED: do NOT assume 2R** | R6 expectancy must use actual tranches, posted TP1/BE behaviour, and follower-capturable pips only; any future R:R statistic is computed from matched data, never assumed |

Provenance: diff evidence in `SONIC_V03_RULE_LEDGER_DIFF_REPORT.md`; contradiction lineage in
`synthesis_v0.3/CONTRADICTION_ADJUDICATION_v0.1.md` (preserved untouched). These decisions bind Orange's
review lane only — they do not, and cannot, alter execution gates or governance policy (R-RISK-1PCT
remains excluded from this lane entirely).
