# Fable 5 Training Batch 001 — Targeted High-Value Processing Report

**Mode: TARGETED METHOD EXTRACTION ONLY — SINGLE-SESSION.** Observation-only. Date 2026-07-11.
Listener PID 87988 untouched. All lot/leverage/compounding content in the sources was **noted and excluded
by policy** (no risk-sizing enters Orange); volumes treated as descriptive only. Machine-readable:
`fable5_training_batch_001.json` + `fable5_training_batch_001_merge_queue.json`. Gates
`PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged.

## 1. Processed (7 items) / skipped / later

**Processed:** FP-EDU-004 OB Strong-vs-Weak (repo PDF, 2pp) · FP-EDU-003 Trading Guide (repo PDF, 12pp) ·
FP-EDU-002 Playbook + Farouk Education (2) (repo text extractions, grepped) · Live Jul-5 stream (existing
276KB transcript, grepped via the Jun-30 stream below taking priority) · **NEW: Schermopname 2026-06-24
(J26 "GOLD BREAKDOWN", 73.6MB, sha256 e576af86…7b34) → registered FP-LIVE-VIDEO-EXPLAINER-003,
RIGHTS_PENDING_PRIVATE_REVIEW, transcribed locally** · **NEW: "10 min stream.mp4" (actually a full ~1h
Jun-30/S1-era stream, 187.2MB, sha256 dadb6e54…141c) → registered FP-LIVE-VIDEO-EXPLAINER-004, same
rights, transcribed locally** · Schermopname 2026-07-05 indicator walkthrough (repo screens already
ingested; **audio now transcribed** — FP-INDICATOR-005 context).

**Skipped as duplicates:** all five Downloads PDFs (byte-duplicates of registered repo copies), Live Jul-5
mp4, indicator mov, the three campaign breakdown movs (= FP-CAMPAIGN-001/002/003), GMT20251221
(FP-INDICATOR-001, ingested), GMT20251012 (FP-EDU-007, ingested), duplicate "(1)/(2)" copies.

**Later review:** Live with Farouk Friday 3 July (525MB — likely FP-EDU-001's true source; register-date
discrepancy noted) · 3× Schermopname 2025-12-14 movs ([kyle]-era) · Trading Journal / trade-audit xlsx +
WhaleRoom_TradeRecap_1.pdf (potential stop-width calibration data) · Exochart/Delta-OI tutorials (out of
SMC scope per R-OI).

## 2. Lessons on the weak topics (with classifications)

### Stop-width / invalidation — the batch's biggest win
- **Structure-relative placement is universal across sources:** "place the stop beyond that [key S/R]
  level" (EDU-003 §7), "just outside the OTE zone" (Education-2), "outside the range" (Education-2),
  "stop loss below this low / above this high" (v004 stream). → **STRENGTHENS F6/stop_outside_zone.**
- **Mitigated → wider stop, now REPEATED TEACHING:** v004: "because this was mitigated… I put my stop
  loss a little bit higher. So again, I put my stop loss higher." (twice, plus "maybe stop loss a little
  bit bigger"). → upgrades `mitigated_level_wider_invalidation` provenance; numeric mapping still
  **NEEDS_FORWARD_EVIDENCE**.
- **NEW doc-vs-practice tension:** EDU-003 §7 commands "never remove or widen it / never move the stop
  further away" — while his own taped practice widens stops adaptively. → **NEEDS_HUMAN_REVIEW** (follower
  rule vs his discretion; mirrors the 2R finding).

### Mitigation depth / zone_touch_count
- EDU-004: **"Fresh/unmitigated — the FIRST TAP is the strongest"**; weak-OB page: "already tapped several
  times — each retest drains it; a mitigated block is spent", diagram labelled **"TAPPED 3×"**. v004 uses
  mitigated/unmitigated as the primary level-state vocabulary throughout. → **STRENGTHENS F2**; the v0.3
  thresholds (0 fresh / ≥3 spent) are now source-aligned; no exact numeric beyond the 3× canon → weight
  stays LOW.

### Numeric displacement — RESOLVED VIA ARTIFACT
- EDU-004: a strong OB requires "**big displacement leaving it** — a strong impulse exits the block **and
  drops an FVG right after**". → displacement is testable by its artifact (**FVG present after the
  impulse**), computable from OHLC 3-candle gaps — no pip threshold needed.
  → **NEW_PROMISING_FEATURE: `displacement_fvg_artifact_test`** (unblocks R-DISPLACEMENT).

### Strong/weak levels
- EDU-004 gives a checkable **5-point STRONG-OB rubric**: (1) displacement+FVG out, (2) swept liquidity
  just before forming, (3) fresh/unmitigated, (4) bias-aligned (Trend-EMA side), (5) bonus BPR overlap =
  strongest. Weak = none of these / tapped / counter-trend / alone. → **STRENGTHENS F3**: level_quality_tag
  gets rubric v0.1 (evidence-citable per point).

### Management / multi-position (lane-4 / 8D refinements)
- **BE at +50p measured from the AVERAGE entry for layered positions** (EDU-003 §8: "at +50 pips from
  average, move STOP LOSS to your average") — not per-leg, not near-edge. → refines the scratch model.
- **Exact tranche schedules:** Conservative TP1 50%/TP2 30%/TP3 20%; Advanced TP1 30%/TP2 30% + SL→entry
  (+50) + remainder runs (EDU-003 §6) — replaces our assumed 50/25/25.
- **"Never add a 4th entry to a loser"** (§8 rule 05) → hard layering cap ≤3 from the source.
- **One shared stop-loss for all legs** (§8 rule 02) → 8D leg model refinement.
- **"Enter as soon as the signal is published"** (§2 tip) → the guide's canonical follower behaviour is a
  post-time market fill → **lane-3 is the official follower lane; STRENGTHENS R6** (and explains the
  fill-lag cost structurally).
- v003 (J26): "if it doesn't come to your level, don't take a trade — just skip" (no-chase doctrine);
  v005: OB extension semantics ("extend, extend" — zones project forward until mitigated) → **Lane-6
  formation-time definition input**.

## 3. Does it support or weaken Orange v0.3?

**SUPPORTS.** F2's thresholds match the source canon (first-tap strongest / 3× spent); F3 gains a rubric;
F6 is confirmed by four independent sources; the graded-confluence posture matches EDU-004's
strongest-confluence language. Nothing contradicts v0.3's design; the two tensions found (never-widen doc
rule; BE-at-average) are refinements, not contradictions.

## 4. Safety confirmation

All processing read-only from existing files/duplicates; two new items registered as private research
evidence (rights pending); transcripts local-only (ephemeral scratchpad); no lot/risk/account content
carried into Orange; no execution built; no permits/leases/orders; gates unchanged; listener PID 87988
running; no TradingView/Worker/R2/secret action. `NOT_INTEGRATION_READY` unchanged.

## Next step

Merge queue → human ratification for the never-widen tension; implement the five MERGE_NOW items in the
Cycle-003 capture/lane-4 parameters; Cycle 003 on next gold-trades activity. Batch 002 later: the
Trading-Journal xlsx (stop-width calibration), Live Jul-3, and the 2025-12-14 movs.
