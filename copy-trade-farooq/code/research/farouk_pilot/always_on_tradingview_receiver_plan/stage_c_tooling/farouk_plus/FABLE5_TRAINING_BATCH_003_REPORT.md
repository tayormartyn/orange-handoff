# FABLE 5 TRAINING BATCH 003 — REPORT
**As of 2026-07-12 ~10:25 local (Sun). Machine-readable twins: `fable5_training_batch_003.json` +
`fable5_training_batch_003_merge_queue.json`. Mode: extraction from the six relaunched transcripts +
WhaleRoom_TradeRecap_1.pdf. Review-only; no scoring change; v0.3 live labels untouched.**

## 0. Live-priority gate (checked first)
Read-only store query at 10:14: max msg id still **45647**; the only post-cursor message remains the
**non-XAU HYPE/crypto chatter** (navigatorjosh forward, Hormuz uncertainty) — recorded NON-TRIGGERING,
left for Cycle 004. **No new XAU/Gold activity → extraction proceeded.** Listener PID 87988 verified
running in the same check.

## 1. Processed items (7) — registered as private research evidence
| Evidence ID | Source | Content | Rights/provenance |
|---|---|---|---|
| FP-B003-01 | `Schermopname_2025-12-14_om_16.45.20.mov` (410s, 58 seg) | Indicator series pt.1: session range boxes, yellow (market-maker) candles, VWAP | member-recorded WhaleRoom video; private research only |
| FP-B003-02 | `Schermopname_2025-12-14_om_17.03.11.mov` (344s, 49 seg) | pt.2: POC/VAH/VAL, SFP sweep dots, liquidity sweeps, EMAs (unused by him) | same |
| FP-B003-03 | `Schermopname_2025-12-14_om_17.12.15.mov` (478s, 76 seg) | pt.3: ORB (Asia/London/NY), orb mid = hidden liquidity, no-trade-inside-orb | same |
| FP-B003-04 | `Schermopname 2026-06-29 om 16.37.24.mov` (219s, 45 seg) | Jun-29 gold recap: pre-planned long, layering doctrine, mitigated-OB rule | same |
| FP-B003-05 | `Schermopname 2026-07-01 om 20.16.35.mov` (509s, 182 seg) | Jul-1 LOSS post-mortem: no-FVG dump = sweep; weak break; stop above Asia high | same |
| FP-B003-06 | `Schermopname 2026-07-02 om 19.40.23.mov` (381s, 72 seg) | Jul-2 recovery: multi-TF close confirmation stack, 4H-OB target, 78–80% Asia-high stat | same |
| FP-RECAP-001 | `WhaleRoom_TradeRecap_1.pdf` (7,209 B) | Feb-17→Mar-27 2026 recap: 25+ trades, 18+W/3L/5 missed, per-trade entry+SL prices | member-distributed WhaleRoom PDF; private research only |

sha256 for all six media recorded in `derived/transcripts/batch_003/FP-B003-0*/\*_source_meta.json`.
**Dedup:** no overlap with FP-EDU-001..007, FP-INDICATOR-001..006, FP-CAMPAIGN-001..004,
FP-LIVE-VIDEO-EXPLAINER-001..004, FP-AUDIT-001/002, FP-JOURNAL-001 (checked by filename/size/duration/
source-asset). **Skipped as duplicates:** the byte-identical `(1)`/`(2)` Downloads copies of two
2025-12-14 files (never transcribed). Nothing skipped as lower priority.

**Transcription-quality note (applies throughout):** faster-whisper base.en garbles his accent
consistently: "view up"=VWAP, "feathery gap"/"effigy"/"FPG"/"IFG"=FVG, "very high/very low"=VAH/VAL,
"50 minutes"=15 minutes, "PTC"=BTC, "swing fell pattern"=swing failure pattern. Spoken price digits
(e.g. "four five zero four four zero") are LOW-confidence until OHLC-matched.

## 2. Stop-width / invalidation lessons (headline #1)
**FP-RECAP-001 adds 19 usable posted stop-width samples (Feb–Mar 2026)** — a period BEFORE our existing
dataset: widths $8–$89, **median ≈ $21 — matching the existing 32-sample median of ~$20 across a
different quarter and a ~$700 price change** (cross-period stability of stop_width_by_level_type v0.1).
Structure: routine zone-trades cluster $13–$40; a **wide tail $55/$84/$89 sits on counter-trend shorts
explicitly noted "low lot"** (width and size inversely linked — recorded as claim-context only, no
sizing fields). The tightest stop in the set ($8, 19-Mar long) is one of only three losses, and its
note says **"SL hit at 4762" vs posted SL 4767 — first documented posted-vs-actual stop gap (~$5)**,
direct evidence for the central caveat (his real stops sit wider than posted). FP-B003-05 adds the
structural-anchor rule: *"put the stop above Asia High… to be safe"* → stop_outside_zone + structural
invalidation anchor. Classification: **STRENGTHENS_EXISTING_FEATURE** (stop_width_by_level_type v0.1
dataset + stop_outside_zone); merge = capture-only dataset extension.

## 3. Mitigation-depth lessons
- FP-B003-04: entry OB was reached by a **sweep slightly below the zone** before reacting ("they came to
  this OB, swept a little bit lower — you can expect a reaction") → reaction-after-overshoot is expected,
  not invalidation → supports capture of overshoot depth (8D leg events).
- FP-B003-06: he prefers **deeper entries within the zone** ("good entry 116… I was hoping a little bit
  higher to 126"; "looking for a little bit deeper replacement [mitigation]") and names **"75–80" as the
  depth they need before direction decides**. Classification: **STRENGTHENS_EXISTING_FEATURE**
  (mitigation-depth capture fields); numeric depth values LOW-confidence (transcript digits).

## 4. Displacement / FVG-artifact lessons (headline #2)
FP-B003-05 (the Jul-1 LOSS post-mortem) articulates the exact causal rule behind
`displacement_fvg_artifact_test`: the losing sell followed a down-move that left **no FVGs on 5m or 1H**
("no fair value gaps to the downside… usually they break a level and go on"), which he now reads as a
**sweep, not displacement** — "that was a **weak break** on the one-hour sweep", and healthy moves are
"**sideways, clear the cluster, then dump**" while a single no-FVG leg means full retrace into stops.
**No numeric pip threshold is spoken — FVG-presence remains the right test design.** Sweep + BOS then
flips his bias ("this is a sweep, this is a break of structure → look for longs").
Classification: **STRENGTHENS v0.4 backlog item displacement_fvg_artifact_test** — now backed by a
self-diagnosed LOSS, the strongest possible evidence class. Offline replay before any scoring use.

## 5. Strong/weak/spent level lessons
- **Spent level:** FP-B003-04: *"Don't enter another long here at this OB — it's already mitigated"* —
  the first explicit statement that a mitigated OB must not be re-used. → new v0.4 candidate
  **mitigated_level_exclusion** (hard filter), NEEDS ratification before any scoring use.
- **Fresh/untested = strong:** FP-B003-06: price stopped exactly at a **4H OB** ("why did we stop at
  4140 — this was the four-hour OB"); *"this OB never got retested → this OB will be a support"*; the
  never-retested FVG "is why they stopped at 4120". FP-B003-03: "this level never got tested — they need
  to retest it" (untested-level magnet). → strong_ob_rubric_v0_1: freshness/untested component confirmed
  as dominant; HTF (4H) OBs act as both target and reversal shelf.
- **Touch-count exhaustion:** FP-B003-01 (VWAP): *"they tested so many times — they're gonna lose it"* →
  direct doctrine support for **zone_touch_count (F2, the v0.3 driver)**.
Classification: touch-count + freshness = **ALREADY_IN_ORANGE / STRENGTHENS**; mitigated-exclusion =
**NEW_PROMISING_FEATURE (v0.4 backlog, ratification-gated)**.

## 6. BOS/CHoCH confirmation nuance
- FP-B003-04: *"we need at least one hour candle close above the daily bearish FVG"* else no
  continuation (that's why the fake-out higher never came).
- FP-B003-06: graded multi-TF close stack — Asia-high break + **5m close + 15m close + hourly close
  above = "high confirmation"**; weekly: "no candle close above this week → no continuation, no reason
  for long". Weekly CHoCH used as HTF context in FP-B003-05.
Classification: **STRENGTHENS** ratified `bos_candle_close_confirmed (+confidence)` and the graded
confluence stack — now with a concrete TF hierarchy (5m<15m<1H<W).

## 7. Indicator price-level extraction / Lane-6 pre-mark lessons
- The Dec-2025 series documents the semantics of every panel level the indicator draws: session range
  **boxes** (top/mid/bottom; mid = dotted), **VWAP** (session/D/W/M; institutional fair price;
  above=bullish), **POC/VAH/VAL** (D/W; "reclaim weekly POC → long to next weekly POC"), **SFP dots**
  (sweep prints), **liquidity-sweep marks**, **ORB top/mid/bottom** (mid = "hidden liquidity";
  **no-trade inside the orb**; breakout→retest = entry; "wait in London until they retest the orb"),
  **yellow candles** (market-maker presence → retrace-entry direction filter). All machine-extractable →
  enriches `indicator_price_level_extraction` and the 13-condition alert mapping.
- **Pre-marking is HIS OWN workflow:** FP-B003-04 *"we made this plan yesterday… I set everything up"*
  (levels marked a day ahead, then took a shower through the fill); FP-B003-06 *"they went to a zone
  that I marked before"*; FP-RECAP-001 *"**limit orders are a cheat code — always be prepared with your
  entry zone**"* (and 17-Feb "missed by $2" as the motivating miss). This is direct doctrine support for
  the **Lane-6 pre-mark hypothesis** (levels exist and are actionable before the Telegram post) and for
  limit-at-zone as the canonical follower mechanic (fill_lag_cost lane).
Classification: **STRENGTHENS** Lane-6 builder + alert mapping + R6 lanes 2/3. PM-F001/PM-F002 untouched.

## 8. Management / multi-position lessons
- **Close worst / hold best (verbatim):** FP-B003-04 *"layering — and if it go up two entries, close the
  worst entry, hold the best entry"*.
- **BE after layering:** FP-B003-06 *"trades go in another direction — you need to put your stop at
  break even, of course, [with] a couple of entries"*; recap PDF shows "**SL to entry**" at TP1 as the
  routine (20-02, 24-02, 20-03), "moved SL at 260p" on the 500p winner, "held 10% for higher" (26-02).
- **SL-to-entry / scratch:** FP-B003-05 BTC: "at 6961 we will put stop loss to entry"; TP1-then-stopped
  counted as managed outcome (PARTIAL convention).
- **Weekend/day discipline:** recap 27-03 "closed all positions before the weekend" (R4b-adjacent);
  month-level accounting: FP-B003-06 "1–5 stop losses fine — what matters is ending the month green".
- Size mentions in sources ("bigger size because I was confident", "low lot" on wide stops) recorded as
  **claim-context only — no sizing fields produced anywhere in this batch.**
Classification: **ALREADY_IN_ORANGE / STRENGTHENS** (be_at_average_for_layered, close-worst/hold-best,
tranche schedules, R4b, R6 lane-4 management modeling).

## 9. Claim-quality / accounting-convention lessons
FP-RECAP-001 documents the claim conventions precisely: **"85%+" = 18W/(18W+3L), with 5 MISSED and 4
REMOVED excluded** (flats-excluded convention, matching FP-JOURNAL-001 two years earlier); a **+3,000-pip
"WIN" with no entry/SL/direction** ("big move, community highlight" — a market move counted as a win);
missed trades narrated with full hypothetical favor (-1,000p "missed by $2"); one data error (27-03
short: SL 5075 against a ~4433 market — impossible, excluded from the width dataset). FP-B003-05 adds
lane-separation evidence: BTC signal labeled *"it's a paper trade, but I took it of course on my real
account"* — posted lane ≠ his book, explicitly. Losses ARE posted and dissected honestly (Jul-1
post-mortem), consistent with 0-contradicted history. Classification: **STRENGTHENS** R6 lane-5 claim
discount + the central caveat; capture-only notes.

## 10. New quantitative claim (watchlist)
FP-B003-06: *"above Asia high [with candle-close confirmation], 78–80% chance the market goes higher in
London/US — based on the 22-year data"* → **asia_high_break_session_prior**: NEW_PROMISING but
unverified marketing-adjacent statistic → **WATCHLIST_FEATURE + NEEDS_FORWARD_EVIDENCE** (could be
tested offline against long-horizon XAU session data; never scored without verification + ratification).

## 11. Classification summary
- **ALREADY_IN_ORANGE:** zone_touch_count doctrine; close-worst/hold-best; BE-for-layered; SL-to-entry;
  tranche/partials; stop_outside_zone; weekend close discipline.
- **STRENGTHENS_EXISTING_FEATURE:** stop-width dataset (+19 Feb–Mar samples, median ~$21);
  posted-vs-actual SL gap; bos_candle_close_confirmed TF hierarchy; strong-OB freshness component;
  mitigation-depth capture; indicator level semantics; Lane-6 pre-mark doctrine; limit-at-zone; R6
  lane-5 claim conventions.
- **NEW_PROMISING_FEATURE:** mitigated_level_exclusion (v0.4, ratification-gated).
- **WATCHLIST_FEATURE / NEEDS_FORWARD_EVIDENCE:** asia_high_break_session_prior (78–80% claim);
  conviction-linked behavior notes.
- **NEEDS_HUMAN_REVIEW:** none blocking; mitigated_level_exclusion ratification only if promoted to
  scoring; recap data error noted.
- **REJECTED_OR_DUPLICATE:** 27-03 SL-5075 row (data error); duplicate video copies; EMA module (he
  states he never uses it — no feature).

## 12. Verdicts
- **Detector v0.3: SUPPORTED** (touch-count exhaustion doctrine = F2 driver; confirmation stack aligns
  with graded confluence; nothing contradicts). Live labels UNCHANGED.
- **Detector v0.4 backlog: STRENGTHENED** (displacement_fvg_artifact_test now loss-backed;
  + mitigated_level_exclusion candidate; rubric freshness emphasis). Offline replay before any use.
- **Lane 6: STRENGTHENED** (pre-marking is his own doctrine; panel-level semantics enrich the builder).
- **R6: STRENGTHENED** (limit-at-zone mechanics, SL-to-entry management, lane-5 claim conventions,
  posted-vs-actual stop gap).
- **Human ratification: not required now**; required before any v0.4 scoring use of
  mitigated_level_exclusion (queued).
- **OHLC matching recommendation: YES, later** — the recap's 20 dated Feb–Mar 2026 trades with entry/SL
  prices are deterministically checkable; recommend a **Feb–Mar 2026 OHLC match** alongside the existing
  May option (would independently test the 85% claim). NOT run now.

## 13. Safety attestation
Observation-only throughout. Listener **PID 87988 running/untouched**; no python killed; transcription
NOT rerun (all six outputs present and readable). No execution built (broker/QST/cTrader/nano/copy/demo/
live absent); no permit/lease/order; gates `PAPER/PREVIEW/False/False`; TradingView/Worker untouched.
No lot/risk/account/route/ticket/order fields; labels review-only. **`NOT_INTEGRATION_READY` unchanged.**

## 14. Next exact step
**Cycle 004 / XAU-F001 at first XAU post after tonight's ~22:00Z reopen** (msg 45647 also pending
there), under the full 001B+002B capture spec. Offline queue after that: detector v0.4 offline replay
(now including the strengthened displacement test + mitigated-exclusion candidate); optional Feb–Mar
2026 + May OHLC matching; Orange master re-issue with Batch-003 deltas.
