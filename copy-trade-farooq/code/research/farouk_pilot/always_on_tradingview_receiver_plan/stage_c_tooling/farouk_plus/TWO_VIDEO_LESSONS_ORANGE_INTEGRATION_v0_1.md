# Two-Video Lessons → Orange Design Integration v0.1 (Step 8F)

**Mode: VIDEO LESSON INTEGRATION ONLY — SINGLE-SESSION.** Observation-only. Date 2026-07-11.
This note makes the FP-LIVE-VIDEO-EXPLAINER-001/002 lessons **durable design content** (they bind the
Lane-6 backlog, R6 model, and Cycle-002 capture spec conceptually; no existing Step-8/8C/8D artefact is
edited — they remain immutable, this note extends them). No execution surface; no trade-ready labels;
gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged. Machine-readable:
`two_video_lessons_orange_integration_v0_1.json`.

## 1. What is now part of Orange (from the videos, evidence-anchored)

1. **Farouk's method is substantially mechanical** — Asia H/L + London/US lows liquidity frame; lost Asia
   low with decisive candle close flips bias; entry at unmitigated OB/FVG/BPR retest with M5/M15 CHoCH
   confirmation; 4H bias veto. The construction is largely reproducible from his own indicator outputs.
2. **His indicator panel exposes exact machine-readable prices** (CHoCH / OB-retest / Fresh-OB /
   Asia-break) — Lane-6 pre-marking = reading that lane, not reverse-engineering charts.
3. **Stop width is adaptive by level type** ("bigger stop loss because this is a mitigated level"; "next
   time I'm gonna put my stop loss a little bit higher") — invalidation is a learnable function, not a
   constant.
4. **Layered-entry mechanics confirmed**: 4–5 equal tranches across the zone, one stop, tranche exits, BE
   after profit (matches the 8D schema; volumes never recorded as sizing).
5. **The his-vs-follower gap has three named mechanisms**: earlier/better fills (fill-lag), wider
   discretionary stops (stop-width), Vantage-vs-Pepperstone feed (~$0.5–2).
6. **R2b is his own doctrine** ("after the range you don't enter again") — rule provenance upgraded from
   "empirically discovered" to "stated by the source and empirically confirmed" (both verified SL losses
   came from breaking it).
7. **Two live PRE_MARK seeds**: sell region **~4150–4184** ("80–84 BE" plan) and **weekly supply
   4430–4480** — registered before any corresponding post exists (leak-free by construction).

## 2. Feature classifications (added to the Farouk-plus backlog)

| feature | class | note |
|---|---|---|
| `stop_width_by_level_type` | **PROMISING_SCORING_FEATURE** | Lane-6 invalidation-track input; learnable from his posted-SL distribution + level-type tags; explicitly narrated by him |
| `fill_lag_cost` | **PROMISING_SCORING_FEATURE** | R6 refinement: the measured cost of post-time entry vs indicator-level first-touch — the primary follower cost driver |
| `indicator_price_level_extraction` | **PROMISING_SCORING_FEATURE** | parse exact CHoCH/OB/FVG/BPR/Asia-break prices from TV-alert lane + screenshots; feeds Lane 6 and setup enrichment |
| `vantage_vs_pepperstone_feed_difference` | **WATCHLIST_FEATURE** | bounded ~$0.5–2 (S2/J17 evidence); annotate outcome-matching tolerance, never a score |
| `layered_zone_tranche_map` | **WATCHLIST_FEATURE** | leg-event enrichment per the 8D schema; 8D-A showed leg choice is NOT a materiality lever, so watch not score |
| `mitigated_level_wider_invalidation` | **NEEDS_FORWARD_EVIDENCE** | the specific level-type→width mapping needs forward samples with level-type tags before it can score |

(No feature REJECTED in this batch. `own_doctrine_compliance_no_reentry` from the lessons report is
absorbed into R2/R2b scoring rationale rather than listed as a separate feature.)

## 3. Lane-6 backlog update (conceptual, binding on the next Lane-6 iteration)

- Pre-mark levels **may come from indicator-visible CHoCH/OB/FVG/BPR/Asia-break prices** (alert-lane
  captures and evidence screenshots) — the preferred source over hand construction.
- **Every PRE_MARK_CANDIDATE must now include `invalidation_width` AND `stop_width_by_level_type`**
  (level-type-tagged width hypothesis) — grading of level-correct vs invalidation-survived stays
  independent (8C addendum).
- Anti-leakage contract unchanged and re-affirmed: evidence_ts < pre_mark_time ≤ post_time; frozen-window
  hash; post-dated citations auto-invalidate.

## 4. R6 model update (conceptual)

- **`fill_lag_cost` is measured on every XAU-F record**: (follower post-time fill − indicator-level
  first-touch price), signed by direction, alongside the existing lanes.
- Lane separation is re-affirmed and extended: **Farouk private fill · posted-zone fill · post-time fill ·
  Orange-ready fill (lane 6, when a valid pre-mark existed) · management-instruction outcome · headline
  claim** — never merged.

## 5. Cycle-002 capture additions (conceptual; extends the 8C addendum + 8D leg events)

Per XAU-F record, additionally capture: **exact indicator levels when visible** (screenshots/videos/posts —
CHoCH/OB/FVG/BPR/Asia-break prices verbatim); **feed/source notes** where available (his platform vs our
reference); **level-type tag**: FRESH | MITIGATED | RETEST | OB | FVG | BPR | ASIA_BREAK | HTF_SUPPLY_DEMAND
(multi-tag allowed) — the input `stop_width_by_level_type` and `mitigated_level_wider_invalidation` need.

## 6. Safety confirmation

Documentation integration only; targets pre-flight-checked (did not exist); no Step-8/8C/8D/8D-A or video
artefact modified; no execution built (broker/QST/cTrader/nano/copy/demo/live absent); no lot/account/
ticket/order fields anywhere; no permits/leases/orders; gates unchanged; listener PID 87988 running; no
TradingView/Worker/R2/secret action; no trade-ready labels. `NOT_INTEGRATION_READY` unchanged.

## Next step

Run **Cycle 002** on the next gold-trades activity with: the 8C management-timing block, the 8D leg-event
stream, the two PRE_MARK seeds active, and the new capture additions above (indicator levels, feed notes,
level-type tags, fill_lag_cost measurement).
