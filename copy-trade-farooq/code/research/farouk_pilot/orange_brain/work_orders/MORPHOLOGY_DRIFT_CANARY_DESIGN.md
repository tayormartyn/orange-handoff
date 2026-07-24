# MORPHOLOGY-DRIFT CANARY — DESIGN (D-020; DESIGN ONLY, build awaits approval)
Purpose: catch the NEXT format change without knowing it in advance. The June-2026 change would have surfaced the week it happened had this run.

## Signal 1 — ORPHAN-MANAGEMENT ALARM (fast tripwire)
**Rule:** ≥2 management-typed gold-header messages within a rolling **24-hour window** that correlate to NO open campaign AND follow NO detected ENTRY in the same window → LOUD alarm ("possible entry-morphology drift").
**Window justification (from our own data):** in every observed campaign (F001–F006), the first management instruction followed its entry by minutes-to-hours, never crossing a day boundary by more than the overnight gap; Farouk manages same-session. 24h spans one full trading day incl. the Asia-reopen overnight case while staying short enough to catch drift within the week (117 historical orphan days ⇒ the June change would have tripped this on day one). Threshold ≥2 suppresses the single-stray case (e.g. a late orphan on an adjudicated campaign).
**Data source:** wire's own outputs — XAU_F_ORPHAN_MANAGEMENT records + intake ORPHAN_MANAGEMENT_MESSAGE class + open-campaign state from cards. Read-only; NO new live process — evaluated inside brain_refresh/ORANGE_STATUS on each run (and Martyn's daily status habit makes it effectively daily).

## Signal 2 — ENTRY-RATE vs MANAGEMENT-RATE RATIO (slow drift detector)
**Rule:** weekly detected-entry count vs trailing-4-week management-instruction rate; alarm when the entries/mgmt ratio falls below **50% of its trailing-8-week median** for 2 consecutive weeks (sustained, not a quiet-week artifact; a genuine no-trade fortnight drops BOTH counts and leaves the ratio intact).
**Data source:** intake classification ledger (append-only counts) — pure read.

## Signal 3 (bonus, cheap) — QUARANTINE-MIX SHIFT
Alarm when the weekly QUARANTINED_UNPARSED_SIGNAL_CANDIDATE share of gold-header messages doubles vs trailing median — new phrasings land in quarantine first.

## Non-goals / safety
No auto-fix, no parser mutation, no message reinterpretation — alarms route to the operator brief + ORANGE_STATUS as WARN lines with the offending message ids. False-positive posture: prefer noisy over silent (this class of failure has cost three incidents + 224 missed historical entries).

## Build estimate
~150 lines inside brain_refresh (shares its ledger readers) + fixtures replaying the June-2026 transition as the acceptance test: the canary MUST fire on the historical data at the week of the format change.
