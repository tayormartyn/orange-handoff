# Gate G — Classification Summary v0.1

Replay of `raw_farouk_text_classifier_v0_1` over **74** Gate G captures (window 2026-07-08T22:15:04.258Z → 2026-07-09T09:51:02.760Z). Descriptive counts only — no execution meaning.

## By event_family

| event_family | count |
|---|---|
| ENGULFING | 27 |
| A_SIGNAL | 24 |
| LIQUIDITY_SWEEP | 10 |
| BPR | 8 |
| STRUCTURE | 5 |

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

## By direction (bias descriptor only — NOT order side)

| direction | count |
|---|---|
| SHORT_HINT | 23 |
| LONG_HINT | 19 |
| SHORT | 14 |
| LONG | 10 |
| NONE | 8 |

## By confidence bucket (description-quality, NOT trade-quality)

| confidence | count |
|---|---|
| 0.9  family + instrument + timeframe | 64 |
| 0.6  family only (no instrument/TF) | 10 |

## Unknown / unclassified

**0** of 74 — every capture matched a known Farouk family.

## Note on the 0.6 bucket

The 10 rows at 0.6 are the **Sweep** captures, whose raw text is `Farouks Playbook: Sweep low (bullish) on XAUUSD` — it carries **no trailing timeframe number**, so instrument+timeframe extraction returns null and the classifier emits a warning rather than guessing. Instrument (`XAUUSD`) is present in the text but the v0.1 extractor requires the `on <SYM> <TF>` pair. See replay report for the v0.2 recommendation (instrument-only extraction).
