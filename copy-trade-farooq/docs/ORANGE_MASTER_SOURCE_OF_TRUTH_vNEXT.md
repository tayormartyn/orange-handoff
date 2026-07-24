# ORANGE — MASTER SOURCE OF TRUTH (vNEXT)
**As of 2026-07-12 (~11:45Z, Sunday, pre-reopen). Single durable status file — read this first in any new
session (ChatGPT / Fable / Gemini / Claude / local). Machine-readable twin:
`orange_master_source_of_truth_vnext.json`. Supersedes the 2026-07-11 pair (preserved untouched).
Update discipline: extend/re-issue with a new as-of date; never let two sessions write farouk_plus
concurrently (single-session rule, standing since the Step-8 collision).**

## 1. Mission
Build **Orange**: a Farouk-plus XAU intelligence/shadow engine. Learn Farouk's (SeaScalper/Whaleroom)
method from evidence; **separate his private execution edge from the follower-capturable edge**; test
whether Orange can pre-mark his levels before the Telegram post and beat late-following. Everything is
**observation/review-only** — Orange produces review labels and research, never trades.

## 2. Safety state (verified this session, from source)
Broker/QST/cTrader/nano/copy execution: **absent or hard-disabled**. Permits/leases/orders: **none**.
Gates: `MODE=PAPER / LISTENER_MODE=PREVIEW / EXECUTION_ENABLED=False / CTRADER_EXECUTION_ENABLED=False`
(+ `ORDER_SENDING_ENABLED=False / ORDER_MANAGEMENT_ENABLED=False` in demo_executor config).
**`NOT_INTEGRATION_READY` unchanged.** Labels capped at REJECT / WATCH / SHADOW_CANDIDATE_LOW /
SHADOW_CANDIDATE_MEDIUM / HUMAN_REVIEW_REQUIRED (+ PRE_MARK_* set). Enforcement: ai_review fail-closed
validator + extended forbidden-token guard (TRADE_READY/EXECUTE/ORDER/LOT_SIZE/BROKER_ROUTE/ACCOUNT_ID/
RISK_SIZE/COPY_TRADE/NANO/LIVE/DEMO_EXECUTE unwritable) — stamp comes from the validator, never producers.

## 3. Live infrastructure (CHANGED at the 2026-07-12 controlled reboot)
**Telegram PREVIEW listener PID 23012** (python, started **2026-07-12 11:18:08Z**, command
`python -u module_a_telegram.py`, logs `data/listener_logs/listener_20260712_131808.out/.err.log`) —
the ONLY live capture process; never restart it from a work session (report if dead). **PID 87988 retired**
(died at the ~10:06Z laptop power-down for heat). The power-down window was recovered by a copied-session
capture-only backfill: store max is **msg 45648** and agrees with the channel. **Forward cursor: msg 45646
(CYCLE_003)** — the two post-cursor messages are non-triggering: **45647 = NON_XAU** (forwarded
navigatorjosh HYPE/Hormuz chatter, photo preserved) and **45648 = IRRELEVANT** (admin newsfeed-channel
notice). Cycles 001–003 all clean NO_NEW_XAU_SETUP (market closed since Fri; reopens tonight ~22:00Z).
TV alert lane: Worker→R2 capture exists (read-only evidence; fires only when market open). His feed =
**Vantage** ("XAUUSD-VIP"); our deterministic reference = **Pepperstone** (~$0.5–2 differences observed).

## 4. Historical evidence base
**34 XAU trades deterministically outcome-matched across 18 sessions: 21 VERIFIED_WIN · 3 VERIFIED_LOSS ·
10 PARTIAL · 0 CONTRADICTED** (June 100% adjudicated; 11 trades 1m-confirmed, 23 on 5m fallback).
**FP-AUDIT-002 independent claim-lane: +0.27R to +0.35R per primary gold signal.** Expectancy
triangulation: literal follower automation ≈ 0 (Model B) · managed-credit ≈ +0.3R (~Model A +132p) ·
truth = instruction-timing dependent (8C capture decides). **Central caveat — now doubly documented:**
the follower-capturable edge ≠ his private fills; his fills are earlier (market-at-decision, Vantage),
his stops wider than posted — **Batch-003 adds the first concrete posted-vs-actual SL gap (~$5, 19-Mar
recap row)**. **Batch-003 also adds FP-RECAP-001** (Feb-17→Mar-27 2026: 25+ trades, 18+W/3L claim
conventions documented) and **+19 stop-width samples, median ~$21 — cross-period match with the existing
~$20** (stop-width structure is stable across quarters and a ~$700 price change).

## 5. Detector status
**v0.3 = active forward scorer** (with **v0.2 computed in parallel per record — forward A/B**), labels
UNCHANGED through Batch 003/003B. v0.3 in-sample replay: **MEDIUM tier 14 = 11W/0L/3P (zero-loss top
tier)**; all 6 losses at LOW or below; no winner rejected; driver = F2 zone_touch_count (**Batch-003:
doctrine-confirmed — "tested so many times → they're gonna lose it"**). **v0.4 = offline backlog only**,
now: displacement_fvg_artifact_test (**loss-backed** by the Jul-1 post-mortem; FVG-presence design,
no pip threshold) · **mitigated_level_exclusion (NEW candidate hard filter — RATIFICATION-GATED before
any scoring use)** · confirmation_tf_hierarchy grading (5m<15m<1H<W, +confidence-only) · layering-cap
flag · rubric-count input · audit-R scoring (needs ratification). **Offline replay before any use.**

## 6. R6 expectancy model (six lanes + capture add-ons)
Lanes, never merged: **1 Farouk private fill** · **2 posted-zone follower** · **3 post-time follower**
(canonical per his own guide) · **4 management-instruction follower** (expectancy lane) · **5 headline
claim** (always discounted; inflation_ratio>1.25 → human review) · **6 Orange pre-mark**. Ratified: **no
2R assumption · never-widen binds follower lanes · claim discount**. Capture add-ons: audit_r fields ·
fill_lag_cost · BE-at-average for layered · tranche schedules 50/30/20 & 30/30+run. **Batch-003
strengthens lane 5** (85%+ = W/(W+L) with MISSED+REMOVED excluded; +3,000p no-entry "win"; "paper trade
but I took it on my real account" = explicit posted-vs-private lane separation) **and lanes 2/3**
(limit-at-zone = "cheat code" doctrine; SL-to-entry at TP1 = routine management).

## 7. Lane-6 status
Builder spec v0.1 complete · repaint guard active (untested — no indicator-sourced pre-mark yet) · alert
mapping complete (13 named conditions). **Batch-003 strengthens the core hypothesis: pre-marking is HIS
OWN workflow** (day-ahead plans, "went to a zone that I marked before", limit-order doctrine) and adds
the **indicator panel-level semantics pack** (boxes/VWAP/POC/VAH/VAL/SFP dots/liquidity-sweep marks/ORB
top-mid-bottom with no-trade-inside-orb/yellow candles) as machine-extractable builder inputs. **Active
candidates: PM-F001-SELL-4150-4184 (expires Jul-17) and PM-F002-SUPPLY-4430-4480 (expires Jul-31), both
PRE_MARK_OBSERVED, farouk_post_match_status=PENDING, untouched through reboot + Batch 003/003B.**
Retrospective lane-6 (n=3): levels matched 2/3, 0 profitable fills — stop-width is the binding constraint.

## 8. Training & recovery
**Batches 001 / 001B / 002 / 002B / 003 / 003B complete.** Batch-003 evidence: FP-B003-01..06 (six
relaunched transcripts: Dec-2025 indicator series ×3, Jun-29 recap, Jul-1 LOSS post-mortem, Jul-2
recovery) + FP-RECAP-001 (WhaleRoom_TradeRecap_1.pdf). Batch-003B merged the five capture-only items
(stop-width extension, SL-gap note, indicator semantics, limit-at-zone doctrine, claim conventions) into
capture schema/research notes ONLY. Sonic/4.8 corpus recovered on disk (~200 artefacts, 33 FP-EDU).
Ratifications on file: BOS candle-close = +confidence only · graded confluence stack · no 2R ·
never-widen (follower lanes). **Ratification queue: mitigated_level_exclusion (before any v0.4 scoring
use; not blocking now).**

## 9. Feature stack (review-only)
As per the 2026-07-11 issue (R2/R2b, R4b, R6, zone_touch_count, STRONG/WEAK tags + strong-OB rubric,
confluence ranking, lane6_repaint_guard, stop_outside_zone, stop_width_by_level_type, fill_lag_cost,
indicator_price_level_extraction, be_at_average_for_layered, tranche schedules, layering_cap_max3,
displacement_fvg_artifact_test, bos_candle_close_confirmed, audit-R capture fields) **plus Batch-003B
capture-only fields:** entry_mechanic_evidence · pre_planned_evidence · posted_sl_price /
actual_stop_evidence / posted_vs_actual_sl_gap_usd · indicator_level_source_kind ·
claim_convention_notes · claim_has_entry_sl. Stop-width dataset now: 32 sprint widths (median $20) +
6 May samples + spoken $30–40 anchor + **19 Feb–Mar 2026 recap samples (median ~$21)**.

## 10. Proven / not proven
**Proven:** Farouk's record materially real in the checked sample (0 contradicted); v0.3 > v0.2
in-sample; corpus not lost; forward stack built and armed; **stop-width median stable across quarters
(Batch-003)**; **pre-marking is his own doctrine (Batch-003)**. **NOT proven:** v0.3 out-of-sample;
lane-6 pre-mark match rate; true Orange fill lag; broker/demo readiness; whether Orange can match his
private execution; the 78–80% Asia-high claim (watchlist).

## 11. Demo-readiness blockers (all must clear before the topic is even DISCUSSED)
≥15 forward XAU-F records · ≥5 forward sessions · deterministic OHLC within 48h where possible ·
v0.2/v0.3 forward A/B results · fill_lag_cost measured · pre-mark match/miss evidence · 100% human review ·
no contradiction / unacceptable loss leakage · governance sign-off for any gate change (never implied).

## 12. Next exact actions
1. **Cycle 004 / XAU-F001 at the first real XAU post after tonight's ~22:00Z gold reopen** (listener
   PID 23012 live) — full 8C+8D+8F+001B+002B+003B capture spec; v0.2/v0.3 parallel labels; PM-F001/
   PM-F002 comparison; same-day 1m OHLC request; 48h deterministic match.
2. Detector v0.4 offline replay (displacement enrichment + mitigated_level_exclusion + TF-hierarchy +
   prior backlog) — offline only; mitigated_level_exclusion additionally ratification-gated.
3. Optional OHLC matching: **Feb–Mar 2026 recap trades (tests the 85% claim deterministically)** + the
   existing May option.
4. Re-issue this master with Cycle-004 results when XAU-F001 exists.

**Key files:** everything from the 2026-07-11 issue, plus: `ORANGE_CONTROLLED_REBOOT_STATUS.*` ·
`FABLE5_TRAINING_BATCH_003_REPORT.md` + `fable5_training_batch_003.json` +
`fable5_training_batch_003_merge_queue.json` · `TRAINING_BATCH_003B_CAPTURE_ONLY_INTEGRATION.*` ·
ledgers `forward_validation_ledger_v0_2.jsonl`, `pre_mark_candidates_v0_1.jsonl`, `forward_cursor.json` ·
history `research/farouk_pilot/MONITORING_RESUME_STATUS.md` (append-only narrative).
