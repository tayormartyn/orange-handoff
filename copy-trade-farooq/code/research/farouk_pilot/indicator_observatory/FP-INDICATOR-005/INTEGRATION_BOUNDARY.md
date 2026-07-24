# FP-INDICATOR-005 — INTEGRATION BOUNDARY

Scope + hard boundary for the "Farouk's Playbook — Smart Money Suite" alert interface. This is **evidence
documentation only**.

## What was done
- Inventoried + hashed the 10 alert-interface screenshots; transcribed the alert conditions, message payloads,
  and frequency controls (see ALERT_INTERFACE_REGISTER.json/.csv, ALERT_PAYLOAD_FINDINGS.md).

## What was NOT done (hard boundary)
- **No alert was created, edited, or activated.** (The captures show the "Create alert" dialog; the Create
  button was never used by this analysis.)
- **No webhook was created, configured, or pointed anywhere.**
- **Nothing was connected to QST.** The alert conditions (A+++ setup, A+ or better, Sweep low, CHoCH up, …)
  are documented as evidence; they are NOT wired to any detector, order path, or execution gate.
- **No detector code** was written; **no specification** was modified.
- **No order** was sent, amended, cancelled, or managed; the **1.0% campaign risk cap** and all **execution
  gates** are unchanged (all False).

## Conceptual mapping (documentation only — NOT an integration)
The Farouk alert conditions correspond to concepts already in the design-stage state machine
(`FAROUK_STATE_MACHINE_SPEC_v0.1`, not modified):
- **A+++ setup / A+ or better** ~ `QUALIFIED_CANDIDATE` grades (but the confluence COUNT behind them is still
  UNKNOWN → F_CONFLUENCE_UNKNOWN).
- **Sweep low / Sweep high** ~ `SWEEP_*` states; **CHoCH up/down** ~ CHoCH; **BPR formed / Engulfing / Asia
  Trap** ~ pattern/structure events.
These are noted for future reference only. Any real integration would require: (a) explicit authorisation,
(b) resolving repaint/timing (bar-close option exists but marker repaint is UNKNOWN), and (c) a defined,
structured webhook payload (current default = plain condition-name text).

## Integration readiness verdict
**NOT integration-ready.** Webhook-capable at the TradingView layer, but blocked by: unknown alert() runtime
payload/timing, unknown marker repaint behaviour, plain-text default payloads, and the standing rule that
nothing connects to QST/execution without explicit authorisation. Recommended precondition: a live/forward
capture (FP-LIVE-OBSERVATION-001) to establish repaint + alert timing before any wiring is even considered.
