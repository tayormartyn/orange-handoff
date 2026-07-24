# Gate G — Methodology Score WITH Session + HTF v0.1

**Mode:** OFFLINE. Session + HTF proxies fed to `farouk_methodology_scorer_v0_1` via the offline adapter.
**Candidate-only; no label is trade-ready.** `NOT_INTEGRATION_READY` unchanged.

## Adapter decisions (conservative, honest)

- `session_context` → **None** (still): the session is `SESSION_UNCONFIRMED` and Asia is corpus-unsupported,
  so it cannot count as a satisfied factor.
- **HTF proxy → NOT scored:** the corpus defines no SMC HTF-bias rule, so feeding a proxy HTF bias as a
  weighted factor would be inventing weight. HTF is kept as **descriptive context** only.
- FVG / displacement proxies (from the chart extractor) continue to feed as before.

## Scores across the build-up

| candidate | alert-only | + chart-context | **+ session/HTF** |
|---|---|---|---|
| ALIGNED_CHOCH_TO_A | 0.275 / LOW | 0.375 / LOW | **0.375 / SHADOW_CANDIDATE_LOW** |
| SWEEP_TO_CHOCH_CONTEXT | 0.370 / LOW | 0.590 / LOW | **0.590 / SHADOW_CANDIDATE_LOW** |
| BPR_TO_A_CONTEXT | 0.180 / WATCH | 0.400 / LOW | **0.400 / SHADOW_CANDIDATE_LOW** |

All: candidate_only=true; execution / broker / qst / order_intent / risk_sizing = **false**.

## What changed

- **No score change from session/HTF.** Session stays unconfirmed (→ not a satisfied factor) and HTF is a
  proxy we deliberately do not weight. Labels are identical to the chart-context step: **all
  `SHADOW_CANDIDATE_LOW`.**
- The exercise *resolved* session and HTF **as proxies**, but resolving them as proxies correctly did
  **not** unlock anything — precisely because the corpus marks the confirmed versions BLOCKED/UNKNOWN.
- Added signal-quality caution: the ALIGNED CHoCH→A candidate's HTF proxy is **bearish against its LONG
  hint** — a further reason it is not trade-ready.

## Trade-ready?

**No.** Best label remains `SHADOW_CANDIDATE_LOW`. Confirmed session (timezone), order block, and a real
HTF-bias rule are all still missing; outcomes are mixed-to-poor; n=3.

## Safety confirmations

- Candidate-only; no execution / order / broker / lot / account / risk / permit / lease.
- Offline; no broker/cTrader/QST; no deploy.
- **`NOT_INTEGRATION_READY` unchanged.**
