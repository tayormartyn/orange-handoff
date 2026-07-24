# ORANGE MASTER SOURCE OF TRUTH vNEXT — ADDENDUM: Batches 004 + 004B
**As of 2026-07-12 ~12:45Z. Read together with `ORANGE_MASTER_SOURCE_OF_TRUTH_vNEXT.md` (2026-07-12).
Extend-not-edit: the vNEXT pair is preserved; this addendum records the Batch-004/004B deltas and the
day's offline work since the vNEXT issue. Next full master re-issue: after Cycle 006 / XAU-F001.**

## What changed since the vNEXT issue (same day)
1. **Cycles 004 + 005 ran clean** (NO_NEW_XAU_SETUP; cursor advanced 45646→45648 in Cycle 004 —
   45647 NON_XAU, 45648 IRRELEVANT; store still 45648). XAU-F001 still pending; PM-F001 (exp Jul-17)
   and PM-F002 (exp Jul-31) still PRE_MARK_OBSERVED / match PENDING / untouched.
2. **Detector v0.4 offline replay done — NOT promoted** (v0.3 unchanged). V4-LIT rejected
   (catastrophic over-filter); V4-SP/SPX mixed (0 promoted losses but 10–11 winners demoted; gate-type
   objection; in-sample threshold selection); V4-TF neutral; displacement untestable in-sample.
   Promotion conditions codified in `DETECTOR_V0_4_PROMOTION_GATE.md`; nothing pending.
3. **Training Batch 004 (targeted gap fill) complete:** FP-EDU-001 (Live Jul-5, 2h08) finally
   Fable-reviewed; **FP-B004-Z2** (Dec-21 Zoom, 2h45) transcribed + mined; **FP-B004-Z1** (Oct-12
   Zoom) transcribed then **REJECTED — guest EMA scalping, off-method family, quarantined from the
   XAU engine**; **FP-B004-LOG1** (SeaScalper_TradeLog_1.pdf) processed. Missing-file list confirmed
   precisely (15-min stream companion; distinct Friday indicator Q&A; EDU-035's fuller displacement
   session; FP-CAMPAIGN-004 video).
4. **Batch 004B capture-only merge done** (`TRAINING_BATCH_004B_CAPTURE_ONLY_INTEGRATION.*`):
   ten new capture fields — `london_high_low_panel_evidence`, `us_high_low_panel_evidence`,
   `orb_timing_context`, `magnet_logic_evidence` (L6), `stop_feasibility_context` (L6),
   `mitigation_depth_pct_if_stated`, `anticipatory_be_threshold_pips`, `anticipatory_be_evidence`,
   `limit_at_zone_evidence`, `claim_convention_evidence` — plus enum additions
   (`indicator_level_source_kind` += LONDON_/US_ H/L, FLAT_CANDLE, GAP) and 8C value
   `scratch_mode=DOCTRINE_ANTICIPATED`. **All capture-only; nothing scored.**

## Key new doctrine on file (Batch 004)
- **Anticipatory follower BE:** standing instruction to move SL→entry at **+50–60p before** his
  message ("before I say put stop loss to entry, you guys need to do it already") — Model B's +50 BE
  arm is official follower doctrine; 8C now distinguishes LITERAL vs DOCTRINE_ANTICIPATED scratches.
- **Stop-width causal driver:** width sized to surrounding **unmitigated levels / sweep risk**, not
  only level type (Z2 verbatim ×2) → `stop_width_by_level_type` v0.2 research input; plus a
  **stop-feasibility veto** ("this level is too big" → no trade).
- **Panel surface (Jul-5 update):** London H/L + US H/L levels, extended boxes, Asia-trap alerts;
  ORB = first 15 minutes (London 09:00 GMT+1, NY 15:30); unretested orb breakouts / unmitigated
  weekly levels / unfilled gaps = **magnets**; flat candles = mitigation-required level class.
- **First mitigation-depth numeric:** "at least 50% of the zone" (LOW-confidence digits).
- **Documentary limit-at-zone evidence:** official log prints "Limit Long/Limit Buy" (FP-B004-LOG1);
  claim-convention instance #3 (92% = 12W/1L, BE+Removed excluded); **bot-lane announced → watchlist**.

## Unchanged (re-affirmed this addendum)
Safety state (gates `PAPER/PREVIEW/False/False`; execution absent/hard-disabled; no
permits/leases/orders; `NOT_INTEGRATION_READY` unchanged) · listener **PID 23012** (only live capture
process; never restart from a work session) · detector **v0.3 live + v0.2 parallel A/B** · v0.4
offline behind its promotion gate · ratification queue (mitigated_level_exclusion) · demo-readiness
blockers · single-session write rule.

## Next exact actions (supersedes the vNEXT list item 1 timing only)
1. **Cycle 006 / XAU-F001 at the first real XAU post after tonight's ~22:00Z reopen** — full
   8C+8D+8F+001B+002B+003B+**004B** capture spec; v0.2/v0.3 parallel; PM-F001/PM-F002 comparison;
   same-day 1m OHLC request; 48h deterministic match.
2. Offline queue: optional Feb–Mar 2026 + May OHLC matching; v0.4 forward re-replay after ≥15
   XAU-F records; full master re-issue with Cycle-006 results.
