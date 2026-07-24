# PROPOSED ADJUDICATION — XAU-F006-20260720 CLOSED ON THE EVIDENTIAL RECORD
**STATUS: PROPOSED, NOT EXECUTED. Awaiting Martyn's explicit approval.** Drafted 2026-07-20 per operator instruction (D-031). Append-only throughout; no original record altered.

## Analysis confirmed (operator's two consequences)
1. **The deploy gate is unsatisfiable as stated — CONFIRMED, and worse.** F006's runner factually scratched at 16:41Z (bar low 4001.30 through the BE region; corroborated by Farouk's video statement). Lane A holds the stop at 3992 (never traded; price recovered to 4018). Natural close paths: (a) Farouk posts a terminal — he will not, for a position he already left; (b) price later trades to 3992 — **this is the ACTIVE CORRUPTION RISK: Lane A would then record a FALSE −13-point stop-out at the wrong price and time on a position that factually closed at ≈4005 on 16:41Z.** The false-open state is not merely a jam; left alone it can mint a false outcome.
2. **Jam risk on the next campaign — CONFIRMED by direct precedent.** F003's apparently-open state caused F004's management to fail closed on multi-campaign ambiguity (P02 pause, orphaned instructions, unmanaged Lane A). The identical mechanism triggers the moment F007 arrives while F006 sits open.

## Proposed records (append-only, to be written ONLY on approval)
**A. Forward ledger — `XAU_F_TERMINAL_ADJUDICATION` (F005 late-recovery / F003 adjudication precedent):**
- setup_id XAU-F006-20260720; terminal type BE_STOP_SCRATCH_ADJUDICATED; effective time **2026-07-20T16:41:00Z**, price basis 4005 (Lane A mid-leg entry = the level the dropped `sl entry` instruction would have set).
- Basis (both cited): (i) independent bar evidence — 16:41Z single-bar low 4001.30 through the BE region, 3992 never traded, far leg never filled (tracker ingestion log, PEPPERSTONE feed); (ii) SOURCE_REPORTED corroboration — video sha de34a426ab0ce768…, transcript [07:15]/[09:21] "stop plus entry got hit".
- **Flag: `OUTCOME_AFFECTED_BY_DEFECT: PARTIAL_INSTRUCTION_SILENT_LOSS`** (msg 45937's `sl entry` clause dropped; D-028).
- Statistical treatment: **EXCLUDED** from Lane A expectancy, fill-rate and management-fidelity statistics (defect-affected). The adjudication exists to terminate a false open state, NOT to improve any number — F006 was already excluded.
- Provenance chain: D-028 (defect discovery) → D-030 (independent detection) → this record.
**B. Follower ledger:** matching close record (runner leg scratched at entry basis 4005, 16:41Z), same flag.
**C. Card:** lifecycle CLOSED_ADJUDICATED; original card revisions preserved (append-only card write per existing pattern).
**D. Watcher:** RESOLVED marker for F006 (firewall closes via the adjudication token, F005 precedent), enabling terminal/cost/coverage records.

## Execution plan (on approval; ~10 minutes, read-write limited to the ledgers named above)
Dry-run first (print records, write nothing) → apply → idempotency re-run (second apply = zero writes, F005 precedent) → verify: F006 excluded-open count 0, next-campaign correlation unambiguous, ledger line-count deltas exactly as proposed, all pre-existing lines byte-identical (f006_scoped_verification captures before/after).

## Explicitly recorded
This is **not** a manual correction to improve results. It is lifecycle hygiene: preventing a false open state from jamming F007+ and from minting a false stop-out if price ever reaches 3992. The deploy gate then reads: adjudication → v2 extension (compound completeness + hold-leg + per-clause fail-closed) → full re-proof → deploy → D-018 amended.

---
## STATUS UPDATE (append-only): EXECUTED 2026-07-20 under D-032
Approved with Conditions 1+2, both satisfied (governance rule + per-leg terminal states in the record). Dry-run → apply (fwd +2, follower +1) → idempotency re-run zero writes → scoped verification PASS → wire model: F006 closed. See D-032.
