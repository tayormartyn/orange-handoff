# HTF Bias Resolver v0.1 — Report

**Mode:** OFFLINE HTF CONTEXT. Aggregates imported 1m OHLC into 15m/1h bars and computes a proxy
directional bias. **Observation-only; PROXY only.** No live download, no broker/QST, no deploy.
`NOT_INTEGRATION_READY` unchanged.

## Files

- `htf_bias_resolver_v0_1.py` — the resolver (pure compute; CSV read only in `__main__`).
- `test_htf_bias_resolver_v0_1.py` — tests (synthetic OHLC).

## Corpus grounding (why it is strictly a PROXY)

The corpus defines **no exact SMC HTF-bias rule**: "which EMA / what bias definition" is unresolved
(`comparisons/FP-OFFICIAL-DOCS-vs-CAMPAIGNS-001-002-003.json`; `FAROUK_LEVEL_CONSTRUCTION_SPEC_v0.2.md:73`).
The only concrete EMA period (1H / 50 EMA) belongs to a **separate, RESEARCH_ONLY "Vishal" method — not
the SMC state machine** (`FAROUK_METHODOLOGY_RULE_LEDGER_v0.3.jsonl:20`, R-EMA-METHOD). So this resolver
uses a documented default EMA (20) purely as a proxy and **never claims a confirmed Farouk HTF bias**
(`confirmed_farouk_htf_bias=false`, note `NEEDS_HUMAN_REVIEW`).

## Output

`htf_bias_proxy` ∈ {`BULLISH_PROXY`, `BEARISH_PROXY`, `NEUTRAL_OR_INSUFFICIENT_DATA`}, plus per-timeframe
`bias_15m_proxy` / `bias_1h_proxy`, `close_minus_ema_*`, `bars_15m` / `bars_1h`, warnings, and the safety
block (all execution flags false).

## Method (proxy)

- Aggregate 1m → 15m and 1h buckets (floor to bucket start).
- Proxy EMA (period 20) on closes up to the anchor; bias = last close vs EMA.
- Need ≥ 22 aggregated bars per timeframe; else `NEUTRAL_OR_INSUFFICIENT_DATA` + warning.
- Combined: agreeing 15m & 1h → that bias; one-sided sufficiency → that timeframe (flagged weak);
  disagreement/insufficient → NEUTRAL.

## Test results — ✅ PASS

`python test_htf_bias_resolver_v0_1.py` → **5 tests, OK.** Covers: 1m→15m/1h aggregation counts; rising
data → BULLISH_PROXY; falling data → BEARISH_PROXY; too-short window → NEUTRAL_OR_INSUFFICIENT_DATA +
warning; all safety flags false.

## Applied to Gate G (see replay report)

The single ~11.6h window is **too short for a robust 1h EMA** — 1h had only 8–13 bars (< 22), so every
1h proxy = `NEUTRAL_OR_INSUFFICIENT_DATA`. 15m had enough (29–51 bars). Combined proxies fell back to
the 15m read (flagged weak). **These proxies are descriptive context, NOT fed into the methodology score**
(the corpus has no HTF rule to weight).

## Safety confirmations

- Candidate-only; no execution / order / broker / lot / account / risk / permit / lease.
- Offline; no broker/cTrader/QST; no live download; no deploy.
- **`NOT_INTEGRATION_READY` unchanged.**

## Status

v0.1 — implemented, tested (5/5). HTF remains a proxy; a confirmed HTF-bias factor is blocked until the
corpus defines the rule.
