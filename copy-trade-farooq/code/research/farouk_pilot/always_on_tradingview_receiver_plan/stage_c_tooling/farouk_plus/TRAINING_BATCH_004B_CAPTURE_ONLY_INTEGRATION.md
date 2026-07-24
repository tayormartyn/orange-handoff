# Training Batch 004B — Capture-Only Integration (Batch-004 lessons → Cycle-006 capture spec)

**Mode: BATCH 004B — CAPTURE-ONLY MERGE, NO LIVE SCORER CHANGE. SINGLE-SESSION.** Observation-only.
Date 2026-07-12 (~12:45Z). Extends (never edits) the Cycle-002 schema addendum and the 001B/002B/003B
integrations. **Detector v0.3 live labels are UNCHANGED for Cycle 006; v0.4 stays offline (promotion
gate untouched); no v0.4 replay run; no OHLC matching run.** Machine-readable:
`training_batch_004b_capture_only_integration.json`. Master addendum:
`ORANGE_MASTER_SOURCE_OF_TRUTH_vNEXT_ADDENDUM_BATCH004B.md`. Gates `PAPER/PREVIEW/False/False`;
`NOT_INTEGRATION_READY` unchanged.

## 0. Live-priority gate (checked first)
Listener **PID 23012 running/untouched** (only python process). Read-only store query at ~12:42Z:
max msg id still **45648** = cursor; market closed until ~22:00Z; alert lane cannot fire.
**No XAU trigger → Cycle 006 not invoked; Batch 004B proceeded.**

## 1. New capture-only fields (per XAU-F record and, where marked (L6), per PRE_MARK_CANDIDATE)

| field | definition | source lesson |
|---|---|---|
| `london_high_low_panel_evidence` | whether London High/Low panel levels were visible/citable in setup context (values + bar-close-confirmed flag; UNKNOWN if not visible) | B4-L9 (Jul-5 indicator update) |
| `us_high_low_panel_evidence` | same for US High/Low panel levels | B4-L9 |
| `orb_timing_context` | which session ORB applies (ASIA / LONDON_0900_GMT+1 / NY_1530, first-15-minutes definition), breakout/retest state, and whether an unretested orb breakout existed nearby | B4-L10 |
| `magnet_logic_evidence` (L6) | citable unmitigated levels / unretested orb breakouts / unfilled gaps named as draw targets ("they will come back"), with message/media refs; UNKNOWN if none cited | B4-L4, B4-L8 |
| `stop_feasibility_context` (L6) | any statement that a stop was placeable/unplaceable at a level ("this level is too big" class); values FEASIBLE / INFEASIBLE_STATED / UNKNOWN | B4-L6 |
| `mitigation_depth_pct_if_stated` | spoken/visible mitigation depth as % of zone (e.g. "at least 50% of the zone"); numeric only when stated — never inferred; UNKNOWN otherwise | B4-L3 |
| `anticipatory_be_threshold_pips` | the standing follower BE threshold in force (currently 50–60p per the Jul-5 verbatim); recorded as doctrine reference, not computed | B4-L14 |
| `anticipatory_be_evidence` | evidence bearing on whether followers were expected to BE before the instruction: doctrine restatements, "you should already have done it" class messages, with ids/ts | B4-L14 |
| `limit_at_zone_evidence` | citable limit-order evidence for THIS setup (posted "Limit Long/Buy/Sell" labels, pending-order statements); extends 003B `entry_mechanic_evidence` with the documentary class | B4-L13 (FP-B004-LOG1) |
| `claim_convention_evidence` | which claim-accounting convention the setup's result claims use, citing the instance (flats-excluded W/(W+L); BE-after-run rows; Removed rows), extends 003B `claim_convention_notes` | B4-L16 |

Supporting enum extension (capture-only, from 004 merge queue): `indicator_level_source_kind` +=
`LONDON_HIGH | LONDON_LOW | US_HIGH | US_LOW | FLAT_CANDLE | GAP`. New 8C capture value:
`scratch_mode = DOCTRINE_ANTICIPATED` (BE move preceding the instruction message).

**All fields are capture-only: never scored by v0.3, never gates, no sizing semantics. The
never-widen ratification stands; stop-feasibility/magnet fields are research inputs to the Lane-6
invalidation track and `stop_width_by_level_type` v0.2 only.**

## 2. Cycle 006 / XAU-F001 readiness (updated)

When the first real XAU setup arrives, the record must additionally answer, from evidence:
1. **Would the +50–60p anticipatory BE have applied?** (price reached entry+50–60p before any
   SL-to-entry instruction → `scratch_mode=DOCTRINE_ANTICIPATED` candidate; deterministic from OHLC
   once imported.)
2. **Did the formal SL-to-entry instruction come EARLY or LATE vs the doctrine threshold?**
   (instruction ts vs first entry+50–60p touch — the 8C Model-A/B band collapser, now with a
   doctrine-anchored reference point.)
3. **Was London/US H/L or ORB context visible/citable?** (fields above; bar-close-confirmed values
   only, repaint guard applies.)
4. **Was any level treated as a magnet/liquidity draw?** (unmitigated level / unretested orb / unfilled
   gap named as target.)
5. **Was stop feasibility mentioned?** (FEASIBLE / INFEASIBLE_STATED / UNKNOWN.)
6. **Was mitigation depth visible or stated?** (% of zone if stated; entry-depth-within-zone
   deterministic from OHLC otherwise; UNKNOWN never guessed.)

Everything else per the standing 8C+8D+8F+001B+002B+003B spec; v0.2/v0.3 parallel A/B unchanged.

## 3. Explicitly NOT merged
- **FP-B004-Z1 (Oct-12 Zoom) stays REJECTED/off-method** — guest EMA/stochastic scalping family;
  no field, note, or lesson from it enters the XAU engine; registered sha256 provenance only.
- `fvg_claim_chain` stays v0.4/v0.5 backlog (capture-first; needs forward FVG inventory; no scoring).
- `london_us_session_break_priors` + bot-lane watch stay WATCHLIST (verification + ratification
  before any consideration).
- No ratification requested; the mitigated_level_exclusion gate is unchanged.

## 4. Safety confirmation
Documentation/capture-schema only; targets pre-flight-checked (none existed); nothing overwritten;
no execution built (broker/QST/cTrader/nano/copy/demo/live absent); no permits/leases/orders; gates
unchanged; listener PID 23012 running/untouched; no TradingView/Worker/R2/secret action; no
lot/risk/account/route/ticket/order fields. `NOT_INTEGRATION_READY` unchanged.

## Next step
**Cycle 006 / XAU-F001 at the first real XAU post after tonight's ~22:00Z reopen** under the full
spec including §1–§2. Offline queue unchanged: optional Feb–Mar 2026 + May OHLC matching; v0.4
forward re-replay after ≥15 XAU-F records.
