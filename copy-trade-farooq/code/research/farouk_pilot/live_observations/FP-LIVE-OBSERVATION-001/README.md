# FP-LIVE-OBSERVATION-001 — Live Alert Observation (P1)

**Status: PROTOCOL PREPARED — NOT YET RUN. No alert created. Integration = NOT_INTEGRATION_READY.**

Purpose: forward, observation-only validation of the **Farouk's Playbook — Smart Money Suite** (FP-INDICATOR-005)
TradingView alert surface, to resolve the P1 unknowns (runtime payloads, bar-close vs intrabar timing, repaint/
mutation, duplicates, A+/A+++ grade behaviour). Derived from `synthesis_v0.3/LIVE_VALIDATION_PLAN_v0.1.md` (P1)
and `synthesis_v0.3/FAROUK_STATE_MACHINE_CANDIDATE_v0.2.md` (untrusted ALERT_INTAKE).

## Context
XAUUSD · Pepperstone · 3m · app/toast only · **no webhook** · **no broker action**.
P1 conditions: A+++ setup · A+ or better · Any alert() function call · Sweep low · Sweep high · CHoCH up · CHoCH down.
Named conditions → **Once per bar close**; **Any alert()** → script-controlled timing/payload preserved.

## Files
1. `LIVE_TEST_PROTOCOL.md` — step-by-step (chart/feed, TZ, config snapshot, safe alert creation, pre-close →
   close → +1 → +5 observations, message capture, panel/marker capture, duplicates, grade changes, repaint, cleanup).
2. `ALERT_CREATION_CHECKLIST.md` — how to create the alerts LATER (app/toast only, no webhook).
3. `EVENT_OBSERVATION_TEMPLATE.json` — per-event record schema + field guidance (24 fields).
4. `EVENT_OBSERVATION_TEMPLATE.csv` — flat log with the same fields.
5. `SCREENSHOT_NAMING_GUIDE.md`
6. `SCREEN_RECORDING_GUIDE.md`
7. `LIVE_VALIDATION_GUARDRAILS.md`
8. `PASS_FAIL_CRITERIA.md`
9. `CLEANUP_CHECKLIST.md`
10. `README.md` (this file)

## Golden rules
- A TradingView alert is an **untrusted observation**, never a trade signal.
- Record only what is directly visible; use **UNKNOWN**, never a guess.
- No code, no QST, no webhook, no broker/risk/permit/lease/execution change.
- Verdict stays **NOT_INTEGRATION_READY** unless PASS_FAIL_CRITERIA are all met with live evidence.

## Suggested working subfolders (create at run time)
`screenshots/` · `recordings/` · results copies (`RESULTS.json/.csv`, `RESULTS_SUMMARY.md`).
