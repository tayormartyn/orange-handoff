# Farouk-Plus Ruleset v0.1 — Review-Only Scoring Predicates

**Mode: STEP 2 RULESET FORMALISATION ONLY.** Observation-only. Date 2026-07-11.
**These rules are NOT trade gates.** They are scoring predicates/features for a review-only shadow candidate
detector. Their outputs are review labels for humans; they never produce, imply, or rank an executable
action. Deterministic OHLC matching remains the authority for outcomes; every machine-produced record passes
the ai_review fail-closed validator (`review_only=True, executable=False, trade_ready=False`). Gates
`PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged.

Evidence base: `winner_loss_comparison_v1.json` (33 matched trades: 20 W / 6 L / 7 P; loss sample n=6 —
every adoption below is provisional pending ≥15 forward-captured trades per the Day-6 thresholds).

---

## 1. Rule classifications

| rule | classification |
|---|---|
| R2 attempt cap ≤2 | **ADOPT_AS_SCORING_FEATURE** |
| R2b first-attempt-only (no re-entries) | **ADOPT_AS_SCORING_FEATURE** (stronger weight than R2) |
| R4b no new entries ≥15:30Z | **ADOPT_AS_SCORING_FEATURE** |
| R6 claim-discount / TP1-centric expectancy | **ADOPT_AS_SCORING_FEATURE** (analytic control) |
| MAE management feature | **WATCHLIST_FEATURE** (outcome-side diagnostic — not knowable at entry) |
| R1 first-touch (retrospective 4h definition) | **NEEDS_FORWARD_EVIDENCE** (rejected as retrospectively defined; re-testable only with forward pre-marked levels / TV alerts) |
| R3 50p displacement ≤60min deadline | **REJECTED_AS_DEFINED** (zero discrimination: 20/20 W and 5/5 L passed) |
| R5 HTF veto | **NEEDS_FORWARD_EVIDENCE** (1–1 on this sample; a veto would have removed winner J29; Farouk's own control is size-reduction) |

## 2. Formal predicates (evaluable at signal time unless noted)

- **R2 — attempt cap:** `attempt_number(campaign_id, setup) <= 2`. `attempt_number` = 1 + count of prior
  entry announcements for the SAME campaign (same/near-identical zone or an explicit "re-enter"/"re-entry"
  reference) on the same trading day. Evidence: breach cost = verified SL loss J17 (attempt 5); kept winner
  J29 is the known cost of the stricter R2b.
- **R2b — first attempt only:** `attempt_number == 1` (equivalently `re_entry_flag == False`). Evidence:
  removed ALL 3 re-entry losses (J08, J10, J17 ≈ 450–700p avoided) at the cost of 3 winners
  (J14, J19, J29 ≈ 380p TP1-centric).
- **R4b — late-day cutoff:** `entry_time_utc.time() < 15:30Z` (flag `after_1530z_flag == False`).
  Evidence: removed losses J03 + J17 and one scratch, cost one ~53p winner (J06).
- **R6 — claim discount (applies to RESULT review + expectancy math, not entry scoring):**
  `claim_discounted_pips = min(claimed_pips, achievable_pips)` where `achievable_pips` comes from the
  deterministic matcher's achievable-fill logic; `inflation_ratio = claimed_pips / max(achievable_pips, 1)`.
  Expectancy is computed ONLY from TP1/TP2-structure outcomes + scratch modelling — never from runner claims.
  Evidence: J30 (+33–56%), S1 (+8%), J11 (fill-dependent).
- **MAE management feature (outcome-side, replay/monitoring only):** `mae_pips_from_mid` measured by the
  deterministic matcher; historical separation W median 70p vs L median 284p. Used for replay diagnostics,
  expectancy modelling, and forward drift monitoring — never as an entry-time score (not knowable then).

## 3. Measurable fields (required on every scored record)

`setup_id`, `campaign_id`, `attempt_number`, `first_attempt_flag`, `re_entry_flag`, `entry_time_utc`,
`after_1530z_flag`, `claimed_pips`, `achievable_pips`, `claim_discounted_pips`, `TP1_reached`,
`MFE` (pips, from zone mid), `MAE` (pips, from zone mid), `outcome_status` (from the deterministic matcher
ONLY: VERIFIED_WIN / VERIFIED_LOSS / PARTIAL / CONTRADICTED / AMBIGUOUS_INTRABAR / INSUFFICIENT_DATA).

## 4. Review-only scoring model v0.1

1. **baseline_candidate** — a parsed setup with direction + numeric zone + SL that passed the deterministic
   evidence validators. Baseline label: `WATCH`, score 0.
2. **risk_reduction_flags** (+1 each): `first_attempt_flag` (R2b) · `not after_1530z_flag` (R4b).
3. **tail_risk_flags** (−1 each): `attempt_number >= 3` (R2 breach, −2 instead of −1) · `re_entry_flag` ·
   `after_1530z_flag` · counter-trend note present (R5 watch signal — flag only, weight 0 until forward
   evidence; recorded, not scored).
4. **claim_quality_flags** (result-side, do not alter the entry score; route to review):
   `inflation_ratio > 1.25` on any prior claim by the same poster window → `claim_quality=DEGRADED`.
5. **confidence_modifier** = sum of flag weights.
6. **final review label** (the ONLY outputs the model may emit):

| score | label |
|---|---|
| ≤ −2 | `REJECT` |
| −1 … 0 | `WATCH` |
| +1 | `SHADOW_CANDIDATE_LOW` |
| ≥ +2 | `SHADOW_CANDIDATE_MEDIUM` |
| any contradiction, ambiguity, missing field, or DEGRADED claim quality | `HUMAN_REVIEW_REQUIRED` (overrides) |

Caps: no label above `SHADOW_CANDIDATE_MEDIUM` exists in v0.1; nothing skips the existing HR process
(HUMAN_REVIEW_QUEUE); labels expire — a label is void once the entry window passes (no retro-labels
presented as live).

## 5. Forbidden outputs (fail-closed)

The scoring model MUST NOT emit — and the ai_review validator rejects any record containing — fields or
labels matching: **TRADE_READY, EXECUTE / EXECUTION, ORDER, LOT_SIZE / LOT, BROKER_ROUTE / BROKER,
ACCOUNT_ID / ACCOUNT, RISK_SIZE / RISK, QTY, POSITION_SIZE, PERMIT, LEASE, CTRADER, QST, TRADE_NOW, ROUTE.**
(Superset of `ai_review.schema.FORBIDDEN_KEY_SUBSTRINGS` — the validator remains the enforcement point;
every scored record is stamped `review_only=True, executable=False, trade_ready=False` by the validator,
never by the producer.)

## 6. Safety confirmation

Documentation/formalisation only — no code executed against live systems, no execution built, no gates
touched, listener PID 87988 untouched, broker/QST/cTrader absent, no permits/leases/orders,
`NOT_INTEGRATION_READY` unchanged.

## Next step

Step 3 — AI-assisted filter sweep of the captured June+July gold-trades messages (through the ai_review
validator) for features not yet coded; then Step 4 — shadow candidate detector v0_2 replay with this
ruleset as scoring features, diffed against the 33 known outcomes.
