# ORANGE — MASTER SOURCE OF TRUTH
**As of 2026-07-11 (evening). Single durable status file — read this first in any new session
(ChatGPT / Fable / Gemini / Claude / local). Machine-readable twin: `orange_master_source_of_truth.json`.
Update discipline: extend/re-issue with a new as-of date; never let two sessions write farouk_plus
concurrently (single-session rule, standing since the Step-8 collision).**

## 1. Mission
Build **Orange**: a Farouk-plus XAU intelligence/shadow engine. Learn Farouk's (SeaScalper/Whaleroom)
method from evidence; **separate his private execution edge from the follower-capturable edge**; test
whether Orange can pre-mark his levels before the Telegram post and beat late-following. Everything is
**observation/review-only** — Orange produces review labels and research, never trades.

## 2. Safety state (verified this session)
Broker/QST/cTrader/nano/copy execution: **absent**. Permits/leases/orders: **none**. Gates:
`MODE=PAPER / LISTENER_MODE=PREVIEW / EXECUTION_ENABLED=False / CTRADER_EXECUTION_ENABLED=False`.
**`NOT_INTEGRATION_READY` unchanged.** Labels capped at REJECT / WATCH / SHADOW_CANDIDATE_LOW /
SHADOW_CANDIDATE_MEDIUM / HUMAN_REVIEW_REQUIRED (+ PRE_MARK_* set). Enforcement: ai_review fail-closed
validator + extended forbidden-token guard (TRADE_READY/EXECUTE/ORDER/LOT_SIZE/BROKER_ROUTE/ACCOUNT_ID/
RISK_SIZE/COPY_TRADE/NANO/LIVE/DEMO_EXECUTE unwritable) — stamp comes from the validator, never producers.

## 3. Live infrastructure
**Telegram PREVIEW listener PID 87988** (python, started **2026-07-10 21:54:45**) — the ONLY live capture
process; never restart it from a work session (report if dead). Text+photo capture proven live and via
copied-session backfill (image-only, sha256-addressed, append-only). **Forward cursor: msg 45646**
(2026-07-11 06:35:57Z; cycles 001–003 all clean NO_NEW_XAU_SETUP — market closed since Fri close).
TV alert lane: Worker→R2 capture exists (Gate D–H era; alerts fire only when market open); read as
evidence only. His feed = **Vantage** ("XAUUSD-VIP"); our deterministic reference = **Pepperstone**
(~$0.5–2 differences observed).

## 4. Historical evidence base
**34 XAU trades deterministically outcome-matched across 18 sessions: 21 VERIFIED_WIN · 3 VERIFIED_LOSS ·
10 PARTIAL · 0 CONTRADICTED** (June 100% adjudicated; 11 trades 1m-confirmed, 23 on 5m fallback).
"22 trades/2 losers" June claim = PARTIALLY SUPPORTED (convention-dependent). **FP-AUDIT-002 independent
claim-lane: +0.27R to +0.35R per primary gold signal** (22 May–27 Jun; cross-validates the June ledger
row-by-row; +6 pre-capture May trades recovered). **Central caveat: the follower-capturable edge ≠ his
private fills** — his fills are earlier (market-at-decision, Vantage), his stops wider than posted
(taped), so headline claims track HIS book. Expectancy triangulation: literal follower automation ≈ 0
(Model B, +1.4p/trade raw, +25.6 filtered) · managed-credit ≈ +0.3R (~Model A +132p) · truth =
instruction-timing dependent (8C capture decides).

## 5. Detector status
**v0.3 = active forward scorer** (with **v0.2 computed in parallel per record** — forward A/B).
v0.3 in-sample replay: **MEDIUM tier 14 = 11W/0L/3P (zero-loss top tier)**; all 6 losses at LOW or below;
no winner rejected; driver = F2 zone_touch_count. v0.2 artefacts preserved. **v0.4 = backlog only**
(layering-cap flag, displacement_fvg_artifact_test, rubric-count input, audit-R scoring [needs
ratification]) — offline replay before any use.

## 6. R6 expectancy model (six lanes + capture add-ons)
Lanes, never merged: **1 Farouk private fill** (widgets) · **2 posted-zone follower** · **3 post-time
follower** (canonical per his own guide: "enter as soon as the signal is published") · **4
management-instruction follower** (where expectancy is computed) · **5 headline claim** (always
discounted; inflation_ratio>1.25 → human review) · **6 Orange pre-mark**. Capture add-ons:
`audit_r_midpoint/low/high` (claim-lane R, capture-only) · `fill_lag_cost` (post-time fill vs
indicator-level first-touch) · **no 2R assumption (ratified)** · **never-widen binds follower lanes
(ratified)** · BE-at-average for layered · tranche schedules 50/30/20 & 30/30+run.

## 7. Lane-6 status
Builder spec v0.1 complete (16 inputs; minimum-evidence rules; $3/overlap match test; leak-free frozen
windows) · **repaint guard active** (bar-close-confirmed indicator values only; untested — no
indicator-sourced pre-mark yet) · alert mapping complete (13 named conditions; A LONG/SHORT via payloads;
panel prices = primary level source) · **active candidates: PM-F001-SELL-4150-4184 (expires Jul-17) and
PM-F002-SUPPLY-4430-4480 (expires Jul-31), both PRE_MARK_OBSERVED, farouk_post_match_status=PENDING**.
Retrospective lane-6 (n=3): levels matched 2/3 but 0 profitable fills — stop-width, not level, is the
binding constraint.

## 8. Training & recovery
Sonic/Claude-4.8 corpus **recovered on disk (~200 artefacts, 33 FP-EDU records) — no re-upload needed**.
Sonic v0.3 rule-ledger diff complete (23 rules; 6 merged as review features). Human ratifications on file:
BOS candle-close = +confidence only · graded confluence stack · no 2R assumption · never-widen (follower
lanes). **Batches 001/001B/002/002B complete** (videos 001–004 + indicator audio + PDFs + audits +
journal). New evidence IDs this era: FP-LIVE-VIDEO-EXPLAINER-001..004, FP-AUDIT-001/002, FP-JOURNAL-001.

## 9. Feature stack (review-only; weights per ruleset v0.1 + merge plans)
R2/R2b re-entry controls (+contingency_pre_declared flag) · R4b late-day cutoff · R6 six-lane expectancy ·
zone_touch_count · STRONG/WEAK level_type_tag (+5-point strong-OB rubric v0.1) · confluence ranking
(tiebreaker) · lane6_repaint_guard · stop_outside_zone · stop_width_by_level_type (dataset: 32 widths
median $20 + 6 May samples + $30–40 spoken anchor; STRONG class $20–85) · fill_lag_cost ·
indicator_price_level_extraction · be_at_average_for_layered · source-exact tranche schedules ·
layering_cap_max3 · displacement_fvg_artifact_test (FVG-presence, no pip threshold) ·
bos_candle_close_confirmed (+confidence) · capture-only: audit_r fields, stop-width anchors, management
timing (8C), leg events (8D), level tags/feed notes (8F).

## 10. Proven / not proven
**Proven (in the checked sample):** Farouk's win/loss record is materially real (0 contradicted; losses
posted live and OHLC-accurate); v0.3 > v0.2 in-sample (zero-loss top tier); the old corpus is not lost;
the forward stack is built and armed. **NOT proven:** v0.3 out-of-sample; lane-6 pre-mark match rate;
true Orange fill lag; broker/demo readiness; whether Orange can match his private execution.

## 11. Demo-readiness blockers (all must clear before the topic is even DISCUSSED)
≥15 forward XAU-F records · ≥5 forward sessions · deterministic OHLC within 48h where possible ·
v0.2/v0.3 forward A/B results · fill_lag_cost measured · pre-mark match/miss evidence · 100% human review ·
no contradiction / unacceptable loss leakage · governance sign-off for any gate change (never implied).

## 12. Next exact actions
1. **Cycle 004** at next market activity (gold reopens Sunday ~22:00Z; first XAU post → **XAU-F001**).
2. Score v0.2/v0.3 in parallel; compare vs PM-F001/PM-F002.
3. Capture: management timing (8C), leg events (8D), stop-width anchors, audit-R fields, level tags,
   fill-lag inputs, indicator levels, feed notes.
4. Request same-day 1m OHLC; deterministic match within 48h.
5. Later: detector v0.4 offline replay; Training Batch 003 (2025-12-14 movs, recap PDF, May OHLC option)
   if the market stays quiet.

**Key files:** ruleset `FAROUK_PLUS_RULESET_v0_1.*` · detector replays `detector_v0_2/_v0_3_replay_results.json` ·
R6 `R6_FOLLOWER_FILL_EXPECTANCY_MODEL_v0_1.*` + expectancy tables v0_1/v0_1b · Lane-6
`LANE6_PRE_MARK_BUILDER_SPEC_v0_1.*` + `lane6_v0_2_update.*` · capture spec `forward_cycle_002_schema_addendum.json`
+ 001B/002B integrations · ledgers `forward_validation_ledger_v0_2.jsonl`, `pre_mark_candidates_v0_1.jsonl`,
`forward_cursor.json` · ratifications `HUMAN_RATIFICATION_RECORD_v0_1.*`, `TRAINING_BATCH_001B_*` ·
history `research/farouk_pilot/MONITORING_RESUME_STATUS.md` (append-only narrative).
