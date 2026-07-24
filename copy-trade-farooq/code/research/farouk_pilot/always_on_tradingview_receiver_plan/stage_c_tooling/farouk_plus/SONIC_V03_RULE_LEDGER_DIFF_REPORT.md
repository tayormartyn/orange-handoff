# Sonic v0.3 Rule Ledger ↔ Farouk-Plus Diff Report (Recovery Item 1)

**Mode: RULE LEDGER DIFF ONLY — SINGLE-SESSION.** Observation-only. Date 2026-07-11.
Sources: `synthesis_v0.3/FAROUK_METHODOLOGY_RULE_LEDGER_v0.3.jsonl` (23 rules) +
`CONTRADICTION_ADJUDICATION_v0.1.md` (8 items) diffed against the full current Orange design (ruleset
v0_1, detector v0.2, R6 six-lane model, Lane 6, Cycle-002 schema 8C/8D/8F). Nothing merged into execution;
the merge queue emits review-features only. Machine-readable: `sonic_v03_rule_ledger_diff.json` +
`farouk_plus_rule_merge_queue_v0_1.json`. Gates unchanged; `NOT_INTEGRATION_READY` unchanged.

## 1. Tally (23 Sonic-era rules)

| classification | n | rules |
|---|---|---|
| ALREADY_IN_ORANGE | **4** | R-MGMT-TP1-BE (Model B +50 BE arm + 8C capture) · R-MGMT-PARTIAL (lane-4 tranches/8D) · R-NY-1330 (R4b/session policy) · R-INDICATOR-PANEL (8F lineage) |
| PARTIALLY_IN_ORANGE | **4** | R-MGMT-CONTINGENCY · R-CHOCH-NONUNIVERSAL · R-ALERT-BARCLOSE · R-AGRADES |
| MISSING_HIGH_VALUE | **5** | R-STOP-OTE · R-CONFLUENCE-ORDER · R-MITIGATION (touch-count nuance) · R-STRONGWEAK · R-BOS-CANDLECLOSE (with proposed adjudication) |
| MISSING_LOW_VALUE | **3** | R-OTE-FIB · R-VA-68 · R-SCOB-CLOSE (families unobserved in our 34-trade sample) |
| CONTRADICTS | **2** | R-BOS-CANDLECLOSE (EDU-016 vs 021, inherited) · **R-RR-2R (NEW: doc vs observed practice — see §3)** |
| OBSOLETE_OR_REJECTED | **5** | R-RISK-1PCT (out of review-lane scope by no-risk-sizing policy; governance layer) · R-INDUCE-DISPLACE-TRAP (unverified inference) · R-EMA-METHOD (separate family) · R-OI · R-BFI (excluded narratives) |

## 2. High-value merges (queued as REVIEW FEATURES, never gates)

1. **`contingency_pre_declared` flag (from R-MGMT-CONTINGENCY) — refines R2/R2b.** Sonic distinguished
   *pre-declared conditional re-entry at a higher-quality zone* (C004: "if stopped, re-enter 4070–80" —
   exactly J26's 45097 plan) from impulsive re-entry chains (J17). Proposed: a pre-declared contingency
   posted BEFORE the stop exempts the re-entry from the R2b penalty (flag + weight 0→+1, forward-testable).
2. **`zone_touch_count` (from R-MITIGATION + adjudication #4) — first mitigation tradable, repeated =
   spent.** Forward-computable from OHLC; feeds `mitigated_level_wider_invalidation` and Lane-6 pre-mark
   confidence. This is the missing "mitigation depth" surrogate.
3. **STRONG/WEAK added to `level_type_tag` (from R-STRONGWEAK)** — strong high/low = manipulated+BOS+RTO;
   weak = liquidity target. Extends the 8F tag vocabulary; Lane-6 confidence input.
4. **Confluence ORDER (from R-CONFLUENCE-ORDER): BOS > FVG-inversion > Level-reclaim > SFP** — adopted as
   a Lane-6 pre-mark confidence *ordering* (explicitly NOT a minimum count — F_CONFLUENCE_UNKNOWN stands).
5. **Lane-6 repaint guard (from R-ALERT-BARCLOSE)** — indicator marker repaint is UNRESOLVED, so
   pre-marks sourced from indicator levels must use **bar-close-confirmed values only**; extends the
   anti-leakage contract.
6. **R-STOP-OTE ("stop just outside the zone")** — first structural stop-placement rule; input to the
   `stop_width_by_level_type` v0.1 synthesis (recovery item 4).

## 3. Contradictions

- **#1 BOS candle-close (EDU-016 "required" vs EDU-021 "preferred")** — inherited TRUE_CONTRADICTION.
  **New Fable-5 evidence permits a proposed adjudication:** in live practice (video 002) he uses "broke
  Asia low **with a big candle close**" as a strength qualifier, and June narration repeatedly treats
  closes as confirmation-strength, not gates. Proposal: **score candle-close as +confidence (EDU-021
  reading), never a gate** → NEEDS_HUMAN_REVIEW to ratify.
- **#6 all-boxes veto vs graded stack (Playbook-internal)** — unresolved; stays NEEDS_HUMAN_REVIEW;
  detector v0.2's graded scoring implicitly sides with the graded reading (documented, not decided).
- **NEW — R-RR-2R vs observed practice:** the docs teach "target ≥ 2R", but the 34-trade matched sample
  shows tranche-1 exits (~50p) against $20–100 stops run **far below 2R**; only runners occasionally reach
  2R+. Doc-vs-practice divergence → R6 honesty note (expectancy must not assume 2R); NEEDS_HUMAN_REVIEW as
  a finding.
- Confirmations: displacement numeric (blocked, = our R3 rejection), CHoCH non-universal (= our
  family-scope stance), VA-68 window unknown (stays blocked).

## 4. Impact on current rules

| component | change |
|---|---|
| **R2/R2b** | improved: `contingency_pre_declared` exemption flag (queue #1) |
| **R4b** | unchanged — R-NY-1330 independently confirms the NY window our winners cluster in |
| **R6** | honesty note from the 2R contradiction; no formula change |
| **Lane 6** | strengthened 4×: confluence ordering, STRONG/WEAK tags, zone_touch_count, repaint guard |
| stop_width_by_level_type | gains R-STOP-OTE as its first structural input |
| fill_lag_cost / indicator_price_level_extraction | unchanged; R-INDICATOR-PANEL confirms lineage (FP-INDICATOR-005 owns the panel) |

## 5. Safety confirmation

Read + diff only; targets pre-flight-checked; no Step-8*/recovery artefact modified; nothing merged into
execution; no risk/lot/account/broker/ticket fields (R-RISK-1PCT explicitly NOT carried into the review
lane); no permits/leases/orders; gates unchanged; listener PID 87988 running; no
TradingView/Worker/R2/secret action. `NOT_INTEGRATION_READY` unchanged.

## Next step

Ratify the merge queue's NEEDS_HUMAN_REVIEW items (BOS candle-close proposal, all-boxes-vs-graded, 2R
finding) with Martyn; implement the six MERGE_NOW review features in the next detector/Lane-6 iteration;
then recovery item 2 (FP-INDICATOR-001 alert conditions → Lane-6 builder) while awaiting Cycle 002.
