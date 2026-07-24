# PARSER COVERAGE REPLAY — TASK SPEC (operator-issued 2026-07-20; step 3 of the authoritative order, D-015)
Status: QUEUED (runs after TASK 1B corpus ingest, BEFORE alert-lane monitor + demo lane). Read-only toward all live state. **Prerequisite for the demo copy-trade lane — any gap found is fixed and re-proven before that lane is built.**

## Requirements (as issued)
1. Replay the FULL historical Telegram archive through the CURRENT parser (interpreter sha f27a9034 at spec time — record actual sha at run time) and correlation logic.
2. Every message resolves to exactly one of: PARSED / QUARANTINED / EXPLICITLY_REJECTED — **zero silent drops**, proven by count reconciliation (archive rows == disposition rows).
3. Report by morphology class.
4. Regression-test the known failure morphologies and variants:
   - `XAUUSD Sell Zone: X–Y / Stop Loss: Z` (labelled-field form)
   - `full exit` (EXPLICIT_FULL_EXIT family)
   - `close 90% leave 10%` (EPPC close-X-leave-Y)
   - `close N%` (CLOSE_PERCENTAGE_v0_1)
   - `tp 1 now`
   - `put sl to entry`
   - claimed-pips commentary (`700 pips`, `350 pips`, `140-150 pips` — must NEVER be terminal)
   - lot-fraction result cards
5. Crypto handling: BTC/crypto messages identified, instrument-scope tagged per K-047, routed away from XAUUSD; neither silently dropped nor leaking into gold state.
6. List EVERY distinct morphology that fails or quarantines.
7. Output tagged **RETROSPECTIVE_NOT_PROSPECTIVE**. No campaign creation, no freezes, no backdating, no live-ledger writes — replay runs against isolated copies/fixtures only.
8. STOP AND REPORT with full test counts (incl. skipped/deselected/xfail).

## Why it sits at step 3 (operator rationale, D-015)
Two morphology failures have already cost campaigns (F003 watcher-era full-exit gap; F005 close-100% gap). The demo copy trader may not be built on a parser whose historical coverage is unproven. Perishability logic: parser replay + alert-lane monitor are prerequisites; demo-lane fill/spread/latency evidence is unrecoverable once signals pass; H-FPL-02 / Stage 2 / back-data screening operate on captured material and lose nothing by waiting.
