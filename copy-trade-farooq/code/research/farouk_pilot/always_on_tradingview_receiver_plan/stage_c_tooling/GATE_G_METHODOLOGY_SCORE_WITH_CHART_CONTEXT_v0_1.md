# Gate G — Methodology Score WITH Chart Context v0.1

**Mode:** OFFLINE. The chart-context proxies were fed into `farouk_methodology_scorer_v0_1` via a simple
offline adapter (no live integration). **Candidate-only; no label is trade-ready.**
`NOT_INTEGRATION_READY` unchanged.

## Adapter (offline)

Maps extractor proxies → scorer `context` fields, **conservatively**:
- `displacement` = True only if `displacement_candidate`; else None (missing).
- `fvg` = True only if `fvg_candidate`; else None.
- `session_context` = **None** (a `*_UTC_PROXY` is not a confirmed session — TIMEZONE_POLICY_UNCONFIRMED).
- `order_block` = **None** (not claimed at v0.1).
- `telegram_confirmation`, `alert_grade` = None.

## Before vs after chart context

| candidate | score (alert-only) | label (alert-only) | score (+ context) | **label (+ context)** |
|---|---|---|---|---|
| ALIGNED_CHOCH_TO_A | 0.275 | SHADOW_CANDIDATE_LOW | 0.375 | **SHADOW_CANDIDATE_LOW** |
| SWEEP_TO_CHOCH_CONTEXT | 0.370 | SHADOW_CANDIDATE_LOW | 0.590 | **SHADOW_CANDIDATE_LOW** |
| BPR_TO_A_CONTEXT | 0.180 | WATCH | 0.400 | **SHADOW_CANDIDATE_LOW** |

All three: candidate_only=true; execution / broker / qst / order_intent / risk_sizing = **false**.

## What changed and what didn't

- **Scores rose** (FVG proxy for all; displacement proxy for 2 of 3). BPR_TO_A moved WATCH → LOW.
- **No label exceeded `SHADOW_CANDIDATE_LOW`.** Even SWEEP_TO_CHOCH at 0.59 (a MEDIUM-band score) is
  **capped to LOW** because: (a) required context still missing — `session_context` unconfirmed and
  `order_block` not claimed → cap at MEDIUM; and (b) outcome not FAVOURABLE (MIXED/UNFAVOURABLE) → cap at
  LOW. The caps did their job: proxies help the score but cannot manufacture readiness.
- **Nothing is trade-ready.** The ceiling `METHODOLOGY_ALIGNED_SHADOW` remains unreachable while session
  is unconfirmed and OB/HTF are absent — and would still be observation-only if reached.

## Honest reading

Chart-context proxies close *some* of the gap (FVG/displacement), but the two hardest blockers —
**confirmed session (timezone)** and **order block** — are exactly the ones still missing, plus HTF bias.
Proxies are `NEEDS_HUMAN_REVIEW`; they are not evidence of an edge.

## Safety confirmations

- Candidate-only; no execution / order / broker / lot / account / risk / permit / lease.
- Offline; no broker/cTrader/QST; no deploy.
- **`NOT_INTEGRATION_READY` unchanged.**
