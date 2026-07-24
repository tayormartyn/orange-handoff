# Farouk Campaign State Machine — Spec v0.1

**Mode: OFFLINE, OBSERVATION-ONLY.** Deterministic. No broker/cTrader/QST/execution, no permit/lease/order,
no gate change, no trade instruction. `NOT_INTEGRATION_READY` unchanged.

## Purpose

Convert a captured/classified Farouk alert + resolved context evidence into an **observation-only campaign
state**. The machine makes the **Human Review Batch 001 lessons executable and deterministic** — given the
same evidence facts it always yields the same campaign state, and it reproduces the three reviewed verdicts
(HR-0001 → LOW, HR-0002 → WATCH, HR-0003 → REJECT). It **cannot** emit anything tradeable.

## States

Process/context: `IDLE`, `ALERT_CAPTURED`, `CLASSIFIED`, `CONTEXT_PENDING`, `HTF_CHECK_PENDING`,
`HTF_ALIGNED`, `HTF_OPPOSED`, `LIQUIDITY_SWEEP_CONFIRMED`, `STRUCTURE_CONFIRMED`, `POI_CONFIRMED`,
`CONTRADICTION_FOUND`.

Classification (terminal label): `SHADOW_CANDIDATE_MEDIUM`, `SHADOW_CANDIDATE_LOW`, `WATCH_ONLY`,
`SHADOW_REJECTED`.

Lifecycle: `OUTCOME_TRACKING`, `HUMAN_REVIEW_REQUIRED`, `REVIEWED`, `JOURNALLED`.

## Transition walk (deterministic)

1. `IDLE → ALERT_CAPTURED → CLASSIFIED → CONTEXT_PENDING` (always, once an alert+classification exist).
2. Context confirmations (each appended only if the evidence supports it):
   - sweep ∈ {PRESENT, CONFIRMED} → `LIQUIDITY_SWEEP_CONFIRMED`
   - structure_choch == CONFIRMED and **not** choch_in_chop → `STRUCTURE_CONFIRMED`
   - order_block == FRESH → `POI_CONFIRMED`
3. `HTF_CHECK_PENDING` → `HTF_ALIGNED` (htf ALIGNED) or `HTF_OPPOSED` (htf OPPOSED).
4. contradiction → `CONTRADICTION_FOUND`.
5. **Classification** via the ordered decision rules below → one terminal label state.
6. Lifecycle: if outcome known → `OUTCOME_TRACKING`; candidate/WATCH → `HUMAN_REVIEW_REQUIRED`;
   if a human_review verdict is supplied → `REVIEWED → JOURNALLED`; a `SHADOW_REJECTED` with no review is
   journalled directly.

## Decision rules (first match wins) — encoding the batch-001 lessons

Let `ob_valid = FRESH`, `ob_breached = FRESH_BREACHED`, `ob_dead = MITIGATED_SPENT`;
`choch_ok = CONFIRMED & not chop`; `choch_weak = WEAK or chop`; `sweep_ok = PRESENT|CONFIRMED`;
`outcome_bad = UNFAVOURABLE`; `disp_against = displacement AGAINST`; `htf_opposed/htf_aligned`.

1. **SHADOW_REJECTED** if `ob_dead and (contradiction or outcome_bad or disp_against)`, or
   `contradiction and outcome_bad`, or `disp_against and outcome_bad`.
   *(Lesson: spent/mitigated OB, a signal against effective bias, or displacement against the trade — with
   an adverse outcome — is an invalidated thesis, not a candidate.)*
2. **WATCH_ONLY** if `ob_breached`, or `ob_dead`, or `choch_weak and outcome_bad`, or
   `htf_opposed and outcome_bad and not ob_valid`.
   *(Lesson: a fresh-but-breached OB or a spent OB is not a valid POI; weak CHoCH-in-chop with a bad outcome
   is context, not a candidate.)*
3. A candidate REQUIRES `ob_valid and sweep_ok`; otherwise **WATCH_ONLY** (insufficient confluence).
4. **SHADOW_CANDIDATE_MEDIUM** only if `ob_valid and sweep_ok and choch_ok and htf_aligned and not
   contradiction and not outcome_bad and not disp_against`.
   *(Lesson: HTF alignment is the gate to MEDIUM; a weak/chop CHoCH can never reach MEDIUM.)*
5. **SHADOW_CANDIDATE_LOW** if `ob_valid and sweep_ok and not outcome_bad` (capped below MEDIUM because HTF
   is not confirmed-aligned, or the CHoCH is weak).
6. Else **WATCH_ONLY**.

## Batch-001 lessons → rules mapping

| Lesson | Rule |
|---|---|
| HTF alignment is a major gate | MEDIUM needs `htf_aligned` (rule 4); `htf_opposed` caps at LOW (rule 5) / can WATCH (rule 2) |
| OB presence alone is insufficient | candidate needs OB **FRESH** *and* sweep (rule 3), not just any OB |
| Fresh-but-breached OB downgrades | rule 2 `ob_breached → WATCH_ONLY` |
| Spent/mitigated OB downgrades/rejects | rule 1 (with adverse) → REJECT; rule 2 (alone) → WATCH |
| Weak CHoCH in chop ≠ strong candidate | `choch_ok` excludes chop; rule 4 unreachable → at most LOW |
| Signal against effective bias downgraded | `contradiction` / `disp_against` feed rules 1–2 |
| No candidate is trade-ready | `trade_ready` hard-wired False; all exec flags False |

## Guarantees

Deterministic (no time, no randomness, no I/O). Every output is candidate-only / observation-only with all
execution flags hard-wired False. **No broker/account/lot/order/route/risk-sizing/permit/lease field can
appear** — enforced by a fail-closed guard (`_assert_no_execution_surface`) that rejects any such key unless
it is an explicit negative safety flag equal to False. `emits_execution()` is `False` by construction.
The module never reads or writes execution gates and does not change `NOT_INTEGRATION_READY`.
