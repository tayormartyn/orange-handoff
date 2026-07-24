# Training Batch 001B — Ratification Record + Merge Plan

**Mode: RATIFICATION + MERGE PLAN ONLY — SINGLE-SESSION.** Observation-only. Date 2026-07-11.
Extends (never edits) Batch-001, v0.3, Lane-6, R6, and Cycle-002 artefacts. Review-only; no automatic
change to detector v0.3's live forward behaviour — everything below is capture-only or offline/parallel
until separately ratified. Machine-readable: `training_batch_001b_ratification_and_merge_plan.json`.
Gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged.

## 1. HUMAN RATIFICATION RECORD — never-widen vs adaptive width

**Ratifier: Martyn (Batch-001B instruction). Decision: RATIFIED —**

> **"Never widen the stop" binds the follower simulation and the public/follower lane.** Adaptive wider
> stop-width belongs ONLY to Farouk's private/discretionary lane (lane 1) and to Orange's **pre-entry**
> invalidation research. Orange may calculate a structural invalidation width **before a candidate is
> frozen**, but must NOT model a follower widening a stop after entry.

**Binding consequences:** (a) lane-4 follower simulations never widen a stop post-entry — a follower
record showing post-entry widening is **model-invalid**; (b) lane-6/stop_width research computes width
ONLY at pre-mark/candidate freeze time (formula frozen per level type — already the F6 guard); (c) his
taped adaptive widening remains a lane-1 observation feeding the fill/stop-divergence analytics, never the
follower model. Sources reconciled: FP-EDU-003 §7 (the follower doctrine) vs video-002/v004 practice (his
discretion). This mirrors and completes the fill-lag/stop-divergence framework.

## 2. The five MERGE_NOW items — exact behaviour

| feature | behaviour | targets |
|---|---|---|
| **be_at_average_for_layered** | when layered entries are explicitly evidenced (≥2 leg events), the follower BE/scratch reference = the **average of filled legs** (one shared SL), per EDU-003 §8; single-entry setups keep the fill-price BE | R6 lane-4 scratch model · 8D leg schema · Cycle-003 capture |
| **source_exact_tranche_schedules** | expectancy computed under BOTH source schedules — Conservative **TP1 50% / TP2 30% / TP3 20%** and Advanced **TP1 30% / TP2 30% / SL→entry(+50) / remainder runs** — as dimensionless modelling fractions only (never sizing); replaces the assumed 50/25/25 | R6 lane-4 parameters (bracket) |
| **layering_cap_max3** | any 4th/additional entry into a losing position = **doctrine-violation / tail-risk flag** ("never add a 4th entry to a loser"); flag only, complements R2b | Cycle-003 capture · detector v0.4 backlog (flag) |
| **displacement_fvg_artifact_test** | displacement is evidenced by an **FVG created after the OB reaction** (3-candle gap, OHLC-computable); no fixed pip threshold unless later proven | Lane-6 STRONG-rubric point 1 · detector v0.4 backlog · unblocks R-DISPLACEMENT |
| **strong_ob_rubric_v0_1** | STRONG OB scored by five **evidence-cited** components: sweep-before · fresh level · displacement/FVG out · bias-aligned · BPR overlap (0–5 count recorded; UNTAGGED when uncitable) | F3 level_quality_tag · Lane-6 confidence · stop_width_by_level_type v0.1 inputs |

## 3. Conceptual target updates

- **detector v0.4 backlog:** layering_cap flag · displacement_fvg_artifact_test · rubric-count as a
  graded confidence input — all OFFLINE-replay first, never auto-live.
- **Lane-6 builder:** rubric v0.1 becomes the STRONG-tag test; FVG-artifact = displacement evidence;
  formation-time semantics from OB-extension (zones persist until mitigated).
- **R6:** lane-3 post-time fill confirmed canonical ("enter as soon as the signal is published");
  lane-4 runs BE-at-average + both tranche schedules; never-widen binding per §1.
- **Cycle-003 / XAU-F001 capture schema additions:** average-entry evidence · tranche schedule used (if
  statable) · entry count · 4th-entry violation flag · FVG-after-OB artifact · rubric components (cited) ·
  **follower-lane stop-widening = forbidden/model-invalid marker**.
- **stop_width_by_level_type v0.1:** width computed pre-freeze only; rubric score + mitigation state as
  the level-type inputs; his adaptive widening = lane-1 calibration data only.

## 4. Cycle-003 computable items (capture-only this cycle)

average-entry evidence · tranche schedule used · entry count · 4th-entry violation flag · FVG artifact
after OB · strong-OB rubric components · follower stop-widening marker (expected always absent/invalid).
None of these alter v0.3's live labels; they are recorded alongside for the v0.4 offline replay.

## 5. Next merge queue

- **MERGE_NOW_CAPTURE_ONLY:** be_at_average evidence fields · tranche-schedule field · entry count ·
  4th-entry flag · rubric components · FVG-artifact field · stop-widening marker.
- **MERGE_IN_DETECTOR_V0_4_OFFLINE:** layering_cap flag scoring · displacement_fvg_artifact_test ·
  rubric-count confidence input.
- **NEEDS_FORWARD_EVIDENCE:** mitigated→wider numeric mapping · F2 weight upgrade · rubric-count weights.
- **HUMAN_REVIEW_ONLY:** any future proposal to let follower simulations deviate from never-widen (§1
  forbids it; revisiting requires a new ratification).
- **REJECT_DUPLICATE:** none new this step.

## 6. Safety confirmation

Documentation only; targets pre-flight-checked; no artefact overwritten; no execution built
(broker/QST/cTrader/nano/copy/demo/live absent); tranche fractions are dimensionless modelling values —
no lot/risk/account/ticket fields anywhere; no permits/leases/orders; gates unchanged; listener PID 87988
running; no TradingView/Worker/R2/secret action; nothing trade-ready; no automatic promotion.
`NOT_INTEGRATION_READY` unchanged.

## Next step

Cycle 003 on the next gold-trades activity with the §4 capture-only additions active; detector v0.4
offline replay (with the three backlog features) after ≥1 forward setup exists or as the next offline task;
batch 002 (journal xlsx, Live Jul-3, 2025-12-14 movs) as time allows.
