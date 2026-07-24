# Farouk-Plus Shadow Engine — Review-Only Next Steps

**Scope guard:** every task below is **review-only / observation-only**. No broker route, no lot size, no
account id, no risk sizing, no trade instruction, no order intent, no execution of any kind. Deterministic
validators + OHLC matching remain the authority; AI output stays behind the ai_review fail-closed validator.
Gates untouched; `NOT_INTEGRATION_READY` unchanged. "Shadow" = paper-record of *what the rules would have
flagged*, never an instruction.

## The fastest safe path (ordered; each step is offline unless marked)

### Step 1 — Winner/loss comparison table (offline, ~half day)
Build `farouk_plus/winner_loss_comparison_v1.json` from the 33-trade matched sample (Day-2/4/5 JSONs +
Day-1/3 ledgers): per trade — session window, attempt number that day, direction vs HTF drift, time-to-±50p,
MFE/MAE, zone type (from his stated reason), claim-vs-achievable delta. This is pure joining of data we
already have.

### Step 2 — Setup rule extraction (offline)
From Step 1, formalise the candidate rules the evidence already suggests as testable predicates:
- **R1 first-touch rule**: entry only on first touch of the pre-marked zone that day.
- **R2 attempt cap**: skip attempt ≥3 of the same idea (would have filtered both verified SL losses J10, J17).
- **R3 displacement deadline**: if +50p doesn't print within N minutes (fit N from winners: ~5–40 min),
  treat as invalid — matches his own best manual cuts (J03, J08).
- **R4 session filter**: London 08:30–11:30Z + NY 13:30–15:30Z only (fit exact edges from data).
- **R5 HTF veto**: no counter-trend fade at fresh extremes without a stated HTF level (S2, J23 filter).
- **R6 claim discount**: expectancy is computed on TP1/TP2 (50/100–130p) + scratch modelling, never on
  runner claims (J30/S1 inflation).
Backtest each predicate against the 33 matched trades: which losses filtered, which winners kept. Output:
`FAROUK_PLUS_RULESET_v0_1.md` with per-rule hit/miss tables.

### Step 3 — Farouk-plus filter discovery (offline, AI-assisted, review-only)
Use the ai_review lane (validator-stamped) to sweep the 273 June + 269 July gold-trades messages for
features not yet coded (news windows, his own "don't risk profit" warnings, lot-size warnings as volatility
proxies, poll/education days vs trade days). Every extraction passes `validate_reviewer_output`; anything
touching execution vocabulary is rejected by design.

### Step 4 — Shadow candidate detector refinement (offline replay)
Extend `shadow_candidate_detector_v0_1.py` with R1–R6 as *scoring features* (not gates), replay it over the
captured evidence window, and diff its candidates against the 33 known outcomes:
precision/recall per rule combination. Output: `GATE_G_SHADOW_CANDIDATE_REPLAY_v0_2.md`.

### Step 5 — Forward monitoring checklist (live listener, no changes to it)
Daily (uses only what PID 87988 already captures):
1. New XAU setup posted? → append to the forward ledger (same schema as Day-1) same day.
2. Screenshots captured? (media lane is live) → link sha256s.
3. TV alert sequence aligned? → record CHoCH/Sweep/A ids if the indicator fired around the entry.
4. Same-day 1m OHLC export request queued for Martyn (one file per active day, "Go to date" method).
5. Deterministic match within 48h → update the cumulative scoreboard (target: ≥15 forward-matched trades).
6. Any setup where claim vs match diverges → straight to human review (HR queue).

### Step 6 — Precision + screenshot debt (as data arrives)
- June 1–21 **1m** re-export → upgrade the 23 fallback verdicts (expect no status flips; TP/SL guards were
  clean — this tightens claim-time numbers only).
- Review the **77 recovered June screenshots** against the ledger (human or vision lane, review-only):
  confirm the platform screenshots corroborate entries/partials where text is thin (J24's missing entry may
  be recoverable from a screenshot).

## Explicitly out of scope (blocked until governance lifts them)
Broker/QST/cTrader connections (even read-only extensions), demo execution, permits/leases/orders, gate
changes, TradingView alert modifications, Worker deployment, webhook secret rotation, any treatment of
Telegram content as an executable signal. Demo-readiness may only be *discussed* once every threshold in
`SPRINT_DAY6_INTERIM_DECISION_REPORT.md` §7 is met.
