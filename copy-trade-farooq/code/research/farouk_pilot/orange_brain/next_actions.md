# ORANGE — Next actions (ranked; machine copy: next_actions_v0_1.json)
Generated 2026-07-20; order FIXED by operator (D-010): **H-FPL-05 Friday final → TASK 1B corpus (spec: work_orders/TASK_1B_CORPUS_SPEC.md) → H-FPL-02 run → Stage 2 rule mining.** H-FPL-05 harness is BUILT and first interim run is DONE (see h_fpl_05/); action 3 below is superseded in sequence by TASK 1B but its frozen params stand.

## 1. Score H-FPL-05 — the pre-registered Sunday weekly plan — against this week's live bars
- **Objective:** produce `derived/live_video_20260719/H_FPL_05_SCORE_20260724.md` scoring each frozen sub-claim (XAU: buy 3984–4000 first-touch bounce; rejection 4028–35 unless 1h close above → reach 4050–60; daily close < 3959–61 → 3829/3860. BTC: 67.3–68.4k first-touch reject; 63.5k holds) as HIT / MISS / NOT_TRIGGERED with bar citations.
- **Why now:** the only zero-leakage, pre-registered forward test of both Farouk's prospective skill and our zone reading; the evidence window closes when the week ends.
- **Named blocker removed:** none required — zones frozen 2026-07-20, bars already flowing.
- **Required inputs:** EVIDENCE_REPORT_LIVE_20260719.md §6 (H-FPL-05), tracker ingestion log / canonical bars.
- **Claude Code required:** yes (one read-only session). **Live impact:** NONE.
- **Proof of completion:** the score doc with per-sub-claim citations. **Stop:** all sub-claims scored or week over.
- **Deferred alternative:** single Friday-close scoring pass.

## 2. Martyn: clear the actionable quarantine review queue
- **Objective:** append-only resolutions for the actionable queue (18 as of the 07-20 refresh — see operator_brief). Start with the 7 alert-flagged recent ones: 45784, 45896, 45901, 45916, 45922, 45924, 45934. (OQ-8: there is no durable resolution record format yet — defining one is part of this action.)
- **Why now:** only human-resolvable; queue doubled this weekend and grew again live today (45934); fail-loud lane stays trustworthy only if reviewed.
- **Named blocker removed:** PENDING_OPERATOR_REVIEW on 6 durable records.
- **Claude Code required:** no (Martyn; Fable can present the bounded texts on request). **Live impact:** NONE (append-only).
- **Proof:** resolution_status set on all 6. **Stop:** queue empty.
- **Deferred alternative:** review the three oldest first (45784 is from 07-16).

## 3. H-FPL-02 offline event study — Farouk's categorical "no FVG, no OB"
- **Objective:** deterministic study on canonical 1m/5m: do FVG-paired OB candidates reject on first touch more than unpaired ones? Parameters (OB→FVG max bar gap, touch depth, rejection horizon) FROZEN in a params JSON **before** running.
- **Why now:** tests Farouk's own explicit rule (K-015); decision-changing for the detector v0.4 backlog (keep/kill FVG validity gate); fully offline.
- **Named blocker removed:** unfrozen test parameters (freeze them as step 1).
- **Required inputs:** price_data canonical CSVs; smc_features candidate_ob_zones + FVG detector.
- **Claude Code required:** yes. **Live impact:** NONE (research dir only).
- **Proof:** H_FPL_02_EVENT_STUDY.md + frozen-params JSON + reproducible script. **Stop:** measured separation or falsification; NO promotion without forward proof.
- **Deferred alternative:** H-FPL-01 (Asia-break) first if OB/FVG definitional freeze stalls.

**Rejected as circular:** re-investigating indicator existence · rewriting the Sunday summary · new setup families without evidence · decision-free documentation · fitting retrospective/backfill data.
