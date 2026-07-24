# SYNTHESIS FINDINGS

Cross-evidence synthesis across Campaigns 001–004, Education corpus (FP-EDU-001…035), FP-EDU-007 (EMA),
FP-INDICATOR-005 (Farouk's Playbook — Smart Money Suite), [kyle] v1/v2, SpaceMan/Market Cipher B, and the
TradingView alert evidence. Proposal only; no spec overwritten.

## 1. Architecture
A **6-layer model**: (1) Market context (structure/trend-range/session/value/strong-weak), (2) Location objects
(OB/SCOB/FVG/IFVG/BPR/POI/OTE/POC-VAH-VAL/session-HL/liquidity), (3) Event primitives (BOS/CHoCH/sweep/failed-
breakout/inducement/displacement/mitigation/reclaim/rejection/engulfing/Asia-trap/session-cont-rev), (4) Setup
families (11), (5) Composite qualification (A+++/A+ — formula UNKNOWN, not invented), (6) Trade management
(TP1/BE/partials/runner/contingency + LOCKED 1.0% cap).

## 2. Setup families retained (11)
TREND_CONTINUATION, POI_SWEEP_REVERSAL, INDUCEMENT_REVERSAL, SCOB_REVERSAL, STRONG_OB_REVERSAL,
THREE_DRIVE_REVERSAL, RANGE_DEVIATION, POWER_OF_THREE_AMD, NY_REVERSAL, NY_CONTINUATION, SEARCH_AND_DESTROY —
each fully specified (SETUP_FAMILY_SPECIFICATIONS_v0.1.json).

## 3. Promotable now
Management/attribution rules only: TP1→breakeven, partial+runner, the locked 1.0% cap, and the indicator-panel
attribution. **No Alpha ENTRY rule is promotable deterministically** (confluence count + thresholds unknown).

## 4. Family-specific rules
CHoCH-non-universal, OTE Fib 61.8/78.6 + stop-outside-OTE + >=2R, NY 13:30–15:00 UTC, strong/weak levels,
SCOB candle-close, pre-declared contingency — valid within specific families (SCOB/OTE/NY/structure).

## 5. Still blocked
Confluence count, displacement/mitigation numerics, VA-window + POC "T", A+++/A+ formula (threshold), FVG
fill/IFVG, setup expiry (threshold blockers); BOS candle-close + all-boxes-vs-graded (contradiction blockers);
alert payload/timing/repaint + inducement-trap (live-validation blockers).

## 6. Contradictions
2 TRUE (BOS candle-close 016-vs-021; all-boxes-veto vs graded); the rest resolve as family-specific / context-
dependent / terminology / indicator-specific (see CONTRADICTION_ADJUDICATION_v0.1.md).

## 7. Indicator vs discretionary
The indicator supplies OBJECTS + EVENTS + GRADES (observations); qualification-count, family/session choice and
management are DISCRETIONARY. Separate indicators ([kyle], SpaceMan, Market Cipher B, Craters/EMA) not merged.

## 8. Alert-integration implications
Alerts are UNTRUSTED observations. Bar-close firing is user-selectable for named conditions; Any alert() is
script-controlled; payloads are plain text; runtime payload/timing/repaint UNKNOWN → **NOT integration-ready**,
never an authorised trade signal.

## 9. State-machine v0.2
Adds an UNTRUSTED ALERT_INTAKE region (ALERT_RECEIVED → OBSERVATION_VALIDATED → EVENT_DEDUPLICATED →
FAMILY_ADJUDICATED → QUALIFICATION_PENDING → QUALIFIED_CANDIDATE | INVALIDATED) with fail-closed unknowns,
dedup/stale + repaint guards, A+++ != trade, and the v0.1 invariants preserved.

## 10. Next live-validation tasks
P1: A+++ + Any alert() runtime payloads, bar-close-vs-intrabar timing, repaint, duplicates, grade behaviour.
(Then P2 thresholds/terminology, P3 expectancy.) See LIVE_VALIDATION_PLAN_v0.1.md.

## 11. Governance
No detector code; nothing connected to QST; no alert/webhook created; no broker/permit/lease/risk/execution
change; the 1.0% cap and all execution gates unchanged; `FAROUK_METHODOLOGY_SPEC_v0.2.1`,
`FAROUK_STATE_MACHINE_SPEC_v0.1`, dossiers, registers, frozen corpus and indicator evidence NOT overwritten.
