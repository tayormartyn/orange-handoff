# LIVE VALIDATION GUARDRAILS

Binding constraints for FP-LIVE-OBSERVATION-001. These override convenience.

## Absolute prohibitions
- **No webhook** is ever configured (URL field stays empty).
- **No detector code**; nothing is wired to **QST**.
- **No broker / risk / permit / lease / execution** change. The **1.0% campaign cap** and all **execution
  gates (False)** are untouched.
- **No order** is placed, amended, cancelled or managed.
- **No TradingView alert is created during protocol preparation** (only later, per the checklist, app/toast only).

## Evidence-integrity rules
- A TradingView alert is an **UNTRUSTED observation**, never an authorised trade signal (per
  FAROUK_STATE_MACHINE_CANDIDATE_v0.2 ALERT_INTAKE).
- Record only what is **directly visible**; use **UNKNOWN** — never infer a value.
- Do not modify default alert messages (we are capturing the **native** payload).
- Do not rename/move/delete source screenshots or recordings after logging.
- Chart-TZ + UTC recorded for every time field.

## Standing verdict
Integration remains **NOT_INTEGRATION_READY** unless PASS_FAIL_CRITERIA are ALL met with live evidence. A single
REPAINTED or unparseable-payload result on a condition keeps that condition blocked.

## Scope
This session validates **P1** only (payloads, timing, repaint, duplicates, grade behaviour). P2/P3 items
(numeric mitigation, FVG/IFVG, expiry, expectancy) are out of scope here.
