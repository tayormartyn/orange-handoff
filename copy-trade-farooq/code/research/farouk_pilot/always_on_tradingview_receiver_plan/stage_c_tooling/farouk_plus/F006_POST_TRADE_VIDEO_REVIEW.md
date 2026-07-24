# F006 POST-TRADE VIDEO REVIEW (FEATURE/SOURCE_REPORTED — never Lane A truth)
Source: corpus `fp-2026_07_20_farouk_post_trade_breakdown_f006`, sha256 `de34a426ab0ce7680461c556677fc4033bd4bc8b2a258aceb1f45f7d84a67b75`, 9:39, ingested 2026-07-20 (tier PERSONAL_LIVE_METHOD_UNCONFIRMED, post-trade retrospective, XAUUSD). **No pre-registration contamination: F006's T=0 freeze (80fc8f0c, 14:49Z) and committed blind hypothesis predate the video (~18:22) — both durable hours before any retrospective content existed.** Transcript: corpus/transcripts/… (small.en + domain prompt, 90 segs).

## 1. The unposted stop-hit — SOURCE_REPORTED, and INDEPENDENTLY CONFIRMED from our own bars
His words: [07:15] *"unfortunately my stop plus entry got hit, we had this dump, stop plus entry got hit"*; [09:21] *"unfortunately again stop plus entry hit… big wick"*. Never posted to the channel (messages 45936–45945 contain no close/stop post; result cards show only profitable partials).
**Orange's PEPPERSTONE bars (read-only):** after the 15:10Z `tp 1 sl entry` instruction, price first traded down at **16:41Z — single bar low 4001.30** — through his fill/BE region (runner fill 4005.72; avg ≈4009) — then recovered (post-dump high 4018.53). The published stop **3992 was never touched**; the far leg 4000 was **never touched** (low 4001.30).

## 2. The defect's consequence — stated plainly (operator question 3)
- **Correctly-configured Lane A** (stop moved to entry per the dropped instruction): stop event **at 16:41Z, price 4005** — runner BE-scratched, campaign complete.
- **Lane A as configured** (stop still 3992 due to PARTIAL_INSTRUCTION_SILENT_LOSS): **registered NOTHING** — 3992 never traded. The tracker still shows the runner alive. **Yes: the defect made Orange blind to precisely the stop event Farouk described.** It did not just produce a wrong number; it suppressed the event entirely.
- **K-018 partial mitigation PROVEN:** Orange detected the unposted event independently from price alone (given the correct stop level). Stop events are detectable without his posts; entries/fills remain the harder blind spot.
**No Lane A state was altered by this review — F006's records stand untouched pending the parser fix / natural close.**

## 3. Survivorship evidence (n=1, linked to K-018)
Posted F006 record: profitable partial cards only (+63/+401/+597/+793/+961-style). Actual complete record includes a BE stop-out on the runner, disclosed only in a video. **His posted card record is incomplete and cannot be used to estimate follower expectancy.** (Lane A's own accounting — partials banked, runner scratched at BE had the stop moved — remains the only complete follower-truth ledger.)

## 4. Methodology extraction (novelty-gated; nothing promoted from a single video)
| Statement | Tag | Gate/prior-art |
|---|---|---|
| Untapped 1h OB above = magnet after Asia high forms | PRE-TRADE-OBSERVABLE | ALREADY_KNOWN (indicator audit §3 magnets; gate matched OB-family claims — human review confirms prior art) |
| **"We broke Asia high but there's no room — resistance overhead → prefer sells / wait for the dump"** | PRE-TRADE-OBSERVABLE | NOT in registers — a stated **setup-weakening condition** on the Asia-break long (risk-reward filter). Recorded as HYPOTHESIS_ONLY observation; joins the H-FPL-01 design space (condition that cancels the setup); NOT promoted |
| 5m OB + untested ChoCH after London-low sweep = long zone w/ tight stop ("longed 4009/4010, SL ~3990, target 4040") | RETROSPECTIVE (his own trade narration) | consistent with known doctrine; fills corroborate the four-entry evidence |
| Backup buy zone = session liquidity + FVG + BPR + fresh OB below | PRE-TRADE-OBSERVABLE | ALREADY_KNOWN (stacked-confluence doctrine) |
| "If we go higher, high chances 4050–60 — 1h + 4h OB — that's for tomorrow" | PRE-TRADE-OBSERVABLE (forward) | Restates the pre-registered H-FPL-05 sell zone from Sunday — noted for the Friday scoring context |
| BTC: sell 67-ish after rejection, buy limit below (unchanged) | forward | consistent with Sunday plan |

## 5. Corrections cross-check
The video confirms Lane-A-relevant sequencing: his long was ~4009–4010 (cards 4013.02/4009.64/4007.68/4005.72), "stop 3990-something" ≈ published 3992, partials at TP levels, runner BE-scratched on the 16:41Z wick. Lane A divergence (three legs, stop unmoved) already recorded at D-028.
