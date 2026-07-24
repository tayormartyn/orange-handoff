# F007 POST-TRADE VIDEO REVIEW (FEATURE / SOURCE_REPORTED — never Lane A truth)

Source: corpus `fp-2026_07_21_farouk_post_trade_breakdown_f007`, sha256 `022ff2aa86bace0ef0da3a20fac80b01efeed5142c8f6d43e0e44cc0fedfe430`, 6.3 min, 60 segs, ingested 2026-07-21 (tier PERSONAL_LIVE_METHOD_UNCONFIRMED, post-trade retrospective, XAUUSD, linked XAU-F007-20260721). Transcript: `corpus/transcripts/fp-2026_07_21_farouk_post_trade_breakdown_f007.txt` (small.en + frozen DOMAIN_PROMPT, vad_filter, VAD_APPROXIMATE header).

**No pre-registration contamination possible: F007's T=0 freeze (logical `f74697194cbbb359`, decision 08:26:42Z) and its frozen Lane A outcome (+5.38 pips/unit, BE scratch, terminated ~09:29Z) were both durable ~9 hours before this video existed (~17:29Z). Nothing below alters F007's Lane A records; all of it is SOURCE_REPORTED evidence only.**

## 1. What did his F007 actually make? — SOURCE_REPORTED_OUTCOME (operator priority question)

He states a **result and how it ended**, but **no explicit final exit price**:
- [00:00:00] *"Really profitable day today… Fortunately we got stopped out when we put stop loss entry and then it went up."*
- [00:01:14] *"It ran up to more than 100 pips, 90 pips to 100 pips… I closed, of course… profit, profit, profit."*
- [00:02:05] *"we had a couple of entries. I had, I think three, four entries here, went up, closed all entries, made a really good profit. Let one runner… high probability that this level will make another high high… they came down. Of course, we got stopped out."*
- [00:01:58] *"we have put stop loss to entry, we got stopped out… after 90 or 100 pips, depends on your intervals."*

**SOURCE_REPORTED_OUTCOME (registered):** multi-entry long entered ~4059 ("59 ish"), the run reached "90–100 pips", he **closed the entries into profit** and **left one runner**, which was **stopped at breakeven (sl-to-entry)** when price came back down. Net stated: *"really profitable day."*

### Divergence vs Lane A (first STATED, not inferred, measurement of LANE_A_ENTRY_MODEL_ADVERSE_DIVERGENCE)
| | Value | Basis |
|---|---|---|
| Lane A strict realized | **+5.38 pips/unit** | Frozen: **near leg 4063 filled only**; mid 4058 + far 4053 **CANCELLED** (SL_TO_ENTRY cancels unfilled legs); near BE-scratched |
| Source-reported (video) | **~90–100 pips** banked on closed entries + runner BE | His narrative, this video |
| Prior inferred evidence | 09:54Z chart position still open **+943 USD** | Operator screenshot (already recorded) |
| **Adverse gap** | **≈ +85 to +95 pips/unit** that Lane A's entry model did not capture | approximate — see caveats |

**Mechanism (already established, now confirmed against a stated outcome):** Lane A's 3-leg model filled only the **top** near leg (4063) and cancelled the lower legs on SL_TO_ENTRY, then scratched at BE for +5.38. Farouk's **actual fills were lower** (4060.55 / 4059.71 per his own result cards) and he closed them into the 90–100 pip run. The entry-placement model is the adverse mechanism. The 09:54Z open-+943 chart *inferred* this; the video is the first time he *states* the profitable outcome directly.

**Caveats (do not overstate):**
- His "90–100 pips" is a **narrative peak-capture claim**, not a ledgered per-unit result; not perfectly like-for-like with Lane A's modeled realized +5.38.
- **Within-source inconsistency:** the video says *"three, four entries"*; his own result-card screenshots showed **two** fills (4060.55, 4059.71). His count is unreliable even about his own trade.
- **F007's frozen Lane A +5.38 STANDS. Not adjusted.** Recorded as divergence evidence only (D-045/K governance).

## 2. Unposted terminal? — NO. F007 does NOT repeat the F006 pattern (K-018 not strengthened)

Unlike F006 (runner BE stop-out **entirely silent**, disclosed only on video), **F007's terminal was posted to the channel**:
- msg **45974** (09:02:48Z) `TP1_TAKE` + `SL_TO_ENTRY`; msg **45977** (09:09:39Z) `SL_TO_ENTRY`; msg **45973** (09:02:24Z) `CLOSE_WORST` + `HOLD_BEST`.

The sl-to-entry that produced the BE scratch was a **posted, followable instruction**; Orange tracked the BE from the posted stop. The video restates that same outcome and adds nothing that was withheld from the channel. **Therefore F007 is NOT a second instance of the unposted-terminal pattern, and K-018 is not strengthened here.** This is useful *negative* evidence: the F006 silent-stop is not (yet) shown to be systematic.

## 3. Stated reasoning — discrete claims, tagged, novelty-gated (nothing promoted)

| # | Claim (video) | Tag | Novelty / prior-art |
|---|---|---|---|
| a | Mark Asia high / Asia low; from that zone look for HTF rejection / support | PRE-TRADE-OBSERVABLE | ALREADY_KNOWN (Asia-level + HTF doctrine) |
| b | Asia bullish → Frankfurt above Asia high → London higher = up-momentum | RETROSPECTIVE (session narrative) | observational |
| c | Buy ~4059; 5m OB; "a low that failed" (sweep); "candle close above = retest continuation" | mixed (OB/sweep observable; retest-continuation doctrine) | ALREADY_KNOWN (gate → K-014 OB/retest family) |
| d | Closed all entries into profit, kept one runner for a further higher-high | RETROSPECTIVE (management) | observational |
| e | Runner sl-to-entry, stopped out | RETROSPECTIVE (outcome) | — |
| f | US-session A++ long at 4038/4039 (1h breaker OB + mitigation wick + 5m OB confluence) that **never triggered** ("didn't come, never got tested") | PRE-TRADE-OBSERVABLE (untriggered) | observational; a *setup that did not fire* |
| g | Forward: gold "110/120 to close the gap"; OB under 10 = sell zone; broke Sunday trendline | forward | ties to pre-registered H-FPL-05 context |

Novelty gate: doctrines match prior art (K-014 retest/OB; continuation/higher-high known). **No rule promoted from a single video.**

## 4. Live vs retrospective rationale — reliability-of-post-hoc-explanation evidence

- **LIVE** (msg 45976, 09:07:27Z): *"1h Bullish FVG tapped / 1h Low Sweep / 1/3m Bullish CHoCH"* — three specific SMC features.
- **RETROSPECTIVE** (this video): frames the same entry via **Asia high/low + London momentum + 5m OB + "a low that failed"** and a **candle-close-above retest** thesis.

| Live feature (45976) | Restated in video? |
|---|---|
| 1h Bullish **FVG** tapped | **OMITTED** — no FVG mentioned for the entry |
| 1h **Low Sweep** | **RETAINED** (loosely) — "we had a low… they failed" |
| 1/3m Bullish **CHoCH** | **OMITTED** — no CHoCH mentioned |
| — Asia/London session momentum | **ADDED** (not in the live call) |
| — higher-high runner thesis | **ADDED** |

**No hard contradiction, but the two most specific live features (FVG, CHoCH) are dropped and the setup is reframed in different structural vocabulary retrospectively.** Combined with the Lane C finding that **none** of the three live features is Orange-computable, this is direct evidence that his live rationale's specificity is **not stable** under his own post-hoc retelling — relevant to any future attempt to use his stated rationales as labels. Recorded as evidence; not a rule.

## 5. Leg-selective management (FR-058) — PARTIAL corroboration, not a clean fourth

Video: *"closed all entries, let one runner… we put stop loss to entry, we got stopped out."* This corroborates the **sl-to-entry + single-runner** management family and matches the posted 45973 `CLOSE_WORST`/`HOLD_BEST` / 45974 `TP1_TAKE`/`SL_TO_ENTRY`. **But he does NOT explicitly say "close the worst, hold the best"** — he says "closed all entries, let one runner," silent on which leg is held. So this is a **partial/adjacent corroboration of the management doctrine, NOT a fourth explicit close-worst/hold-best statement.** FR-058 remains G1-confirmed CLOSE_WORST_HOLD_BEST on its existing triple corroboration; unchanged.

---
**Nothing promoted. F007 Lane A records untouched (+5.38 stands). Gates unchanged. SOURCE_REPORTED evidence only.**
