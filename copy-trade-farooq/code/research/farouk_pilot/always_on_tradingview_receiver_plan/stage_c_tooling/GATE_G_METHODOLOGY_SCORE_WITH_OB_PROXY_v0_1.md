# Gate G — Methodology Score WITH OB Proxy v0.1

**Mode:** OFFLINE. OB proxy fed to `farouk_methodology_scorer_v0_1` via the offline adapter, **only as
low-confidence proxy evidence**. **Candidate-only; no label is trade-ready.** `NOT_INTEGRATION_READY`
unchanged.

## Adapter decision

- `order_block` → **True only if `order_block_proxy_found`** (a LOW-confidence, human-review-required
  proxy). Where not found → None (missing).
- `session_context` → None (still unconfirmed); HTF still not scored; FVG/displacement proxies as before.

## Scores across the full build-up

| candidate | alert-only | + chart-context | + session/HTF | **+ OB proxy** |
|---|---|---|---|---|
| ALIGNED_CHOCH_TO_A | 0.275 / LOW | 0.375 / LOW | 0.375 / LOW | **0.375 / SHADOW_CANDIDATE_LOW** (no OB proxy) |
| SWEEP_TO_CHOCH_CONTEXT | 0.370 / LOW | 0.590 / LOW | 0.590 / LOW | **0.690 / SHADOW_CANDIDATE_LOW** |
| BPR_TO_A_CONTEXT | 0.180 / WATCH | 0.400 / LOW | 0.400 / LOW | **0.500 / SHADOW_CANDIDATE_LOW** |

All: candidate_only=true; execution / broker / qst / order_intent / risk_sizing = **false**.

## What changed and what didn't

- **Scores rose** where an OB proxy was found (SWEEP 0.59→0.69; BPR 0.40→0.50). ALIGNED unchanged (no OB
  proxy).
- **No label changed.** All three remain `SHADOW_CANDIDATE_LOW`. Even SWEEP at **0.69** (just under the
  0.70 alignment threshold) is capped to LOW because: (a) **session still unconfirmed** → required context
  missing → cap MEDIUM; and (b) **outcome not FAVOURABLE** → cap LOW. The OB proxy is itself LOW /
  human-review-required, so it should not — and did not — unlock readiness.
- The BPR OB proxy is **mitigated ("spent")** — a *weak*-OB signature — another reason not to lean on it.

## Trade-ready?

**No.** Best label `SHADOW_CANDIDATE_LOW`. Confirmed session, a reviewed (not proxy) OB, a real HTF rule,
graded setups, and adequate sample size are all still missing; outcomes remain mixed-to-poor.

## Safety confirmations

- Candidate-only; OB fed only as LOW-confidence proxy; no execution / order / broker / lot / account /
  risk / permit / lease.
- Offline; no broker/cTrader/QST; no deploy.
- **`NOT_INTEGRATION_READY` unchanged.**
