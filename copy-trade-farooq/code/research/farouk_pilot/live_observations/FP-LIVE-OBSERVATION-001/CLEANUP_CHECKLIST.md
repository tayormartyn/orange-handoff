# CLEANUP CHECKLIST (after the live window)

- [ ] **Delete every alert** created for this test (list them from the run log; confirm each is removed).
- [ ] Open TradingView **Alerts panel** → confirm **zero** active alerts remain from this test.
- [ ] Confirm **no webhook URL** was ever saved on any alert (should have been empty throughout).
- [ ] Confirm notifications were **App/Toast only**; no external delivery configured.
- [ ] Stop and save the screen recording(s); do not edit the master. Hash into the run log.
- [ ] Move all screenshots into `screenshots/`; verify naming; (optional) hash them.
- [ ] Finalise `EVENT_OBSERVATION_TEMPLATE.json/.csv` copies as the completed log (e.g. `RESULTS.json/.csv`).
- [ ] Fill PASS/FAIL per condition in a short `RESULTS_SUMMARY.md`; carry forward the verdict.
- [ ] Re-affirm: **NOT_INTEGRATION_READY** unless every PASS_FAIL criterion was met.
- [ ] Confirm governance intact: no code, no QST, no broker/risk/permit/lease/execution change, no order.
- [ ] Note any P2/P3 items observed opportunistically (for the next session) — do NOT act on them.
