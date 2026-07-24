# FP-INDICATOR-006 — BLOCKER IMPACT (27 high-priority questions)

A blocker is only "resolved" with **explicit, measurable** on-screen/verbal evidence. Newly-visible values are
Farouk's **current config** (no reset-to-default shown → not proven factory defaults).

| # | Question | Outcome | Evidence |
|---|---|---|---|
| 1 | A+ / A+++ formula | **UNCHANGED** | "A+ setup should be a sell/buy here" — qualitative; no formula/count |
| 2 | minimum confluence count | **UNCHANGED** | "look for confluence" — no count |
| 3 | all-boxes veto vs graded | **UNCHANGED** | not addressed |
| 4 | CHoCH pivot settings | **RESOLVED (current config)** | **CHoCH pivot length = 5**; Show CHoCH ON (29:06 frame) |
| 5 | FVG lookback | **RESOLVED (current config)** | **FVG lookback = 50 bars** |
| 6 | minimum FVG ATR threshold | **RESOLVED (current config)** | **Min FVG size = 0.5 × ATR** |
| 7 | BPR overlap threshold | **RESOLVED (current config)** | **Min BPR overlap = 0.2 × ATR** |
| 8 | normal OB impulse threshold | **UNCHANGED** | ORDER BLOCK/LIQUIDITY section header seen; values below cut-off (not scrolled to) |
| 9 | Strong OB impulse threshold | **UNCHANGED** | not shown |
| 10 | equal-high/low lookback | **UNCHANGED** | not shown |
| 11 | FVG partial vs full fill | **NARROWED (mechanic)** | **Auto-remove filled FVG/BPR = ON** → a *filled* FVG is auto-removed; partial-fill rule still not numeric |
| 12 | IFVG conversion | **UNCHANGED** | IFVG toggle exists + "IFEG" entry example; no conversion rule |
| 13 | mitigation threshold | **UNCHANGED** | "mitigated/unmitigated" heavily used but qualitative; timeframe-relative; no number |
| 14 | setup expiry | **NARROWED (mechanic)** | **Max zones kept per type = 10** + auto-remove; weekly session reset — but NO time-based per-setup expiry |
| 15 | nBOS definition | **UNCHANGED** | term not used in this session |
| 16 | POC "T" | **UNCHANGED** | not explained ("just look at the data") |
| 17 | Volume Profile window | **UNCHANGED** | no VP/POC/VAH/VAL discussion of substance |
| 18 | Asia-session hours | **NARROWED (methodology, not indicator field)** | edge note "ASIA RANGE (00-07 UTC)" — a research note, NOT the indicator's session-hours setting |
| 19 | London-session hours | **UNCHANGED** | "London breakout" referenced; no explicit hours |
| 20 | US-session hours | **UNCHANGED** | US high/low used; no explicit hours |
| 21 | canonical timezone | **UNCHANGED (confirmed user-local)** | chart TZ = **UTC+2** this session (was UTC+1 in the alert shots) → confirms NO canonical system TZ |
| 22 | candle-close vs intrabar BOS | **NARROWED (practice)** | repeatedly "need a candle close above the zone; no candle close = no entry" — corroborates candle-close for entries; does NOT settle the 016-vs-021 spec contradiction |
| 23 | alert timing | **UNCHANGED** | alarms confirmed to exist/fire on events; NO bar-close/intrabar detail |
| 24 | repaint / post-close mutation | **UNCHANGED** | not addressed |
| 25 | alert message content | **UNCHANGED** | not shown |
| 26 | duplicate-alert behaviour | **UNCHANGED** | not addressed |
| 27 | Campaigns 001-004 panel demonstrated | **RESOLVED (CONFIRMED)** | the CHoCH/Asia-break/OB-retest/Current-OB/Fresh-OB panel is shown LIVE as this indicator's output |

## Net
**Resolved (current-config):** #4,5,6,7 (CHoCH pivot 5, FVG lookback 50, Min FVG 0.5 ATR, Min BPR 0.2 ATR) + #27 (panel attribution).
**Narrowed:** #11, #14 (auto-remove/max-zones mechanics), #18 (Asia 00-07 UTC methodology), #21 (TZ confirmed user-local), #22 (candle-close practice).
**Unchanged/still blocked:** #1,2,3,8,9,10,12,13,15,16,17,19,20,23,24,25,26 — incl. the whole A+/A+++ grade formula, OB-impulse thresholds, mitigation numeric, POC-T/VP, and **all alert timing/repaint/payload/duplicate** (still requires FP-LIVE-OBSERVATION-001).
