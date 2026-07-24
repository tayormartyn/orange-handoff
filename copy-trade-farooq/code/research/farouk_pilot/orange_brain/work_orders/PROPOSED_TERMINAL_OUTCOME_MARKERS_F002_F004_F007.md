# PROPOSED TERMINAL-OUTCOME MARKERS — F002 / F004 / F007 (D-063, awaiting operator approval)

**Status: PROPOSED, NOT WRITTEN. Requires operator approval before any marker enters the forward ledger.**
The terminal-marker code (`live_wire_v3_terminal_marker.py`, sha b160b556fb8792fc) is BUILT and PROVEN (terminal_marker_proof.py 4/4: no-op on current ledger, marker closes exactly its target, malformed marker fails-open). This is the retro-application step it enables.

## Why (recap)
`load_campaign_state` treats a campaign OPEN unless an instruction token (FINAL_CLOSE/EXPLICIT_FULL_EXIT) closes it. F002, F004, F007 all terminated via OUTCOME (P10 BE scratch) with NO token, so they sit nominally OPEN forever, guarded only by the 18h proximity window — the growing nominal-open set (K-052/D-057) that makes P02 pause-noise the expected state under demo operation. `XAU_F_TERMINAL_OUTCOME` is the clean-outcome marker (distinct from `XAU_F_TERMINAL_ADJUDICATION`, which requires a named defect — F006's case).

## Difference from the F006 adjudication (governance)
F006 used `XAU_F_TERMINAL_ADJUDICATION` because its outcome was DEFECT-AFFECTED (PARTIAL_INSTRUCTION_SILENT_LOSS) — the four TERMINAL_ADJUDICATION_GOVERNANCE_RULE preconditions applied. F002/F004/F007 outcomes are CLEAN (no defect; the P10 BE scratch is the true strict-follower result), so they use `XAU_F_TERMINAL_OUTCOME` — which asserts NO adjudication, NO statistical exclusion, NO number change. It ONLY records the already-true terminal so the wire stops treating a finished campaign as open. Expectancy rows are UNCHANGED (F004 +15.18, F007 +5.38, F002 +9.95 all stand exactly as recorded).

## Proposed markers (per-leg states from the tracker, effective at the recorded BE-scratch bar)
```
{"record_type":"XAU_F_TERMINAL_OUTCOME","setup_id":"XAU-F002-20260714","direction":"SHORT",
 "terminal_type":"BE_SCRATCH_OUTCOME","effective_ts_utc":"<bar 1784038380>","basis_price":"4084.58",
 "per_leg_states":[{"leg":"near","price":"4084","FILLED@4084.58 -> BE_SCRATCH"},
                   {"leg":"mid","price":"4089.00","CANCELLED (unfilled)"},
                   {"leg":"far","price":"4094","CANCELLED (unfilled)"}],
 "realized_pips_per_unit":"9.95","defect_affected":false,"statistically_excluded":false,
 "changes_no_number":true,"review_only":true,"executable":false,"observation_only":true}

{..."setup_id":"XAU-F004-20260716","direction":"SHORT","basis_price":"4003",
    "effective_ts_utc":"<bar 1784215260>","realized_pips_per_unit":"15.18", near 4003 FILLED->BE_SCRATCH, mid/far CANCELLED ...}

{..."setup_id":"XAU-F007-20260721","direction":"LONG","basis_price":"4063",
    "effective_ts_utc":"<bar 1784626140>","realized_pips_per_unit":"5.38", near 4063 FILLED->BE_SCRATCH, mid/far CANCELLED ...}
```
(effective_ts values are the recorded terminal bar timestamps; rendered to ISO at write time.)

## Deploy + apply sequence (on approval — NOT executed now)
1. Deploy `live_wire_v3_terminal_marker.py` -> `live_wire.py` at a clean window; restart wire (NO listener touch); banner + cursor + ledger byte-identity checks (the no-op proof guarantees zero behavioural change until markers exist).
2. Append the three `XAU_F_TERMINAL_OUTCOME` records (append-only; dry-run -> apply -> idempotency re-run -> scoped verify, per the F006 executor pattern).
3. Confirm `load_campaign_state` open set -> `[]` (all three closed); WIRE_NOMINAL_OPEN_OUTCOME_TERMINALS register item -> RESOLVED; demo-spec §10 item 4a -> satisfied.
4. Standing: every future outcome-terminal campaign gets its `XAU_F_TERMINAL_OUTCOME` at OUTCOME_FROZEN automatically (wire hook) so the set never regrows.

## CONDITION OF APPROVAL — EXPLICITLY CONFIRMED (operator, 2026-07-21, D-065)
These are `XAU_F_TERMINAL_OUTCOME` records for campaigns that **genuinely closed by outcome** (P10 BE scratch, tracker-confirmed OUTCOME_FROZEN). Explicitly:
- **NOT adjudications.** The TERMINAL_ADJUDICATION_GOVERNANCE_RULE and its four preconditions **do not apply and must not be invoked** — no independent-bar-evidence / hashed-source / named-defect / pre-exclusion test is required or claimed, because nothing is being adjudicated.
- **No named defect** is claimed for any of the three (unlike F006).
- **No number changed** — F002 +9.95, F004 +15.18, F007 +5.38 stand exactly.
- **No exclusion applied** — all three remain in the expectancy row set (F007 keeps its MODEL_ARTEFACT_TERMINAL comparison flag; that flag is unrelated to this marker).
- **No expectancy row affected.** The marker only records the already-true terminal so the wire stops treating a finished campaign as open.
- Written **append-only**, per-leg states cited from the tracker snapshot (above).

## What is NOT proposed
No number changes, no exclusions, no adjudication, no defect claims, no instruction-event fabrication. Constitution v0.1 untouched. APPROVED (D-065) for execution BUNDLED with tonight's 21:00-22:00Z listener-restart maintenance window — not before.
