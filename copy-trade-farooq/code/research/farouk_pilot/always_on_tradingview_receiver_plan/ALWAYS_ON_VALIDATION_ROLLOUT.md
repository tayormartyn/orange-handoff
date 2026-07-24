# Always-On Validation Rollout (§6)

**DESIGN ONLY.** Staged rollout A→J. **No stage past A runs without Martyn's explicit approval of that
stage.** Every stage carries the invariant checks below.

## Per-stage invariants (checked at EVERY stage)

- **No broker/QST/execution path** — receiver import allowlist clean; no outbound trading call.
- **No permits/leases/orders** created.
- **Execution gates False** — `MODE=PAPER`, `LISTENER_MODE=PREVIEW`, `EXECUTION_ENABLED=False`,
  `CTRADER_EXECUTION_ENABLED=False` unchanged.
- **Raw payload captured** byte-exact.
- **UTC timestamps** on `received_at_utc`; provider times stored verbatim.
- **Duplicate handling** works (retries collapse; stored + flagged).
- **No production alert disruption** — Farouk alerts + app/CSV lanes keep working unchanged.

## Stages

### Stage A — Design only  *(this document set; DONE)*
Produce the design docs. No code, no deploy, no endpoint. Exit: Martyn approves option + scope.

### Stage B — Local unit test
Build the receiver logic and test **locally** with manual POSTs (as Stage 1/1B did) — POST-only,
secret path, raw-first, append-only, dedupe, import firewall. No cloud, no TradingView.

### Stage C — Cloud receiver deployed but PRIVATE / UNCONFIGURED
Deploy the function to the cloud in LOGGING_ONLY, with the secret path set but **no TradingView alert
pointing at it yet**. Verify it serves 404/405 correctly to probes and that the import firewall +
storage least-privilege hold. No real traffic.

### Stage D — Manual POST to cloud receiver
Send hand-crafted POSTs to the deployed secret URL (valid path, wrong path, non-POST, oversize).
Verify accept/reject + one append-only record per valid POST + dedupe. Still no TradingView.

### Stage E — One harmless TradingView test alert → cloud receiver
A single NEW harmless test alert (like Stage 2's `LIVE001_WEBHOOK_TEST_STAGE2`) posts to the cloud
receiver. Verify capture + phone notification still fires. Delete the test alert after.

### Stage F — One duplicate Farouk-style test alert (NOT production)
A duplicated Farouk-shaped alert (not a live production alert) posts the JSON payload. Verify parsing,
placeholder resolution, `{{interval}}` = intended chart interval, UTC times. Delete after.

### Stage G — One REAL Farouk alert mirrored, app notifications still ON
Mirror **one** real Farouk alert to the webhook (prefer duplicate-first). Confirm capture **and** that
the app/CSV evidence lane is unaffected. This is the first production-touching step — gated + reversible
(remove the webhook to revert).

### Stage H — Full Farouk alert set mirrored (in batches)
Expand to the remaining Farouk alerts in **small batches**, verifying capture + no disruption at each.
Not all at once.

### Stage I — Parser/deduper reports only
A **read-only** report over the store: counts by event_type/grade/direction, dedupe stats, coverage vs
the CSV/phone lanes, anomalies. Report writes only its own output; imports no engine; makes no decision.

### Stage J — Shadow comparison LATER (out of scope here)
Only after all above, and under the existing shadow-mode safety regime, could captured TradingView
events feed **SHADOW_OBSERVATION_ONLY** analysis. No execution, no archive mutation without its own
gate. Requires separate authorisation.

## Gate between stages

Advancing N→N+1 requires: all invariants green, the stage's specific checks green, and **Martyn's
explicit "proceed to Stage N+1."** Any red invariant halts the rollout and is reported, not worked
around. Any production-touching stage (G, H) is additionally reversible by removing the webhook.
