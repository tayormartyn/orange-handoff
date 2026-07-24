# Farouk Two-Video Method Lessons Report (FP-LIVE-VIDEO-EXPLAINER-001 + 002)

**Mode: VIDEO EXPLAINER INTAKE — OBSERVATION ONLY, SINGLE-SESSION.** Date 2026-07-11.
Both videos = private research evidence, **RIGHTS_PENDING_PRIVATE_REVIEW**, no redistribution, summaries
only. All structured outputs validator-passed (negative check: `broker_route` key rejected). Deterministic
OHLC remains authority — everything below is his narrative, cross-checked against our matched data where
possible. Listener PID 87988 untouched. Gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY`
unchanged. Machine-readable: `farouk_two_video_method_lessons.json`.

## 1. What the videos resolve (mapped to open Orange questions)

| open question | video answer | status |
|---|---|---|
| **Why does he survive where literal follower SL-to-entry scratches?** (Step-8D-A) | Three mechanisms, all now on tape: (a) his fills are earlier/better ("early entry", drawn zones wider/higher than posted); (b) **his stop is discretionary and often wider than posted** ("the stop-loss what I took was a little bit higher", "bigger stop loss because this is a mitigated level"); (c) his feed is **Vantage**, not Pepperstone. | **ANSWERED — confirms fill+stop divergence, adds feed divergence** |
| **Invalidation/stop-width as binding constraint** (8D-A, Lane 6) | Stop width is a *function of level type* (mitigated level → bigger stop) and is *adaptively re-learned* ("next time I'm gonna put my stop loss a little bit higher"). | **CONFIRMED as the binding variable; now has a construction rule to learn** |
| **R2/R2b re-entry limits** | **His own doctrine: "after the range you don't enter again. You have your stop loss. That's it."** June's re-entry chains broke his own rule — and produced both verified SL losses. | **STRONGLY SUPPORTS R2b** |
| **R4b late-day cutoff** | Not directly addressed; the FOMC "don't take a lot of trades" discipline is adjacent (event risk). | NEUTRAL — unchanged |
| **R6 follower-fill expectancy** | "If we get stopped out [at BE] I don't care… if we didn't, we get 500 pips" — **BE-scratching is deliberate**; Model B's mechanism is his real mechanism, but anchored to HIS earlier fill. Follower expectancy must model the *fill-lag* (post-time vs his early entry) as the primary cost. | **SUPPORTS R6; sharpens it: fill-lag is the cost driver, not the scratch rule itself** |
| **Lane 6 pre-marking** | His levels are **his indicator's own outputs** (panel: CHoCH/Asia-break/OB-retest/Fresh-OB with exact prices) + session liquidity map. He also pre-announces levels a day ahead (4150/4120/4099/4165/4020 in video 002; **4150–4180 & 4430–4480 supply boxes + "80–84 BE" in video 001**). | **STRONGLY HELPS — pre-marking = reading his indicator lane; two concrete forward PRE_MARK seeds registered** |
| **Multi-position legs** (8D) | Tutorial on tape: 4–5 equal tranches across the zone, one stop, tranche exits, BE after profit. Matches the 8D schema exactly. | CONFIRMS the leg model; no schema change needed |

## 2. Level-construction lessons (the recipe, as taught)

Asia High/Low (+ London/US lows) are the primary liquidity frame; a **lost Asia low with a decisive candle
close** flips bias short (his claimed "22-year data, 100%" — marketing register, but the rule is
mechanical); entries at **unmitigated OB/FVG/BPR clusters** on the retest, confirmed by **M5/M15 CHoCH**;
HTF (4H) bias can veto counter-direction trades ("I'm not looking for buys today at all"); all of it is
rendered live by his indicator stack — **the levels are machine-readable before he posts**.

## 3. New Farouk-plus candidate features

| feature | class |
|---|---|
| stop_width_by_level_type (mitigated → wider; learnable from his posted-SL distribution + narration) | **PROMISING_SCORING_FEATURE** (Lane-6 invalidation track input) |
| fill_lag_cost (post-time fill vs indicator-level first-touch — the real follower cost) | **PROMISING_SCORING_FEATURE** (R6 refinement) |
| feed_divergence (Vantage vs Pepperstone reference) | WATCHLIST_FEATURE (bounded ~$0.5–2 by S2/J17 evidence) |
| event_risk_discipline (FOMC "don't trade a lot") | WATCHLIST_FEATURE (joins f1 news; needs calendar join) |
| his_own_no_reentry_doctrine_compliance (does the post violate his stated rule?) | **PROMISING** — a compliance flag, strengthens R2b |
| "22-year Asia-low statistic" as claimed basis | NEEDS_FORWARD_EVIDENCE (unverifiable claim; the *rule* is testable, the statistic is not) |

## 4. Contradictions with current Orange assumptions

1. Day-1/3 ledger treated posted zones as *his* entries — **wrong**: posted zones are follower rails; his
   entries are earlier and his drawn zones wider (already suspected via widgets; now confirmed narratively).
2. The "pip inflation" framing is further softened: several "inflated" claims are accurate **from his
   fills/stops** — the divergence is structural (fill-lag + stop-width + feed), not primarily rhetorical.
   (J11's 800-vs-629 remains a genuine overstatement.)
3. Model A's optimistic exits are PARTIALLY vindicated (he does bank at posted TP levels), but its
   follower-fill assumption remains too generous; Model B's mechanism is his real mechanism with the wrong
   anchor. The band-collapse still requires the 8C instruction-timing capture — unchanged.

## 5. OHLC matching needed?

No new matching required: both videos explain already-matched setups (S2/S3/S4 — all deterministic).
Forward: the two pre-mark seeds (4150–4184 sell region; 4430–4480 weekly supply) become PRE_MARK_CANDIDATE
records testable against next week's OHLC when posts/alerts arrive.

## 6. Safety confirmation

Videos registered read-only (hashes preserved; originals untouched in Downloads); transcripts kept in
ephemeral session scratchpad only (regenerable locally; not persisted, not exposed); no volume/account/
ticket data recorded (platform name only, as evidence); all structured outputs validator-passed; no
broker/QST/cTrader/nano/copy/demo/live execution; no permits/leases/orders; gates unchanged; listener PID
87988 running; no TradingView/Worker/R2/secret action; nothing trade-ready. `NOT_INTEGRATION_READY`
unchanged.

## Next step

1. Register the two forward pre-mark seeds as PRE_MARK_CANDIDATE records when Cycle 002 opens (Sunday
   eve/Monday): sell region ~4150–4184 (BE plan "80–84"), weekly supply 4430–4480.
2. Add `stop_width_by_level_type` + `fill_lag_cost` to the Lane-6 invalidation track and R6 refinement
   backlog.
3. Run Cycle 002 on the next gold-trades post under the 8C+8D spec.
