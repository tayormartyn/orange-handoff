# Lane 6 v0.2 Update Report (with detector v0.3)

**Mode: OFFLINE UPDATE — SINGLE-SESSION.** Observation-only. Date 2026-07-11. Extends Lane-6 v0.1
(unchanged on disk) per the ratified Orange v0.3 merge plan. Machine-readable: `lane6_v0_2_update.json`.
Gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged.

## What changed

1. **Four new confidence inputs** (all LOW / tiebreaker; never gates): `zone_touch_count`
   (first-mitigation-tradable / spent-level-penalty), STRONG/WEAK `level_quality_tag` (evidence-cited or
   UNTAGGED; WEAK levels are targets, never entry pre-marks), `confluence_ranking` (BOS > FVG-inversion >
   Level-reclaim > SFP, ratified graded stack, tiebreaker only), `bos_candle_close_confirmed` (+confidence
   per ratification #1).
2. **One new HARD validity rule:** `lane6_repaint_guard` — indicator-sourced pre-mark values must be
   bar-close-confirmed; repaintable intra-bar values invalidate the record
   (`LEAK_DETECTED_INVALIDATED`). Currently trivially clean (no indicator-sourced pre-marks exist yet);
   it bites from Cycle 002 when the alert lane becomes the preferred source.
3. **Invalidation research track armed with its first calibration stat** (from the v0.3 replay F6
   computation): posted-SL width beyond the zone far edge across 32 setups — **median $20, range
   $10–85, with STRONG-tagged levels running wider ($20–85) than untagged ($10–36)**. This is the first
   quantitative support for `stop_width_by_level_type`; the structure-relative width formula will be
   frozen per level type before each forward test window (anti-post-hoc guard).
4. Anti-leakage contract v0.1 unchanged and re-affirmed; the two video-derived pre-mark seeds
   (~4150–4184 sell region; 4430–4480 weekly supply) remain active and now inherit the new
   confidence/validity machinery.

## Safety

Research lane only; labels unchanged (PRE_MARK_* set); no execution path exists for pre-marks to reach;
forbidden outputs unchanged and validator-enforced; listener PID 87988 untouched.
`NOT_INTEGRATION_READY` unchanged.

## Next step

Recovery item 2 — FP-INDICATOR-001 alert conditions → the Lane-6 pre-mark builder (now with the repaint
guard and confidence inputs specified); Cycle 002 applies all of this on the next gold-trades activity.
