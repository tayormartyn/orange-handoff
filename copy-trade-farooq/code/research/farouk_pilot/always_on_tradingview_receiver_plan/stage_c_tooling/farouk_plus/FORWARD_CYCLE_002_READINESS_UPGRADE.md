# Forward Cycle 002 Readiness Upgrade (Step 8C)

**Mode: WORKFLOW UPGRADE ONLY — SINGLE-SESSION.** Observation-only. Date 2026-07-11.
Listener PID 87988 untouched. No cycle run (evidence store unchanged at msg 45646 — no new XAU post). No
outcome matching. No execution surface. Gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY`
unchanged.

## 0. SINGLE-SESSION WORKING NOTE (binding for all future farouk_plus steps)

- **All farouk_plus write-steps MUST be serialised to one session at a time.** The Step-8 collision (a
  parallel session's `follower_fill_expectancy_table_v0_1.json` was briefly overwritten at 13:12Z,
  repaired 13:17Z) is the standing reason.
- **Model A (`follower_fill_expectancy_table_v0_1.json` + `FOLLOWER_FILL_EXPECTANCY_REPORT_v0_1.md`) and
  Model B (`follower_fill_expectancy_table_v0_1b.json` + `..._v0_1B.md`) are BOTH preserved permanently.
  Never overwrite v0_1 with v0_1b or vice versa** — they are the optimistic/conservative bounds of the
  capturability band until forward data collapses it.
- Before any write: check the target exists; version rather than replace; append-only history everywhere.

## 1. Why this upgrade exists

Step 8 showed follower capturability is **assumption-bound**: Model B (automatic BE-scratches) +1.4p/trade
raw vs Model A (posted-TP banking) +132.3p — because June capture cannot tell us **when the management
instructions actually landed relative to price**. Cycle 002+ must capture exactly that, plus the fields
Lane 6 needs (invalidation width was the binding constraint in the retrospective).

## 2. Ledger addendum — management-instruction timing (per XAU-F record)

New required block `management_timing` (see `forward_cycle_002_schema_addendum.json`):
instruction message IDs + exact timestamps for **TP1 / SL-to-entry / close-worst / hold-best / take-off
percentages / final close**, the **scratch trigger time** when price returns to entry after an SL-to-entry
instruction, whether each scratch was **LITERAL (instruction posted before the BE-return) or
MODEL_ASSUMED**, and whether each TP-banking claim was posted **BEFORE or AFTER** the level actually
traded (deterministic, from the OHLC once imported). With these, lane-4 runs on REAL scratch points and
the Model-A/B band collapses per trade.

## 3. Lane 6 PRE_MARK_CANDIDATE schema (formalised)

Fields: `pre_mark_id · evidence_window_start_utc · evidence_window_end_utc · frozen_window_hash ·
pre_mark_time_utc · pre_mark_source · pre_mark_direction · pre_mark_zone ·
invalidation_level_or_structure · invalidation_width · farouk_post_match_status ·
leakage_check_status · expiry_time_utc`.

**Invalidation/stop-width research is logged as its own track**, separate from entry-level research:
every pre-mark carries BOTH an entry-zone hypothesis AND an invalidation hypothesis (structure-derived,
e.g. "above the swept Asia high", with its width in $). The retrospective showed the level can be right
while a $10 invalidation dies where his $40+ posted stops survive — so lane-6 scoring will grade the two
hypotheses independently (`level_correct?` vs `invalidation_survived?`). A pre-post-derivable prior:
his posted SL widths from the 34-setup ledger (learnable without leakage; distribution roughly $20–$100,
median ~$30–$40) may parameterise invalidation-width candidates.

## 4. Cycle 002 requirements (restated with upgrades)

1. New XAU/Gold entry post → **XAU-F001** (detector v0.2 scoring, HR queue, same-day 1m OHLC request,
   48h deterministic match) — **plus the management_timing block filled as messages arrive**.
2. Alert/context BEFORE a post → **PRE_MARK_CANDIDATE** (frozen-window hash, leakage check, entry +
   invalidation hypotheses; compare on his post; match on OHLC).
3. Outcome matching computes **BOTH Model A and Model B follower expectancy per record** until ≥15
   forward trades let the real instruction timing pick the model (or the blend).
4. Cycle runs only when a new setup actually exists; empty days log NO_NEW_XAU_SETUP cycle markers as
   Cycle 001 did.

## 5. Safety confirmation

Documentation-only step; pre-flight verified targets did not exist; both model artefacts intact
(37,218 B / 32,461 B); no cycle run; no outcome matching; no broker/QST/cTrader/nano/copy/demo/live
execution; no permits/leases/orders; gates unchanged; listener PID 87988 running; no
TradingView/Worker/R2/secret action; nothing trade-ready. `NOT_INTEGRATION_READY` unchanged.

## Next step

Wait for gold-trades activity (expected Sunday evening / Monday London). Cycle 002 executes with this
upgraded capture spec; single-session rule applies to every future farouk_plus step.
