# FABLE 5 TRAINING BATCH 004 — REPORT (targeted education gap fill)
**As of 2026-07-12 ~14:50 local (12:50Z, Sun). Machine-readable twins: `fable5_training_batch_004.json`
+ `fable5_training_batch_004_merge_queue.json`. Mode: TARGETED GAP FILL, LIVE-PRIORITY FIRST,
review-only; no scoring change; v0.3 live labels untouched; v0.4 stays offline.**

## 0. Live-priority gate (checked before, during, and after)
Listener **PID 23012 running/untouched** throughout. Read-only store checks at 11:56Z, 12:20Z, 12:33Z,
12:50Z: max msg id still **45648** = cursor; no new messages; market closed until ~22:00Z; alert lane
cannot fire. **No XAU trigger → Cycle 006 not invoked; batch proceeded and completed.**

## 1. Queue selection (targeted at the weak areas; NOT blind ingestion)
Selected 4 items + 1 small add-on; dedup by filename/size/sha256/existing evidence IDs was clean:

| item | source | why selected |
|---|---|---|
| **FP-EDU-001 review** | `raw/live_with_farouk_2026-07-05/_analysis/transcript.json` (276KB, 1,664 seg, 2h08) — on disk since Jul-5, **never Fable-reviewed** (recovery-index item 5) | the long teaching session; indicator semantics, stop-width, mitigation depth |
| **FP-B004-Z1** (NEW) | `Downloads/GMT20251012-140632_Recording.m4a` (43MB, 45 min) — Sunday Zoom Oct-12 2025, unprocessed | "remaining Sunday Zooms" target |
| **FP-B004-Z2** (NEW) | `Downloads/GMT20251221-181518_Recording.m4a` (113MB, 2h45) — Sunday Zoom Dec-21 2025, unprocessed | same; adjacent to the Dec-14 indicator era |
| **EDU-035 + EDU-028 re-read** | BATCH-02 OCR corpus + register | displacement + stop-width weak-topic pair |
| **FP-B004-LOG1** (NEW) | `Downloads/SeaScalper_TradeLog_1.pdf` (5,223 B, End-Feb→W1-Mar 2026 weekly log) — in no prior batch | claim conventions + limit-order evidence |

Transcription: Z1+Z2 transcribed locally (detached `tools/batch_004_transcribe.py`, faster-whisper
base.en cpu/int8; **2/2 ok at 12:32:57Z**; 595 + 2,202 segments) into
`derived/transcripts/batch_004/FP-B004-Z1|Z2/` with sha256 source meta. The known accent/OCR garbles
apply ("50 minutes"=15 minutes, "FPG/effigy/FEG"=FVG, "view up"=VWAP); spoken digits LOW-confidence.

**Missing (listed precisely, not guessed):**
- **"15 min stream" companion to the Jun-30 stream — NOT on disk** (only `10 min stream.mp4`, already
  FP-LIVE-VIDEO-EXPLAINER-004).
- **A separately-recorded "Friday indicator Q&A" — NOT on disk as a distinct file.** The Jul-5 session
  references "we talked about this on Friday" = Live Jul-3, already processed (FP-EDU-001-B).
- **EDU-035's fuller displacement rule** ("I'll explain in more detail during the session", Sept-11
  2025): that session recording is NOT on disk — checked both Zooms; neither contains it.
- FP-CAMPAIGN-004 raw video; FP-EDU-005/006 (register-confirmed unused IDs) — unchanged known gaps.

**Skipped as duplicate / lower value / off-policy:** all "(1)/(2)" copies (both Zoom m4a duplicates +
both 1.1GB/177MB Zoom **video** variants of the same recordings + Exochart dup);
`1_Welcome / 3_How_to_Setup_First_Chart_in_Exochart / 4_How_To_Setup_Templates /
6_Delta_Bars_OI_Net_longs_and_Net_Shorts` (Exochart/Delta/OI series — excluded by rule);
`SeaScalper_TradeLog_1 (1).pdf` (byte-identical dup). **FP-B004-Z1 verdict after transcription:
REJECTED for the XAU engine** — a guest member's EMA/stochastic scalping session (crypto-focused,
heavy lot-size/percent-per-day content, excluded by policy); it is the EMA family already parked as
FP-EDU-007; registered with sha256 for provenance, no lessons merged.

## 2. Displacement lessons
- **FVG claim-chain (Jul-5, NEW):** "they claim the first [bearish FVG], the second — why not the
  third? If the market maker wants to push lower, they need to RESPECT this bearish FVG"; claiming a
  5m FVG → "they will go to the highest level that made that lowest level" (the extreme). A sequential
  FVG-claims rule: claimed FVGs → continuation toward the origin extreme; a respected (unclaimed) FVG
  = the guard level. → **NEW_PROMISING_FEATURE `fvg_claim_chain`** (capture-first; v0.4/v0.5 backlog;
  OHLC-computable forward once FVG inventory is captured).
- **Displacement→FVG→strong OB (Jul-5):** "you will see an impulsive move… FVG, they get FVG. Now we
  know that this is a strong OB" — verbatim confirmation of the `displacement_fvg_artifact_test`
  design. **STRENGTHENS v0.4 backlog item** (still no numeric threshold spoken — FVG-presence remains
  the right test).
- **EDU-035 fuller rule: still MISSING** (see §1). Design unchanged; no fabrication.

## 3. Mitigation-depth lessons
- **First explicit depth anchor (Jul-5):** "we look for another long or **at least 50% of the zone**,
  and then we put stop loss to entry" — a ~50%-of-zone depth reference (transcript digits
  LOW-confidence). **STRENGTHENS** mitigation-depth capture (8D) — joins Batch-003's "deeper
  replacement" preference.
- **Weekly mitigation levels as magnets (Z2):** unmitigated weekly zones repeatedly named as targets
  ("mitigation level 4270-4260… they will come back"); "even once they mitigate and bounce — even a
  dead-cat bounce". **STRENGTHENS** untested-level-magnet + Lane-6 target logic.
- Fresh/spent doctrine re-confirmed verbatim (Jul-5): "tested a couple of times → not a fresh level
  anymore → weak OB". **ALREADY_IN_ORANGE (F2/F3).**

## 4. Stop-width / invalidation lessons (headline)
- **NEW causal driver (Z2, verbatim ×2):** "Friday I had a little bit **bigger stop loss**… because we
  had **a lot of levels to mitigate**"; "they can still sweep the low — that's why I took a bigger
  stop loss, because there are levels that need to get mitigated." → **Stop width is sized to
  surrounding unmitigated levels / sweep risk, not only to the entry level's type.** →
  **NEW_PROMISING** input to `stop_width_by_level_type` v0.2 research (capture: count/distance of
  unmitigated levels between entry and stop candidate).
- **Stop-feasibility veto (Jul-5, NEW):** a level he refuses to trade because "where do you put your
  stop loss?… this level is too big" — unplaceable stop = no trade. **NEW_PROMISING** capture note
  (lane-6 invalidation research: `stop_feasibility_note`).
- Structural anchor re-confirmed: stop above a never-mitigated FVG (Jul-5); EDU-028 OTE re-read adds
  nothing new ("stop outside the OTE zone" already registered; its ≥2R clause already discounted by
  the no-2R ratification). **ALREADY_IN_ORANGE.**

## 5. Strong/weak-level lessons
- **HTF>LTF hierarchy verbatim (Jul-5):** "daily is stronger than the 5 minutes"; "the indicator is
  only giving strong OBs"; fresh-level validity Q&A: "how long are levels valid? If it is fresh, that
  means a strong level" — freshness dominates age. **STRENGTHENS strong_ob_rubric_v0_1 + F3.**
- **Flat candles as a level class (Z2, NEW semantic):** "flat candles is a thing in gold — they need
  to get mitigated"; structure-break + flat candle + gap = strong buyers. Maps to the vector/yellow
  market-maker candle family. **NEW_PROMISING** capture semantic.
- **Gold gap-fill doctrine (Z2):** "gaps for gold — it's a thing… they're just filling these gaps"
  (futures gaps need filling). **NEW_PROMISING** capture semantic (gap level class).

## 6. Indicator / Lane-6 lessons
- **Jul-5 indicator UPDATE documented:** **London High/Low + US High/Low added** to the panel;
  **extended boxes** (levels projected right); **"Asia trap bull/bear" alert usage** explained (set on
  the 5-minute chart); "it's NOT a signal indicator — levels where the market maker will bounce".
  **STRENGTHENS** the alert mapping + Lane-6 builder; extends the 003B `indicator_level_source_kind`
  enum (add `LONDON_HIGH/LOW`, `US_HIGH/LOW`, `FLAT_CANDLE`, `GAP` — capture-only note).
- **ORB session times made concrete (Z2):** ORB = the **first 15 minutes** ("50 minutes" garble);
  London 09:00 GMT+1, NY 15:30; **orb-breakout-never-retested = area of interest (magnet)**.
  **STRENGTHENS** Batch-003 ORB semantics.
- **Session-break priors extended:** Asia-high break "still 80%" + the 78% 22-year claim repeated
  (Jul-5, with on-stream stats); "London High and US High break → continuation" (his "100%" =
  hyperbole). → **WATCHLIST `london_us_session_break_priors`** joins `asia_high_break_session_prior`
  (verification + ratification before any use).
- POC/VAH/VAL + **multi-TF VWAP confluence** (daily+weekly+monthly) used live in Z2. **STRENGTHENS.**
- **Post-break confirmation nuance (Jul-5):** "the best confirmation after we break Asia high/low is
  the change of character on the low time frame, especially the 3 and 1 minutes" — adds sub-5m CHoCH
  granularity to the confirmation stack. **STRENGTHENS** (capture note).

## 7. Limit-at-zone / SL-to-entry / claim lessons
- **Documentary limit-order evidence (FP-B004-LOG1):** the official weekly log prints **"Limit Long /
  Limit Buy"** as the entry type on gold rows. **STRENGTHENS** 003B `entry_mechanic_evidence` doctrine.
- **Anticipatory follower BE (Jul-5, verbatim — 8C-relevant):** "if you are 50 pips in profit, put
  stop loss to entry and take TP… **Before I say put stop loss to entry, you guys need to do it
  already. Like the 50-60 pips.**" → followers are STANDING-INSTRUCTED to move SL to entry at +50-60p
  ahead of his message. Confirms Model B's +50 BE arm as official follower doctrine and adds a
  **capture-only `scratch_mode` value: `DOCTRINE_ANTICIPATED`** (BE move that precedes the
  instruction). Also BE-scratch cost acknowledged on tape ("stopped us to entry, unfortunately…
  a level that we need to re-enter" → R2-family re-entry after scratch).
- **Layering (Z2):** "five-point entry", one shared SL for all legs; "now I just open **one position,
  one stop loss**" (his current lane-1 preference); "free stop loss" = early partial TP financing the
  stop. **STRENGTHENS 8D + R6 lane-1/lane-4 notes** (all sizing digits excluded by policy).
- **Claim-convention instance #3 (FP-B004-LOG1):** "**92% win rate**" = 12W/(12W+1L) with **5 BE and
  1 Removed excluded** — the flats-excluded convention again (joins FP-JOURNAL-001 + FP-RECAP-001);
  log rows carry NO entry/SL prices → **0 new stop-width samples** (stated, not guessed). Overlap rows
  (26-02/27-02/02-03) are consistent with FP-RECAP-001. **STRENGTHENS R6 lane-5.**
- **NEW watch item (FP-B004-LOG1):** a "**Bot Trade Log** — first signal coming soon" lane announced
  (Feb/Mar 2026). Provenance/lane-separation watch only; nothing for Orange to act on. **WATCHLIST.**
- "I don't like to trade Monday in Asia" (Jul-5 + Z2) — R4b-adjacent discipline. **ALREADY/STRENGTHENS.**

## 8. Classification summary
- **ALREADY_IN_ORANGE:** fresh/spent doctrine (F2/F3); stop above structural FVG anchor; EDU-028 OTE
  stop rule; Monday-Asia discipline; multi-TF close stack.
- **STRENGTHENS_EXISTING_FEATURE:** displacement_fvg_artifact_test (verbatim design support);
  mitigation-depth capture (+50%-of-zone anchor); untested-level magnet; strong-OB rubric (HTF>LTF,
  freshness); indicator semantics + alert mapping (Jul-5 update, ORB times, POC/VAH/VAL, VWAP
  confluence); limit-at-zone doctrine (documentary); R6 lane-5 claim conventions (instance #3);
  8D layering/one-shared-SL; R2 re-entry-after-scratch.
- **NEW_PROMISING_FEATURE (capture-first, never scored):** `fvg_claim_chain`;
  stop-width causal driver (unmitigated-level proximity / sweep risk); `stop_feasibility_note`;
  flat-candle + gap level classes; `scratch_mode=DOCTRINE_ANTICIPATED` capture value.
- **WATCHLIST_FEATURE:** `london_us_session_break_priors`; bot-lane provenance watch.
- **NEEDS_FORWARD_EVIDENCE:** all of the above before any scoring use; EDU-035 numeric displacement
  still missing.
- **NEEDS_HUMAN_REVIEW:** none blocking.
- **REJECTED_OR_DUPLICATE:** FP-B004-Z1 (guest EMA scalping session — off method family, sizing
  content excluded); all duplicate file copies; Exochart/Delta/OI series.

## 9. Verdicts
**Detector v0.3: SUPPORTED, labels unchanged. Detector v0.4/v0.5 backlog: STRENGTHENED**
(displacement support + fvg_claim_chain candidate; all offline; mitigated_level_exclusion ratification
gate unchanged). **Lane 6: STRENGTHENED** (panel additions, ORB times, magnets, stop-feasibility).
**R6: STRENGTHENED** (anticipatory-BE doctrine collapses part of the 8C interpretation question;
lane-5 conventions; limit evidence). **stop_width_by_level_type: STRENGTHENED → v0.2 research inputs**
(new causal driver; 0 new numeric samples). **Human ratification: not required now** — nothing
proposed for scoring. **No OHLC matching run. No v0.4 live use. Nothing promoted.**

## 10. Safety attestation
Observation-only. Listener PID 23012 untouched (verified at every gate); transcription wrote only
under `derived/transcripts/batch_004/`; no execution built (broker/QST/cTrader/nano/copy/demo/live
absent); no permits/leases/orders; gates `PAPER/PREVIEW/False/False`; no TradingView/Worker/R2/secret
action; all sizing/lot/fee content in sources EXCLUDED (claim-context only); no order fields.
`NOT_INTEGRATION_READY` unchanged.

## 11. Next exact step
**Cycle 006 / XAU-F001 at the first real XAU post after tonight's ~22:00Z reopen** under the full
8C+8D+8F+001B+002B+003B spec (+ the Batch-004 capture notes). Offline queue: fold the
MERGE_NOW_CAPTURE_ONLY items (see merge queue) at the next capture-spec touch; optional Feb–Mar 2026 +
May OHLC matching; v0.4 forward re-replay after ≥15 XAU-F records.
