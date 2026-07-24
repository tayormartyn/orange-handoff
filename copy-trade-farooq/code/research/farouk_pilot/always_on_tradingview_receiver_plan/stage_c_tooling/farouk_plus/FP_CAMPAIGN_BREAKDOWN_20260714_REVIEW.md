# FP-CAMPAIGN-BREAKDOWN-20260714 — 14 July "gold/btc trade breakdown" (.mov) review

**Classification: RETROSPECTIVE_EXPLANATION.** Cannot create/backdate a blind hypothesis, alter any
pre-trade snapshot, rewrite F001/F002 outcomes, or change constitution/scorers/gates/pre-marks/lanes.
Observation-only. Machine twin: `derived/transcripts/breakdown_20260714/`.

## Task 1 — Durable ingestion (verified)
- Original path: `C:\Users\Marty\Downloads\Schermopname 2026-07-14 om 17.47.54.mov` (unchanged).
- **sha256 `d871ca8474b197f8216a1cd9813cd1bc473d9ee2df67ffd3233e32993d07e023`** (computed twice: ingest + transcriber, match).
- size **62,938,505 B** · duration **95.9 s** · 4096×2192 · audio present.
- Import 2026-07-15 (UTC); asset id FP-CAMPAIGN-BREAKDOWN-20260714; provenance = Discord .mov forwarded by Farouk (ref msg 45742, 2026-07-14T15:53Z), MANUAL_DISCORD_FORWARD, RIGHTS_PENDING_PRIVATE_REVIEW.
- Tools: ffmpeg (frames) + faster-whisper 1.2.1 base.en cpu/int8 vad (`.venv-vision`), model cached, offline.
- On-screen recording clock **17:49:27 UTC+2 = 15:49Z** (consistent with msg 45742 15:53Z).
- Visible symbols/TF/dates: **BTCUSDT.P 1h OKX** (~64,770; panel TF60 Asia-break HIGH OB-retest 63892) →
  **Bitcoin/USDT 4h Binance** (TF240; magnet 71,280; range 58,740–71,280) → **Gold Spot/USD 5m Pepperstone**
  (XAUUSD 4072.93; TF5 Asia-break HIGH OB-retest 4065.94; London High ~4105, US Low ~3989, Asia Low ~3980,
  London Low ~4012; dates 13–14 Jul). **Gold VISUAL ≈ final ~13 s (chart switches to gold near the end);
  gold SPOKEN ≈ 65–90 s (~25 s / ~26%); the remainder is BTC.**

## Task 2 — Timecoded transcript (verbatim; faster-whisper, garbles flagged)
| ts | statement (verbatim / [garble→fix]) | conf | symbol/TF | subject |
|---|---|---|---|---|
| 0.0–14 | "manipulation sitting here… came to this level… equal highs, now we get swept, we come above this zone so you should take profit here. If you got stopped out at entry [he] also gave a trade so you should also be in his trade" | med | BTC 1h OKX | BTC management/TP |
| 18–38 | "equal lows [sipping→sweeping]… I think we're gonna go higher to this [FPG→FVG]… 66,800 / 66,600… flat candle… whole level swept then look for sells" | med | BTC | BTC structure/target |
| 44–63 | "still think we're gonna go to 71 level, holding the monthly level, tapped it, lower-low higher-low… made higher-high on the 4h… if the candle closes like this in 11 minutes we go higher… retest… another long BTC" | med | BTC 4h Binance | BTC daily plan |
| 63–79 | **"for gold trades, [5/5.1] 1-hour candle close look for longs, and we don't have any OB sitting here so we should go to this zone and maybe even a little bit higher"** | med-low | (spoken; BTC still shown) | **GOLD bias = LONG** |
| 79–90 | "we went to this whole level, we swept all this liquidity, you see they [are] mimicking each other, gold and BTC" | med | GOLD 5m Pepperstone (91s) | gold recap + correlation |
| 90–94 | "hope you guys made some good profit today, tomorrow we fight again, goodbye" | high | — | sign-off |

No numbers/words invented; unclear tokens flagged. Gold segment is short and high-level (no zone/stop/leg detail).

## Task 3 — Campaign association matrix
| segment | vs F001 (LONG 4007–19 SL3985) | vs F002 (SHORT 4084–94 SL4144) | classification | evidence | conf |
|---|---|---|---|---|---|
| 0–63 (BTC) | n/a | n/a | **UNRELATED** (BTC campaign 45683/45716/45735) | BTC charts + "another long BTC" | HIGH |
| 63–79 gold "look for longs, no OB, go to this zone maybe higher" | weak directional agree (LONG) | **contradicts** (this is long-bias) | **GENERAL_MARKET_PLAN** (forward gold long) | LONG bias, no zone/stop given | MED |
| 79–90 gold "swept all this liquidity… gold/BTC mimicking" | weak: the swept-lows→long narrative aligns with F001's long | not mentioned | **GENERAL_MARKET_PLAN / weak F001 context** | 91s XAUUSD 5m shows sweep of ~3989–4012 then rally to ~4105 | MED |

**Resolution: the video does NOT explain F001 or F002's construction. It is a BTC breakdown + a brief forward gold-LONG comment. F002 (short) is never mentioned. No segment is XAU-F001_CONFIRMED or XAU-F002_CONFIRMED.**

## Task 4 — Resolve the six consolidation ambiguities (against the ACTUAL video)
*(Verdicts revised after red-team pass — see §Red-team below; two were softened from CONTRADICTED.)*
1. "bearish HTF directional bias" → **PARTLY_CONTRADICTED** — his stated *near-term* gold bias here is **LONG** ("look for longs", ts 63–74) off swept lows. This is solid, but a forward LTF/intraday long spoken over a 5m frame does NOT logically refute an *HTF-bearish* bias (one can scalp longs into an HTF sell zone), and F002 remained a live SHORT. Correct reading: **directional tension** — the video's stated gold bias is long, not the bearish read the consolidation inferred, but "bearish HTF" is not disproven.
2. "F001 = textbook DR-306 3-point entry" → **SUPPORTED_ONLY_BY_OTHER_EVIDENCE** — the video shows none of F001's legs; DR-306 support is Telegram-only.
3. "F002 = VR-14/16 wide HTF stop" → **SUPPORTED_ONLY_BY_OTHER_EVIDENCE** — F002 not in the video.
4. "~4095–4100 pivot = realised target/rejection" → **PARTLY_SUPPORTED** — 91s frame shows rally to London High ~4105 then pullback to 4072; but the video frames ~4100 as the LONG target ("go to this zone maybe higher"), not a short's rejection.
5. "+50 BE overridden to ~+90–100" → **STILL_UNKNOWN** (from this video) / SUPPORTED_ONLY_BY_OTHER_EVIDENCE (Telegram) — the video never discusses BE timing.
6. "Sunday HTF sell zones not reached → LTF-reactive execution" → **STILL_UNKNOWN** — the un-reached Sunday HTF sell zones are **4160–70 / 4250–60**; price reached only ~4105, so "not reached" is NOT refuted (my earlier draft wrongly used the long's 4105 target to contradict it). And "deliberate top-down LONG" is not shown — the video has **no HTF gold chart**, only the 5m frame + "1-hour candle close look for longs"; a daily/HTF→LTF cascade is not evidenced. Verdict downgraded from CONTRADICTED.

## Task 5 — Sunday method vs 14 July (video-confirmed rows only)
| Sunday rule | Video-stated application | Pre-trade evidence | Actual campaign | Verdict |
|---|---|---|---|---|
| Liquidity/session sweep → entry (DR-204) | "swept all this liquidity… look for longs" | 91s: Asia/US/London lows ~3989–4012 swept before the rally | F001 LONG off the low region | **CONSISTENT_APPLICATION** (gold long) |
| Unmitigated OB selection (VR-15) | "we don't have any OB sitting here so go to this zone and maybe higher" | not independently verifiable pre-trade | F001 zone 4007–19 | **NEW_DETAIL** — "no OB → target the next zone/higher" (absence-of-OB reasoning), qualitative |
| HTF>LTF top-down bias | gold LONG continuation stated | — | F001 long | **PARTIAL_APPLICATION** (bias stated, construction not shown) |
| Cross-asset "gold and BTC mimicking each other" | explicit | — | — | **NEW_DETAIL** (correlation aside; excluded from gold lanes per policy) |
| F002 short / bearish zones | **not mentioned** | — | F002 | **INSUFFICIENT_EVIDENCE** |
| Stop / target / BE / partials for gold | **not shown** | — | F001/F002 | **PRIVATE_STATE_REQUIRED** |

## Tasks 6–7 — Decision trace & rejected levels
**No top-down (HTF→LTF) gold trace is recoverable — the video shows NO HTF gold chart, only a 5m frame.**
What is recoverable (5m-only, spoken): liquidity = sweep of the session lows visible on the 5m
(US Low ~3989 / Asia Low ~3980 / London Low ~4012); H1 trigger = "1-hour candle close, look for longs"
(spoken, no H1 chart shown); OB = **none in-zone** ("no OB… go to this zone maybe higher"); session =
London; long target ≈ ~4105 (London High, reached on f_91s). DAILY/H4/H1 tiers are **STILL_UNKNOWN** (not
shown/stated). **Rejected-level ranking: INSUFFICIENT_EVIDENCE** — the gold segment ranks/rejects nothing;
f_91s *displays* many drawn levels but the video never articulates a ranking, so the ranking function is
NOT recoverable. F002 has NO trace here.

## Task 8 — Rule register update (no duplication; existing DR/VR ids)
- **DR-204 (sweep→entry): SUPPORTED** — one more gold instance (swept session lows → long). status REPEATED_CANDIDATE.
- **NEW qualitative sub-note VR-23 (proposed, OBSERVED_ONCE): "absence-of-OB → target the next zone / 'a little bit higher'"** — Farouk uses *no unmitigated OB in the immediate path* as a reason to expect continuation to the next level; provenance ts 63–79s; qualitative; NOT numeric; supporting campaign F001 (weak); confidence LOW; **status OBSERVED_ONCE — not a live rule.**
- **Cross-asset correlation note (OBSERVED_ONCE):** "gold and BTC mimicking each other" — recorded, excluded from gold expectancy/lanes (cross-asset policy).
- **CORRECTION to TDX_CONSOLIDATION_20260715 (softened after red-team):** the campaign's *stated near-term
  gold bias* is **LONG**, which qualifies the consolidation's inferred "bearish" read — but does NOT disprove
  an HTF-bearish bias (F002 stayed a live SHORT). Row-1 → PARTLY_CONTRADICTED (directional tension);
  row-6 → STILL_UNKNOWN (HTF sell zones 4160–4260 were never reached; only ~4105 was). No pre-mark boundary
  changed; no rule promoted.

## Red-team pass (read-only agent) — findings applied
0 CRITICAL; **2 MATERIAL** (both fixed above): (8.1) #1 over-labeled CONTRADICTED → **PARTLY_CONTRADICTED**;
(8.2) #6 over-labeled CONTRADICTED (conflated the long's ~4105 target with the un-reached 4160–4260 HTF sell
zones; asserted a "top-down" gold trace with no HTF gold chart) → **STILL_UNKNOWN**, and Tasks 6–7 downgraded
to 5m-only. MINORs fixed: gold *spoken* content is ~25 s / ~26% (65–90s) vs gold *visual* ~13 s (chart
switches near the end) — the two are now separated; "5/5.1" prefix marked unrecoverable (only "1-hour candle
close, look for longs" is transcript-solid); Asia Low ~3980 separated from US Low ~3989; Task-5 "pre-trade
evidence" column relabeled **chart-history (retrospective)**. No fabrication found; all frame numbers
(64,770 / 63892 / 71,280 / 58,740 / 4072.93 / 4105 / 4012 / 3989 / 3980) confirmed against f_03s/f_51s/f_59s/f_91s.

## Task 9 — Top-down engine delta
**NONE justified.** ~13 s of high-level gold content, single retrospective video → no deterministic
component is warranted (no numeric threshold, no repeatable ranking observable). Fail closed. (A future
qualitative `stated_directional_bias` evidence field is *conceivable* but not built now — one observation
must not become a live component.) The strict follower is unaffected regardless.

## Task 10 — Data sufficiency
**NOT sufficient** for a D1/H4/H1/M15/M5 reconstruction of the 14 July setup. All multi-TF gold CSVs
END 2026-07-10 20:xxZ; the only 14 July data is the 540-row 1m partial (07:30–16:29Z). No D1/H4 export
exists at all. **Exact missing export required:** XAUUSD **2026-07-11 00:00Z → 2026-07-15 00:00Z**, 1-minute,
UTC, Pepperstone (5m/15m/H1/H4/D1 all resample from 1m). One export.

## Safety
Retrospective; nothing enters v0.3; no pre-trade snapshot/blind hypothesis created from it; original file
unchanged; gates PAPER/PREVIEW/False/False; NOT_INTEGRATION_READY unchanged.
