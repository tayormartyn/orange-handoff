# Gate G — Classification Summary v0.2

Replay of `raw_farouk_text_classifier_v0_2` over the **74** Gate G captures
(window 2026-07-08T22:15:04Z → 2026-07-09T09:51:02Z). Descriptive counts only — no execution meaning.

## By event_family

| event_family | count |
|---|---|
| ENGULFING | 27 |
| A_SIGNAL | 24 |
| LIQUIDITY_SWEEP | 10 |
| BPR | 8 |
| STRUCTURE (CHoCH) | 5 |

## By event_type

| event_type | count |
|---|---|
| BEARISH_ENGULFING | 14 |
| A_SHORT | 14 |
| BULLISH_ENGULFING | 13 |
| A_LONG | 10 |
| BPR_TAPPED | 8 |
| SWEEP_HIGH | 6 |
| SWEEP_LOW | 4 |
| CHOCH_DOWN | 3 |
| CHOCH_UP | 2 |
| A_PLUS / A_PLUS_OR_BETTER / A_TRIPLE_PLUS | 0 |
| BPR_FORMED | 0 |

## By direction (bias descriptor only — NOT order side)

| direction | count |
|---|---|
| SHORT_HINT | 23 |
| LONG_HINT | 19 |
| SHORT | 14 |
| LONG | 10 |
| (none / NEUTRAL) | 8 |

## By confidence bucket (description-quality, NOT trade-quality)

| confidence | count |
|---|---|
| 0.9 (family + instrument [+TF]) | **74** |
| 0.6 | 0 |
| 0.0 (UNKNOWN) | 0 |

**Delta vs v0.1:** the 10 Sweep rows moved 0.6 → 0.9 (instrument `XAUUSD` now extracted;
`timeframe` null with `TIMEFRAME_MISSING`, faithful to the sweep alert format).

## Unknown / unclassified

**0** of 74 — every capture matched a known Farouk family.

## Not observed in this sample

A+ / A+ or better (0), A+++ (0), BPR formed (0). Consistent with the daily report v0 and with H1
(dedicated A+) not yet having fired.
