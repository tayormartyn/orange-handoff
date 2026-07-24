# Orange v0.3 Rule Merge Plan (Recovery Item 1B)

**Mode: RATIFICATION + MERGE PLAN ONLY — SINGLE-SESSION.** Observation-only. Date 2026-07-11.
Prerequisite: `HUMAN_RATIFICATION_RECORD_v0_1` (all three decisions RATIFIED). This plan defines how the
six MERGE_NOW features fold into the next detector/Lane-6 iteration (**detector v0.3**, ruleset **v0.2**).
Nothing here is an execution gate; all features are review-lane scoring/context inputs behind the
ai_review validator + extended guard; labels stay capped at SHADOW_CANDIDATE_MEDIUM; no automatic
promotion. Machine-readable: `orange_v03_rule_merge_plan.json`. Gates `PAPER/PREVIEW/False/False`;
`NOT_INTEGRATION_READY` unchanged.

## 1. The six features (behaviour, targets, weights, risks)

### F1 `contingency_pre_declared` — R2/R2b exemption flag
- **Source:** R-MGMT-CONTINGENCY (C004; 45097; his own "if stopped, re-enter at…" plans).
- **Behaviour:** a re-entry whose zone was posted BEFORE the prior stop/BE-out, at a same-or-higher-quality
  level, is tagged `contingency_pre_declared=true` and **exempted from the re-entry penalty** (the −1/−2
  R2/R2b weights do not apply); impulsive chains stay penalised.
- **Affects:** RULESET (R2/R2b), detector scoring, Cycle-002 capture (needs the declaring message id+ts).
- **Forward-available:** yes (declaration timestamp precedes the re-entry by definition). Retrospective:
  computable for June/July too.
- **Weight:** **ZERO_WEIGHT_FLAG initially** (record + display), candidate +1 after ≥5 forward cases.
- **Failure mode:** post-hoc rationalisation — a "plan" cited after the fact. Guard: the declaration
  message timestamp MUST precede the stop event (deterministic).

### F2 `zone_touch_count` — first-mitigation-tradable / repeated-spent
- **Source:** R-MITIGATION + adjudication #4; EDU-004/008.
- **Behaviour:** count deterministic zone touches (OHLC intersections) since zone formation *before* the
  entry; `touch_count==1` → confidence +; `>=2` → confidence − (spent level).
- **Affects:** Lane-6 confidence, detector v0.3 (LOW weight), `mitigated_level_wider_invalidation` input,
  Cycle-002 capture (zone formation time needed).
- **Forward-available:** yes (pure OHLC). **Weight: LOW (±1 max).**
- **Failure mode:** zone-boundary ambiguity inflates counts. Guard: touches computed only on posted/
  pre-marked numeric zones; formation time from evidence, never inferred backwards.

### F3 `level_type_tag` extension: STRONG / WEAK
- **Source:** R-STRONGWEAK (EDU-009/004): strong = manipulated + BOS + RTO; weak = liquidity target.
- **Behaviour:** adds STRONG|WEAK to the 8F tag vocabulary; STRONG levels raise Lane-6 pre-mark confidence
  and map to wider stop-width hypotheses; WEAK levels are targets, not entries.
- **Affects:** Lane 6, stop_width_by_level_type modelling, Cycle-002 `level_type_tag`.
- **Forward-available:** yes when structure is taggable from the alert lane/commentary; else UNTAGGED.
- **Weight:** **LOW** in Lane-6 confidence; ZERO_WEIGHT_FLAG in the detector until forward validation.
- **Failure mode:** subjective tagging drift. Guard: tag requires citable structural evidence (BOS id /
  sweep reference), else UNTAGGED.

### F4 `confluence_order_ranking` — Lane-6 confidence ordering
- **Source:** R-CONFLUENCE-ORDER (EDU-024): BOS > FVG-inversion > Level-reclaim > SFP.
- **Behaviour:** when multiple confluences exist on a pre-mark/setup, confidence follows the ratified
  ORDER (graded stack per ratification #2) — explicitly NOT a minimum count (F_CONFLUENCE_UNKNOWN stands).
- **Affects:** Lane-6 confidence; detector v0.3 tiebreaker.
- **Forward-available:** yes. **Weight: LOW (ordering/tiebreaker only).**
- **Failure mode:** treating the ordering as additive scoring → overfit. Guard: ordering breaks ties, never
  sums.

### F5 `lane6_repaint_guard` — bar-close-confirmed indicator values only
- **Source:** R-ALERT-BARCLOSE (repaint UNRESOLVED).
- **Behaviour:** any pre-mark sourced from indicator levels must cite the **bar-close-confirmed** value
  (alert-lane payloads at close, or panel values from a closed bar); intra-bar/repaintable values are
  invalid evidence → `leakage_check_status=LEAK_DETECTED_INVALIDATED`.
- **Affects:** Lane-6 anti-leakage contract (hard validity rule, not a score), Cycle-002 PRE_MARK records.
- **Forward-available:** yes. **Weight: N/A — validity guard.**
- **Failure mode:** none adverse (it removes evidence); residual risk is over-strictness.

### F6 `stop_outside_zone` — first structural input to stop_width_by_level_type v0.1
- **Source:** R-STOP-OTE (EDU-028) + video lessons (wider stop on mitigated levels).
- **Behaviour:** invalidation hypotheses are constructed as *structure-relative* ("just outside the zone /
  beyond the swept extreme") with width parameterised by level type — never fixed dollar constants (the
  8D-A lesson: a $10 constant died where structure-width survived).
- **Affects:** Lane-6 invalidation track, stop_width_by_level_type v0.1 (recovery item 4), R6 follower
  modelling (scratch realism).
- **Forward-available:** yes; retrospective calibration from the 34-setup posted-SL distribution.
- **Weight:** MEDIUM within the invalidation-track research (not a detector score).
- **Failure mode:** widening stops post-hoc to make pre-marks "survive" → guard: width formula frozen
  per level type BEFORE each forward test window.

## 2. Effects on existing components

| component | change in v0.3 |
|---|---|
| **R2/R2b** | + F1 exemption flag (zero-weight first) — doctrine-compliant re-entries distinguished |
| **R4b** | unchanged |
| **R6** | ratification #3 binds: expectancy from actual tranches/posted behaviour/capturable pips; F6 improves scratch realism; no 2R assumptions anywhere |
| **Lane 6** | + F2, F3, F4 confidence inputs; F5 hard validity guard; invalidation track gains F6 |
| **detector v0.2 → v0.3** | + `bos_candle_close_confirmed` (+confidence LOW, per ratification #1) · F1 flag · F2 LOW · F3/F4 as flags/tiebreakers; graded-stack posture now explicit policy (ratification #2) |
| **Cycle-002 schema** | capture additions: contingency declaration ids/ts, zone formation time, STRONG/WEAK tags, confluence list in order, bar-close confirmation source for indicator values |

## 3. Forbidden uses (restated, binding)

No execution of any kind · no broker/QST/cTrader/nano/copy connections · no lot/risk/account/ticket/order
fields (validator + extended guard enforce structurally) · no trade-ready labels (cap stays
SHADOW_CANDIDATE_MEDIUM) · **no automatic promotion** — every weight upgrade (e.g. F1 0→+1) requires a
new human ratification record after the forward-evidence threshold.

## 4. Safety confirmation

Documentation only; targets pre-flight-checked; prior artefacts untouched; no execution built; no
permits/leases/orders; gates unchanged; listener PID 87988 running; no TradingView/Worker/R2/secret
action. `NOT_INTEGRATION_READY` unchanged.

## Next step

Implement detector **v0.3** + Lane-6 update per this plan (offline, replayable against the 34 matched
setups before any forward use), then recovery item 2 (FP-INDICATOR-001 alert conditions → Lane-6 builder);
Cycle 002 continues to wait on gold-trades activity.
