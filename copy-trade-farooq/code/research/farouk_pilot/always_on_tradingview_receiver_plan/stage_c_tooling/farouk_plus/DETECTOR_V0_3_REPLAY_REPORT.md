# Detector v0.3 — Offline Implementation + Replay Report (IN-SAMPLE ONLY)

**Mode: OFFLINE REPLAY ONLY — SINGLE-SESSION.** Observation-only. Date 2026-07-11.
v0.2 artefacts preserved untouched (new files only). All 34 records passed the ai_review fail-closed
validator + extended guard; 3/3 negative checks passed (`lot_size` key, `copy_trade_flag` key,
`TRADE_READY` label all rejected) — plus one live in-development rejection: the F4 key initially named
`…_order_note` was refused ("order" is a forbidden substring) and renamed. Labels capped at the allowed
five. Gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged. Data:
`detector_v0_3_replay_results.json`.

## 1. What v0.3 adds (per the ratified merge plan)

Base v0.2 scoring unchanged (R2/R2b attempts · R4b ≥15:30Z · caution_language · reason_stated ·
HUMAN_REVIEW overrides) plus: **F2 zone_touch_count** (LOW ±1; *24h-pre-signal touch-episode PROXY* —
formation times aren't recoverable retrospectively; forward runs use true formation times) ·
**bos_candle_close_confirmed** (+1 LOW, ratification #1 — confidence, never a gate; evidence-cited on
S3/S4 only) · **F1 contingency_pre_declared** (ZERO_WEIGHT_FLAG — fired on **0/34**: the corpus's only
pre-declared contingency, msg 45097, was never activated; flag verified present) · **F3 STRONG/WEAK tags**
(flag-only; 6 setups tagged STRONG with citable message ids, rest UNTAGGED) · **F4 confluence ranking**
(tiebreaker note only — no label power by design) · **F5 repaint guard** (Lane-6 validity rule; 0
indicator-sourced pre-marks exist yet → trivially clean, bites from Cycle 002) · **F6 stop_outside_zone**
(research stat only, §4).

## 2. Label × outcome (34 setups; outcomes deterministic, J24 = W per rematch)

| label | n | W | L | P | v0.2 comparison |
|---|---|---|---|---|---|
| SHADOW_CANDIDATE_MEDIUM | **14** | 11 | **0** | 3 | was 22 → 16W/**2L**/4P |
| SHADOW_CANDIDATE_LOW | 8 | 5 | 2 | 1 | was 1 → 1W |
| WATCH | 6 | 4 | 2 | 0 | was 6 → 3W/2L/1P |
| REJECT | 3 | **0** | 1 | 2 | was 2 → 0W/1L/1P |
| HUMAN_REVIEW_REQUIRED | 3 | 1 (J24) | 1 (J10) | 1 (J11) | unchanged |

## 3. v0.2 → v0.3: what changed and why it matters

**10 label changes, all −1 demotions via F2's spent-zone signal.** The two that matter most:
**J23 and S2 — the ONLY two losses that escaped into v0.2's MEDIUM tier — were both demoted to LOW.**
Both sat at zones with ≥3 pre-signal touch episodes (spent levels); F2 caught exactly the loss pattern
that no text feature could. Result: **the MEDIUM tier is now 100% non-loss (14/14; 79% verified-win)**
vs v0.2's 91%.

Costs, stated plainly: 6 winners stepped down MEDIUM→LOW (J01 P, J04, J05, J18, J21, J27), J14 (W)
LOW→WATCH, J15 (P) WATCH→REJECT. **No winner fell to REJECT** (REJECT holds J17 L + J15/J16 scratches).
At the combined promoted tier (LOW+MEDIUM) the loss count is unchanged (2) — v0.3's gain is
**stratification**: losses pushed to the bottom promoted rung, top tier clean. Candle-close behaved
exactly as ratified: it offset the spent-zone penalty on the two best-evidenced setups (S3, S4), keeping
them MEDIUM — a confidence input, never a gate.

**Feature importance this replay: F2 ≫ candle-close > (F1/F3/F4 = flags by design).**

## 4. F6 invalidation research stat (not scored)

Posted-SL width beyond the zone far edge, 32 setups: **median $20** (range $10–85). STRONG-tagged setups
run wider ($20/25/25/37/42/85) than untagged ($10–36, median $19) — first quantitative support for
`stop_width_by_level_type`. Feeds recovery item 4.

## 5. Do-not-overclaim block

**In-sample only**, and doubly so: F2's proxy (24h window, 0/≤2/≥3 thresholds) was chosen ON this sample
and marks 22/32 zones "spent" — the thresholds are untuned and may not generalise; the 6 winner demotions
are the visible cost. The v0.3-vs-v0.2 comparison shares every caveat of the Step-4 replay (circularity,
n=6 losses, 5m fallback on 23 setups). Forward validation on ≥15 XAU-F records decides which detector
version's stratification is real.

## 6. Safety confirmation

Offline only; v0.2 results untouched; no execution built (broker/QST/cTrader/nano/copy/demo/live absent);
no lot/risk/account/ticket fields (two live validator rejections during development prove the guard);
no permits/leases/orders; gates unchanged; listener PID 87988 running; no TradingView/Worker/R2/secret
action; nothing trade-ready; no automatic promotion (F1's 0→+1 upgrade still requires a future
ratification). `NOT_INTEGRATION_READY` unchanged.

## Next step

Lane-6 v0.2 update filed alongside (`lane6_v0_2_update_report.md`). Then recovery item 2
(FP-INDICATOR-001 alert conditions → Lane-6 builder), and Cycle 002 runs detector **v0.3** (with v0.2
computed in parallel per record for the forward A/B) on the next gold-trades activity.
