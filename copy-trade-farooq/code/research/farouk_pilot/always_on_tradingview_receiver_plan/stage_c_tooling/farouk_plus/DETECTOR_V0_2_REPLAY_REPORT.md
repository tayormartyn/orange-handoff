# Farouk-Plus Shadow Engine Step 4 — Detector v0.2 Replay Report

**Mode: STEP 4 REVIEW-ONLY DETECTOR REPLAY ONLY.** Offline. Date 2026-07-11.
Listener PID 87988 untouched. Deterministic OHLC outcomes (Days 2/4/5) are the authority — the detector
only emits review labels and is graded against them retrospectively. **All 34 records passed the ai_review
fail-closed validator + an extended forbidden-token guard** (adds copy_trade / nano / live / demo_execute /
trade_ready / broker_route / risk_size …). Four negative checks passed: `copy_trade_flag` key rejected,
`TRADE_READY` label rejected, `lot_size` key rejected by ai_review, and `trade_ready=True` stamp-tamper
rejected (the validator's own stamp keys are exempt ONLY with their safe values). Gates
`PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged; nothing promoted to trade-ready.

## 1. What was scored (entry-time-knowable inputs only)

attempt number (R2/R2b: first attempt +1, re-entry −1, attempt ≥3 additional −2) · time-of-day (R4b:
before 15:30Z +1, after −1) · caution_language (f2∪f4 in the ENTRY message, +1) · reason_stated (f7, +1 on
arrival). **Excluded from scoring:** BE-stop language and MAE (outcome-side), R6 claim-quality
(retrospective-only in this replay — no prior inflation history existed at most June entries). Missing
required fields (no numeric zone / no entry message) → HUMAN_REVIEW_REQUIRED override.

## 2. Label × outcome matrix (34 setups; outcomes retrospective, deterministic)

| label | n | W | L | P | I |
|---|---|---|---|---|---|
| SHADOW_CANDIDATE_MEDIUM | 22 | 16 | 2 | 4 | 0 |
| SHADOW_CANDIDATE_LOW | 1 | 1 | 0 | 0 | 0 |
| WATCH | 6 | 3 | 2 | 1 | 0 |
| REJECT | 2 | 0 | 1 | 1 | 0 |
| HUMAN_REVIEW_REQUIRED | 3 | 0 | 1 | 1 | 1 |

## 3. Headline: how v0.2 handled the 6 losses and 20 winners

| loss | label | correct? |
|---|---|---|
| J17 (verified SL, attempt 5, 16:42Z) | **REJECT** | ✔ caught by R2+R4b stack |
| J10 (verified SL, re-entry, no zone) | **HUMAN_REVIEW_REQUIRED** | ✔ not promoted |
| J03 (manual cut, 15:58Z) | **WATCH** | ✔ not promoted (R4b) |
| J08 (manual cut, re-entry) | **WATCH** | ✔ not promoted (R2b) |
| J23 (manual loss, first attempt, 09:35Z) | SHADOW_CANDIDATE_MEDIUM | ✘ escaped |
| S2 (verified SL, first attempt, 11:29Z) | SHADOW_CANDIDATE_MEDIUM | ✘ escaped |

- **Loss reduction: YES.** Raw ledger exposure = 6 losses among 33 trades; v0.2's promoted tier
  (LOW+MEDIUM, 23 setups) contains only **2 losses vs 17 winners** — promoted-tier loss share drops from
  18% to 9%, catching 4 of 6 losses in lower tiers. The 2 escapes (J23, S2) are first-attempt, mid-day,
  clean-looking setups that simply failed — **no text feature distinguishes them**; that residual is
  irreducible entry risk, which is exactly what the (out-of-scope) sizing/SL mechanics are for.
- **Winner removal: NO.** **Zero winners were REJECTed.** 17/20 winners promoted; the 3 re-entry winners
  (J14, J19, J29) sit in WATCH — downgraded, not excluded (the known R2b cost, softened: **caution_language
  saved J29 from rejection** — its entry message contains "low lot please", lifting the score from −2 to −1).
- Promoted-tier precision: 17/23 = 74% W, 21/23 = 91% non-loss (vs base rates 61% / 82%).

## 4. Feature value in this replay

| feature | contribution | verdict |
|---|---|---|
| R2/R2b attempt scoring | put all 4 re-entry-related losses at WATCH or below; sole driver of the J17 REJECT | **strongest** |
| R4b after-15:30Z | demoted J03 and stacked on J17 | strong |
| caution_language | rescued winner J29 from REJECT; present on 0 losses | useful, small n |
| reason_stated | mild promoted-tier enrichment (5W/0L among promoted) | useful, low weight |
| HUMAN_REVIEW override | correctly absorbed the un-scoreable records incl. loss J10 | working as designed |
| BE-stop / MAE | excluded from scoring (outcome-side) | correctly withheld |

## 5. Do-not-overclaim block

This replay is **in-sample and retrospective**: the features were selected on the SAME 33 outcomes they are
graded against (circularity), the loss sample is n=6, 23 of 33 outcomes rest on 5m-fallback data, and label
"precision" figures are descriptive, not predictive. The honest claims are only: (a) the scoring stack is
implementable from capture-time data; (b) it is directionally loss-avoiding without rejecting winners on
this sample; (c) the fail-closed guards work. Forward validation on ≥15 newly captured trades (Day-6
thresholds) is the only thing that can upgrade these claims.

## 6. Safety confirmation

Offline replay only. 34/34 validator-passed; 4/4 negative checks passed; labels restricted to the five
allowed review values. No broker/QST/cTrader/nano/copy/demo/live execution; no permits/leases/orders; gates
unchanged; listener PID 87988 running (start 2026-07-10 21:54:45 unchanged); no TradingView/Worker/R2/secret
action. `NOT_INTEGRATION_READY` unchanged.

## Next step

**Step 5 — forward monitoring checklist goes live-side (still observation-only):** run the v0.2 scorer daily
over newly captured setups from the existing listener (no listener changes), emit labels into the HR queue,
request same-day 1m OHLC exports, and deterministically match outcomes within 48h — accumulating toward the
≥15 forward-captured trades needed to validate or refute this ruleset out-of-sample. (Step 6 continues in
parallel: June 1–21 1m upgrade + 77-screenshot review as data arrives.)
