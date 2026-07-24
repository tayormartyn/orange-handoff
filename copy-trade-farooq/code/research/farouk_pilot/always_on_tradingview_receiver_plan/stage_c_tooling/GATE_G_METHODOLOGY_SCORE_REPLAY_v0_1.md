# Gate G — Methodology Score Replay v0.1

**Mode:** OFFLINE. `farouk_methodology_scorer_v0_1` applied to the 3 outcome-matched Gate G shadow
candidates. **Candidate-only; no label is trade-ready.** `NOT_INTEGRATION_READY` unchanged.

## Results

| candidate_id | type | hint | methodology_score | **score_label** | outcome |
|---|---|---|---|---|---|
| ALIGNED_CHOCH_TO_A-0000 | ALIGNED_CHOCH_TO_A | LONG | 0.275 | **SHADOW_CANDIDATE_LOW** | MIXED |
| SWEEP_TO_CHOCH_CONTEXT-0000 | SWEEP_TO_CHOCH_CONTEXT | LONG | 0.370 | **SHADOW_CANDIDATE_LOW** | UNFAVOURABLE |
| BPR_TO_A_CONTEXT-0000 | BPR_TO_A_CONTEXT | SHORT | 0.180 | **WATCH** | UNFAVOURABLE |

All three: `candidate_only=true`; execution / broker / qst / order_intent / risk_sizing = **false**.

### Per-candidate factors

**ALIGNED_CHOCH_TO_A-0000 — SHADOW_CANDIDATE_LOW (0.275)**
- positive: market_structure (CHoCH), direction_alignment, outcome_support (partial: MIXED)
- missing: grade, session_context, displacement, fvg, order_block, telegram_confirmation
- disqualifiers: none

**SWEEP_TO_CHOCH_CONTEXT-0000 — SHADOW_CANDIDATE_LOW (0.370)**
- positive: liquidity_sweep, market_structure, direction_alignment
- negative: outcome unfavourable
- missing: grade, session_context, displacement, fvg, order_block, telegram_confirmation

**BPR_TO_A_CONTEXT-0000 — WATCH (0.180)**
- positive: bpr, direction_alignment
- negative: outcome unfavourable
- missing: grade, session_context, displacement, fvg, order_block, telegram_confirmation

## Key observations

- **Nothing exceeded `SHADOW_CANDIDATE_LOW`.** Every candidate is missing the four high-weight
  `REQUIRED_CONTEXT` factors (session, displacement, FVG, order block), so the label is capped and the
  gaps are listed. This is the correct, honest result — not a defect.
- **Detector confidence ≠ methodology confluence.** The detector's *MEDIUM* candidate (ALIGNED_CHOCH_TO_A)
  scored the **lowest** methodology confluence of the three eligible (0.275), while the *context-only*
  Sweep→CHoCH scored highest (0.370) because it carries both a liquidity sweep and a structure shift.
  Neither is trade-ready; the two lenses simply measure different things.
- **Outcome and methodology disagree too:** the highest methodology score (Sweep→CHoCH, 0.370) had an
  **unfavourable** outcome. Small-n noise — exactly why more observations are needed.

## Trade-ready?

**No.** Best label is `SHADOW_CANDIDATE_LOW`. The ceiling (`METHODOLOGY_ALIGNED_SHADOW`) is unreachable
with our current evidence and, even if reached, remains observation-only. See
`METHODOLOGY_GAPS_BEFORE_TRADING_v0_1.md`.

## Safety confirmations

- Candidate-only; no execution / order / broker / lot / account / risk / permit / lease.
- Offline; no broker/cTrader/QST; no deploy.
- **`NOT_INTEGRATION_READY` unchanged.**
