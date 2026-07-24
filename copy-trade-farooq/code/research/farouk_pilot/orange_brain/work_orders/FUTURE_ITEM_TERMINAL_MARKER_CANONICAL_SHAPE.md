# FUTURE ITEM — TERMINAL-MARKER CANONICAL SHAPE (registered 2026-07-21, D-036 condition (b))

Status: **REGISTERED, NOT SCHEDULED.** This is a named future work item with a stated trigger condition, per the operator's acceptance of WIRE_NOMINAL_OPEN option (3).

## Trigger condition (when this MUST be done)
**Required before any increase in demo-lane autonomy beyond per-campaign human approval.** Until this item is built and proven, demo-lane operation (when it exists) stays at per-campaign human approval, and campaigns whose terminals are outcome-based rather than instruction-token-based (currently F002, F004) remain nominally open in `load_campaign_state()`, guarded only by the 18h PROXIMITY window.

## The problem it fixes
`load_campaign_state()` treats a campaign as OPEN unless the latest XAU_F_SETUP revision's `instruction_events` contains `FINAL_CLOSE` / `EXPLICIT_FULL_EXIT`. Campaigns that ended via price outcome (L20/L50 outcome records — F002 stop-out, F004 final TP) have no such token, so they are nominally open forever. The residual risk (accepted with eyes open in option 3): two genuine campaigns arriving within 18 hours of each other while a nominal-open exists → P02 pause noise; the wire FAILS CLOSED (verified from code 2026-07-21: `len(proximate) > 1` → `XAU_F_CAMPAIGN_PAUSE` on every candidate + `FAIL_CLOSED_REVIEW(ambiguous campaign association)` — no order, no state change, loud, never mis-assigns).

## Canonical template
**F006's `XAU_F_TERMINAL_ADJUDICATION` record (fwd ledger, 2026-07-20, D-032)** is the canonical shape: append-only; per-leg terminal states (no smoothing); effective timestamp + price basis; dual evidence (independent bars + hashed corroborating source); defect flag where outcome was defect-affected; statistical-exclusion flag where applicable; written under the four TERMINAL_ADJUDICATION_GOVERNANCE_RULE preconditions + operator approval.

## Scope when triggered
1. Define the marker record type for OUTCOME-based terminals (distinct from adjudication: no defect required — e.g. `XAU_F_TERMINAL_OUTCOME`) carrying the same per-leg/effective-ts/basis fields.
2. Teach `load_campaign_state()` to honour it (append-only ledger growth only; no rewriting of L20/L50 history).
3. Retro-apply to F002/F004 ONLY under governance + operator approval, closing WIRE_NOMINAL_OPEN_OUTCOME_TERMINALS.
4. Re-prove with ledger byte-identity + full replay before deploy (same pipeline as v2/v2.1).

## What is explicitly NOT authorised now
No retro-adjudication of F002/F004 today (blocked by governance precondition (c) — no named defect affected them); no change to `load_campaign_state()`; no new record types written. Registration only.
