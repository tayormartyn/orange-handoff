# Farouk Campaign State Machine v0.1 — Build Report

**Mode: OFFLINE STATE MACHINE BUILD ONLY.** Observation-only, deterministic. No broker/cTrader/QST/execution,
no permit/lease/order, no gate change, no trade instruction. `NOT_INTEGRATION_READY` unchanged.
Date 2026-07-10.

## Files built

1. `FAROUK_CAMPAIGN_STATE_MACHINE_SPEC_v0_1.md` — states, transition walk, decision rules, lessons mapping.
2. `FAROUK_CAMPAIGN_STATE_SCHEMA_v0_1.md` — input `Observation` + output `CampaignResult` field schema.
3. `farouk_campaign_state_machine_v0_1.py` — pure, deterministic module (`run()`, `_decide()`,
   `emits_execution()`, reviewed fixtures). No imports of broker/execution/config; no I/O.
4. `test_farouk_campaign_state_machine_v0_1.py` — 11 tests (10 required + 1 lifecycle/agreement extra).
5. this report.

## Test results — **11 / 11 PASS**

```
PASS  test_hr0001_ends_shadow_candidate_low
PASS  test_hr0002_ends_watch_only
PASS  test_hr0003_ends_shadow_rejected
PASS  test_htf_opposed_downgrades_candidate
PASS  test_spent_ob_downgrades_candidate
PASS  test_breached_ob_downgrades_candidate
PASS  test_weak_choch_in_chop_cannot_be_medium
PASS  test_no_state_emits_execution
PASS  test_not_integration_ready_unchanged
PASS  test_gates_remain_false
PASS  test_human_review_lifecycle_and_agreement
```

Mapping to the required tests: (1) HR-0001→LOW, (2) HR-0002→WATCH_ONLY, (3) HR-0003→SHADOW_REJECTED,
(4) HTF_OPPOSED downgrades, (5) spent/mitigated OB downgrades, (6) breached OB downgrades, (7) weak CHoCH in
chop cannot be MEDIUM, (8) no state emits broker/demo/live execution, (9) NOT_INTEGRATION_READY unchanged,
(10) gates remain False. Plus (11) reviewed fixtures reach `REVIEWED → JOURNALLED` and the machine label
**agrees** with the human verdict in all three.

## Reviewed-fixture transitions (machine reproduces Batch 001)

**HR-0001 → `SHADOW_CANDIDATE_LOW`** (final `HUMAN_REVIEW_REQUIRED`)
`IDLE → ALERT_CAPTURED → CLASSIFIED → CONTEXT_PENDING → LIQUIDITY_SWEEP_CONFIRMED → STRUCTURE_CONFIRMED →
POI_CONFIRMED → HTF_CHECK_PENDING → HTF_OPPOSED → SHADOW_CANDIDATE_LOW → OUTCOME_TRACKING →
HUMAN_REVIEW_REQUIRED`
reason: *valid POI + sweep but HTF opposed → capped at LOW.*

**HR-0002 → `WATCH_ONLY`** (final `HUMAN_REVIEW_REQUIRED`)
`IDLE → ALERT_CAPTURED → CLASSIFIED → CONTEXT_PENDING → LIQUIDITY_SWEEP_CONFIRMED → HTF_CHECK_PENDING →
HTF_OPPOSED → WATCH_ONLY → OUTCOME_TRACKING → HUMAN_REVIEW_REQUIRED`
reason: *fresh OB breached post-entry → watch only (failed POI).*

**HR-0003 → `SHADOW_REJECTED`** (final `JOURNALLED`)
`IDLE → ALERT_CAPTURED → CLASSIFIED → CONTEXT_PENDING → LIQUIDITY_SWEEP_CONFIRMED → HTF_CHECK_PENDING →
HTF_OPPOSED → CONTRADICTION_FOUND → SHADOW_REJECTED → OUTCOME_TRACKING → JOURNALLED`
reason: *spent/mitigated OB with contradiction / adverse outcome / against-displacement → reject.*

All three match the Human Review Batch 001 final labels (LOW / WATCH / REJECT).

## Safety confirmations

- **No state can emit broker/demo/live execution** — `emits_execution()` is `False` by construction; every
  output is guarded (`_assert_no_execution_surface`) so no broker/account/lot/order/route/risk-sizing/
  permit/lease key can appear (only explicit negative safety flags, all `False`).
- All outputs are **candidate-only / observation-only**; `trade_ready` is always `False`; no candidate can
  become trade-ready.
- Deterministic transitions only (no time, randomness, or I/O).
- The module does not read/write execution gates and does not change `NOT_INTEGRATION_READY`.
- Verified this build: gates `MODE=PAPER`, `LISTENER_MODE=PREVIEW`, `EXECUTION_ENABLED=False`,
  `CTRADER_EXECUTION_ENABLED=False`; no broker/cTrader/QST; no permit/lease/order; Worker pure logging-only
  (not touched this task); Telegram PREVIEW listener PID 16608 running/untouched. `NOT_INTEGRATION_READY`
  unchanged.

## Next step

Wire the state machine into the observation cycle as the **deterministic classification layer** above the
existing classifier → detector → matcher → scorer: feed each newly outcome-matched candidate's resolved
evidence into `run()`, journal the resulting campaign state, and route `SHADOW_CANDIDATE_*` / `WATCH_ONLY`
to human review batch 002. Still observation-only — no broker/QST/execution, no gate change. Begin with the
verified 2026-07-10 H1 A+ and H2 CHoCH-down captures once the Jul-10 OHLC is imported.
