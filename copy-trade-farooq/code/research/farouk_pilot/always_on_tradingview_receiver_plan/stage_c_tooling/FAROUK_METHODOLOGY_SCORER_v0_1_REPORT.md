# Farouk Methodology Scorer v0.1 — Report

**Mode:** OFFLINE METHODOLOGY-SCORER DESIGN + SCAFFOLD. A methodology-aware scoring layer above the
classifier / shadow detector / outcome matcher / journal. **Observation-only; no label means trade-ready;
no broker/action label exists.** No R2, no deploy, no TradingView, no broker/QST. `NOT_INTEGRATION_READY`
unchanged.

## Files

- `farouk_methodology_scorer_v0_1.py` — the scorer (pure function; no I/O).
- `test_farouk_methodology_scorer_v0_1.py` — tests.
- `FAROUK_METHODOLOGY_FACTOR_MAP_v0_1.md` — documented factors → pipeline availability (corpus-cited).
- `FAROUK_METHODOLOGY_SCORING_RUBRIC_v0_1.md` — the six allowed labels + caps.
- `FAROUK_SHADOW_CAMPAIGN_EVIDENCE_SCHEMA_v0_1.md` — evidence record schema.

## What it does

Takes a shadow candidate + classified sequence + optional outcome_stats + optional education-derived
context, and returns: `methodology_score` (0–1 confluence-coverage fraction, **descriptive, not profit
prob**), `score_label` (one of six), `positive_factors`, `negative_factors`, `missing_evidence`,
`disqualifiers`, and the hard-wired safety block (candidate_only=true; execution / broker / qst /
order_intent / risk_sizing = false).

## Design guarantees

- **Only six labels** (`REJECT`, `CONTEXT_ONLY`, `WATCH`, `SHADOW_CANDIDATE_LOW`,
  `SHADOW_CANDIDATE_MEDIUM`, `METHODOLOGY_ALIGNED_SHADOW`) — enforced by an assert. None is trade-ready;
  there is no buy/sell/enter/execute/size/order/broker concept in the code.
- **Ceiling caps:** required context (session/displacement/FVG/order-block) missing → cap at
  `SHADOW_CANDIDATE_MEDIUM`; no favourable outcome → cap at `SHADOW_CANDIDATE_LOW`; grade counted only if
  literally present. **Strong alignment can never be claimed on absent evidence.**
- **Disqualifiers → REJECT:** contradictory direction within the sequence / contradictory cluster.
- **Lone primitive / no direction → CONTEXT_ONLY.**
- `null` context = "not available from pipeline" → `missing_evidence`, never satisfied.

## Test results — ✅ PASS

`python test_farouk_methodology_scorer_v0_1.py` → **8 tests, OK.** Covers: aligned CHoCH→A with
favourable outcome but missing FVG/OB stays shadow-only (not top); contradictory cluster → REJECT/CONTEXT;
A-alone and Sweep-alone → CONTEXT_ONLY (not high); A+ without context not trade-ready; missing evidence
listed; the top label is reachable **only** with full context+favourable yet still carries no execution
permission; all safety flags false / no order-risk-broker keys.

## Grounding

Factor weights and the required-context set come from the repo methodology corpus (see the factor map):
structure/liquidity/OB/FVG/displacement are the high-weight confluence factors; the corpus marks the
geometric thresholds and the grade formula **BLOCKED/UNKNOWN — "do NOT invent"**, and Telegram/Discord as
delivery, not a confluence input. The scorer honours all of that.

## Safety confirmations

- All outputs candidate-only; no execution / order / broker / lot / account / risk / permit / lease field.
- Offline; no broker/cTrader/QST; no deploy.
- **`NOT_INTEGRATION_READY` unchanged.**

## Status

v0.1 scaffold — implemented, tested (8/8). Applied to the 3 journal candidates (see replay report).
