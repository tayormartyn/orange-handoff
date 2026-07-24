# MAINTENANCE WINDOW — 2026-07-21 21:00-22:00Z (BUNDLED, approved D-065)

Two changes in ONE window (avoid two restarts). Execute in this order.

## PRE (capture before-state)
- shas: `live_wire.py` (current a7dbb890...), `module_a_telegram.py` (staged f75b8e8a...), fwd ledger, freeze, guards, const.
- `f006_scoped_verification.py capture` (or equivalent state snapshot).
- confirm no campaign is actively OPEN and being managed (all three are nominal-only opens; F007 terminal).

## STEP 1 — WIRE V3 TERMINAL-MARKER DEPLOY (Fable)
1. copy `live_wire_v3_terminal_marker.py` -> `live_wire.py`; record after-sha (expect b160b556fb8792fc).
2. STEP 2 (markers) is written BEFORE the wire restart so the restarted wire loads them in one pass — OR after, either works (no-op proof guarantees identical behaviour until markers exist). Recommend: write markers first, then restart, so one restart sees the final state.

## STEP 2 — WRITE THE THREE XAU_F_TERMINAL_OUTCOME MARKERS (Fable, append-only)
- append F002/F004/F007 markers per PROPOSED_TERMINAL_OUTCOME_MARKERS_F002_F004_F007.md (per-leg states, effective_ts = terminal bar, basis price). Dry-run -> apply -> idempotency re-run (zero writes) -> scoped verify (pre-existing lines byte-identical, growth = exactly 3 records).
- CONDITION: TERMINAL_OUTCOME not adjudication; no defect/number/exclusion (D-065).

## STEP 3 — LISTENER RESTART (Martyn's call; the capture-gap action)
- restart `module_a_telegram.py` (staged f75b8e8a, LIVE_EDIT capture wired) — seconds of gap, no backfill; do it inside the quiet 21:00-22:00Z metals close.

## STEP 4 — RESTART WIRE + WATCHER + OBSERVER (Fable)
- stop the 3, prove PIDs dead, clear locks, restart detached with fresh logs (listener/tracker/companion/shadow untouched).

## POST (verify)
- banner reports the running v3 sha; `load_campaign_state` open set -> `[]` (F002/F004/F007 all closed by marker); cursor intact; global ledger byte-identity (pre-existing lines) + growth = the 3 markers only; gates re-read PAPER/PREVIEW/False/False; 7/7 services single-instance.
- amend registers: WIRE_NOMINAL_OPEN_OUTCOME_TERMINALS -> RESOLVED; LIVE_EDIT defect -> closes once a live edit is captured; demo-spec §10 items 2 + 4a -> satisfied.
- report BOTH sha sets + the open-set-now-empty confirmation.

## STEP 5 — SEQUENCED, NOT IN THIS WINDOW: ~6h proximity window
- Deploy the PROXIMITY_HOURS 18 -> ~6 change AFTER the marker is live and confirmed (the marker changes the population the window operates on — sequence them, do NOT bundle). Separate small change, its own before/after + no-op proof.
