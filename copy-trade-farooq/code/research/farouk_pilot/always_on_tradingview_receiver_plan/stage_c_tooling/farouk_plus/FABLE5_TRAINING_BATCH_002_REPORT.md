# Fable 5 Training Batch 002 — Stop-Width, Journal/Audit, and Older-Video Review

**Mode: TARGETED METHOD EXTRACTION ONLY — SINGLE-SESSION.** Observation-only. Date 2026-07-11.
Listener PID 87988 untouched. All sizing/account/leverage/compounding content redacted or excluded by
policy (the xlsx dumps auto-redacted matching columns). Machine-readable: `fable5_training_batch_002.json`
+ `fable5_training_batch_002_merge_queue.json`. Gates `PAPER/PREVIEW/False/False`;
`NOT_INTEGRATION_READY` unchanged.

## 1. Processed / skipped / later

**Processed (5):**
1. **`farouk_trade_audit.xlsx` → FP-AUDIT-001** — a prior independent signal audit, 22 May–27 Jun 2026,
   31 rows (27 gold + 4 BTC) with per-row Entry/Stop/TPs, audited outcomes, R mid/low/high.
2. **`farouk_final_reconciliation_audit.xlsx` → FP-AUDIT-002** — the reconciliation pass: audited
   distribution 26W/4L/1BE (vs 28W/3L uploaded); **"Recommended honest Gold range: +0.27R to +0.35R per
   primary signal"**; sign-off explicitly "NOT YET".
3. **`Trading Journal - Farouk - Whale Room.xlsx` → FP-JOURNAL-001** — his July-2024 **crypto** journal:
   260 trades (223W/18L/17F, "92.5%" excluding flats from the denominator), entry+SL per row, management
   comments; plus a 10%-per-trade compounding fantasy sheet (excluded as reference).
4. **Live with Farouk, Friday 3 July 2026 (525MB) → transcribed (2,268 segments)** — reconciles the
   FP-EDU-001 register-date question (register says Jul-3; the repo raw copy is the Jul-5 stream — both
   exist; processing recorded as FP-EDU-001-B).
5. Live Jul-5 transcript — deprioritised this batch (Jul-3 covered the same era with new material).

**Skipped as duplicates/low:** GMT-zoom sets (ingested), 2025-12-14 movs ([kyle]-era, deferred again),
Exochart/Delta tutorials (out of scope), WhaleRoom_TradeRecap_1.pdf (tiny; later).

## 2. The batch's headline: a THIRD expectancy lane + row-level cross-validation

- **FP-AUDIT-002's claim-based R expectancy: +0.27R to +0.35R per primary gold signal** (methodologically
  careful: under/over-credits corrected, unknowns bracketed, re-entries/layers flagged as its stated
  critical limitation). With typical posted gold stops ($25–40 structural), 0.3R ≈ roughly 75–120
  pips/signal — **sitting near Model A and far above Model B**, because it (like Model A) credits his
  claim-based managed exits. Triangulation now reads: literal-automation ≈ 0 (Model B) · claim/managed
  credit ≈ +0.3R (audit, Model A) · truth = instruction-timing dependent (8C capture decides).
- **Row-level cross-validation of our June ledger by an independent prior audit:** J01=0R partial,
  J03=−0.16R manual, J08=manual loss, J21="narrowly avoided SL" 0.784R, J22=invalid-stop typo,
  J23=manual loss — **every checked verdict matches ours.** Confidence in the Day-3/5 ledger rises.
- **Six pre-capture May gold trades recovered** (22–29 May, claim-only): incl. a 2.2R full-TP3 winner
  (May-29) and the era's stop widths ($20/24/40/25/25/20 beyond far edge) — extends the stop-width
  calibration set and the RESULT_CLAIM_ONLY ledger backward (OHLC-matchable later if May data is exported).

## 3. Lessons on the weak topics

- **Stop-width/invalidation:** +6 May width samples (median holds ~$20–25); Jul-3 spoken anchor —
  **"stop loss above a level… 3, 400 pips"** ($30–40 named as the normal level-based scale) + "this is
  too big stop loss" width judgement + wick-relative placement ("a little bit lower, below this wick") →
  **STRENGTHENS stop_width_by_level_type v0.1 dataset**.
- **Mitigation depth:** nothing numeric new (v004/EDU-004 canon stands).
- **Displacement:** "the longer the range, the bigger the move" (range-size heuristic; WATCHLIST) — the
  FVG-artifact test remains the operative resolution.
- **Strong/weak:** no additions beyond rubric v0.1.
- **Management/multi-position:** FP-JOURNAL-001 shows the SAME doctrine in July-2024 crypto ("stop loss
  to entry (100% profit)", partials, early cuts) — the management style is **stable across 2 years and
  asset classes** (doctrine-stability = confidence in forward modelling). Also confirms the win-accounting
  convention (flats excluded from the denominator) as long-standing — claim-quality context for R6.
- **Feed/source:** nothing new.

## 4. Orange impact

**v0.3 SUPPORTED** (cross-validation strengthens the underlying ledger; nothing contradicts). **R6
STRENGTHENED** — the audit R-lane becomes a recordable per-setup metric (`audit_r_midpoint`, capture-only)
and the +0.27–0.35R claim-lane estimate joins the expectancy triangulation. **Lane 6:** minor (width
dataset grows). **Detector v0.4 backlog:** unchanged. **Human ratification: none required this batch**
(no doctrine conflicts found; the audit's own "sign-off NOT YET" note is preserved as its status).

## 5. Safety confirmation

Read-only processing; xlsx sizing columns auto-redacted; compounding/lot/leverage sheets excluded; no
execution built; no permits/leases/orders; gates unchanged; listener PID 87988 running; no
TradingView/Worker/R2/secret action; transcripts local-ephemeral. `NOT_INTEGRATION_READY` unchanged.

## Next step

Cycle 004 at next market activity (full capture spec + the new `audit_r_midpoint` capture field);
detector v0.4 offline replay when scheduled; batch 003 later (2025-12-14 movs, WhaleRoom_TradeRecap,
May-trade OHLC matching if May data gets exported).
