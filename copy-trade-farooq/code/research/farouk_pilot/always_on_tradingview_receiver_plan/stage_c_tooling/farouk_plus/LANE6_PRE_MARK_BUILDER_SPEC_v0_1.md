# Lane-6 Pre-Mark Builder Spec v0.1 (Recovery Item 2)

**Mode: BUILDER SPEC ONLY — SINGLE-SESSION.** Observation-only. Date 2026-07-11.
The builder creates **review-only PRE_MARK_CANDIDATE records** from already-captured indicator/alert
context. It has **no execution path**: records flow only to the forward ledger and human review; the
validator + extended guard reject TRADE_READY / EXECUTE / ORDER / LOT_SIZE / BROKER_ROUTE / ACCOUNT_ID /
RISK_SIZE / COPY_TRADE / NANO / LIVE / DEMO_EXECUTE as keys or labels. It never touches TradingView
alerts (it READS the alert-lane archive the Worker already stores). Machine-readable:
`lane6_pre_mark_builder_spec_v0_1.json`. Gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY`
unchanged.

## 1. Inputs (per candidate)

`alert_id · alert_type (mapped enum from FP_INDICATOR_001_ALERT_MAPPING) · alert_timestamp_utc ·
bar_close_confirmed (bool — REQUIRED true for indicator-sourced values) · instrument · timeframe ·
direction_hint (from alert type/payload) · structure_context (CHoCH/BOS refs) · liquidity_context
(sweep/Asia-trap refs) · ob_fvg_bpr_context · indicator_price_level_if_visible (panel value from a CLOSED
bar) · level_type_tag (8F vocabulary + STRONG/WEAK, evidence-cited or UNTAGGED) · zone_touch_count (true
formation time forward) · confluence_ranking (BOS/CHoCH > FVG-inversion > Level-reclaim > SFP; tiebreaker)
· stop_outside_zone_candidate (structure-relative invalidation hypothesis + level-type width, frozen
formula) · repaint_guard_status (CLEAN | LEAK_DETECTED_INVALIDATED)`

## 2. Creation logic

**Minimum evidence to create a candidate** (all four): (a) ≥1 HIGH-usefulness alert event
(Sweep/CHoCH/BPR/Asia-Trap) bar-close-confirmed; (b) a numeric level — panel value from a closed bar, or a
zone constructible from the alerted structure; (c) a direction hint consistent across the cited events;
(d) an invalidation hypothesis (stop_outside_zone_candidate with frozen width formula). Anything less →
**PRE_MARK_INSUFFICIENT_CONTEXT** (recorded, not scored).

**Confidence scoring (review-only):** base OBSERVED; +1 per additional independent HIGH-class confluence
(ordering per ranking, tiebreak only); +1 if level_type_tag = STRONG (evidence-cited); −1 if
zone_touch_count ≥3 (spent); A-grades recorded at weight 0. Confidence caps at the label
`PRE_MARK_OBSERVED` — pre-marks have **no shadow-candidate tier of their own** and never feed detector
labels directly.

**Expiry:** end of the session in which the pre-mark was created (or an explicit stated horizon for
day-ahead levels, e.g. the video-seed weekly supply) → `PRE_MARK_EXPIRED` if untouched and unposted.

**Comparison on Farouk's post:** when a gold-trades entry post arrives, compare zones (overlap OR
mid-distance ≤ $3) → `PRE_MARK_MATCHED_FAROUK` / `PRE_MARK_DID_NOT_MATCH`; record
`time_before_post_seconds` and the fill-lag implication (would the pre-mark level have filled earlier?).

**Outcome matching:** when OHLC arrives (48h SLA), the deterministic matcher computes hypothetical
touch/MFE/MAE/invalidation-survival for the pre-mark EXACTLY as for XAU-F setups; `level_correct` and
`invalidation_survived` graded independently (8C addendum).

## 3. Anti-leakage (hard, inherited + extended)

evidence_ts < pre_mark_time ≤ post_time · frozen-window hash · post-dated citations auto-invalidate ·
**F5: indicator values must be bar-close-confirmed; intra-bar/repaintable values invalidate the record** ·
uncertain alerts → INSUFFICIENT_CONTEXT. Labels restricted to: PRE_MARK_OBSERVED · PRE_MARK_MATCHED_FAROUK
· PRE_MARK_DID_NOT_MATCH · PRE_MARK_INSUFFICIENT_CONTEXT · PRE_MARK_EXPIRED.

## 4. Cycle-002 integration

1. Alert context before a gold post → builder creates PRE_MARK_CANDIDATE (validator-passed) → forward
   ledger + HR queue visibility.
2. Farouk posts → XAU-F001 created (8C timing + 8D legs + 8F captures) → pre-mark comparison computed.
3. **Detector v0.3 AND v0.2 labels computed in parallel per record** (forward A/B preserved).
4. `fill_lag_cost` measured (post-time fill vs indicator-level first-touch) and indicator levels recorded
   verbatim where visible.
5. OHLC within 48h → deterministic outcomes for both the setup and any pre-marks.

## 5. Safety confirmation

Spec only — no live code, no alert changes, no execution wiring; the two video-derived seeds
(~4150–4184; 4430–4480) become the builder's first candidates when Cycle 002 opens. Listener PID 87988
untouched; no permits/leases/orders; gates unchanged; no Worker/R2/secret action.
`NOT_INTEGRATION_READY` unchanged.

## Next step

Cycle 002 on the next gold-trades activity runs the full stack: builder pre-marks (if alert context
arrives first) + XAU-F001 + v0.2/v0.3 A/B + fill-lag + deterministic matching.
