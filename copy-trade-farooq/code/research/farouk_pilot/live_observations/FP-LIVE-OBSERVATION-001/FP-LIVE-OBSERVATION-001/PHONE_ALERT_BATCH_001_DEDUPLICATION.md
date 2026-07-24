# PHONE_ALERT_BATCH_001 — Deduplication

Source: `TradingView_Alerts_Log_2026-07-06.csv` (111 raw rows). Read-only processing.

## Method

Each CSV row = one alert **firing**. TradingView fires multiple alerts on the same 3-minute bar
close: the dedicated grade/structure alert (e.g. `APLUS`, `SWEEP_HIGH`) **and** the composite
`ANY_ALERT` alert carrying the same semantic message. To avoid double-counting the same underlying
market event, rows were grouped by:

`(timestamp_utc, semantic_event)`

where `semantic_event` is parsed from the alert Name (dedicated) or the Description (composite):
symbol (XAUUSD), feed (Pepperstone) and timeframe (3m) are constant across all rows, so they do not
further split groups.

Deduplication is **structural** (collapsing dedicated⇄composite mirrors of one firing). It does not
merge semantically-related-but-distinct alerts that happen to share a timestamp (e.g. an "A+ or
better" grade trigger and its directional "A+ (LONG)" companion are kept as two semantic rows,
because they are different messages — see note below).

## Result

- Raw rows: **111**
- Distinct `(timestamp, semantic_event)` groups: **90**
- Collapsed (dedicated⇄composite duplicates removed): **21**

## Distinct-event counts

| Semantic event | Distinct events |
|---|---|
| Bullish Engulfing | 13 |
| Bearish Engulfing | 13 |
| BPR tapped | 13 |
| A (SHORT) | 12 |
| Sweep high | 12 |
| A (LONG) | 9 |
| Sweep low | 7 |
| A+ or better (grade trigger) | 4 |
| A+ (LONG) | 2 |
| A+ (SHORT) | 2 |
| CHoCH up | 2 |
| CHoCH down | 1 |
| A+++ | 0 |
| BPR formed | 0 |
| Asia Trap | 0 |

## Dedicated ⇄ composite cross-check

| Dedicated alert | Dedicated firings | Matching composite message | Composite firings | Note |
|---|---|---|---|---|
| SWEEP_HIGH | 12 | "Sweep high (bearish)" | 12 | 1:1 — 12 sweep-high events |
| SWEEP_LOW | 7 | "Sweep low (bullish)" | 6 | **mismatch: 7 vs 6** (see Limitations) |
| CHOCH_UP | 2 | "CHoCH UP" | 2 | 1:1 |
| CHOCH_DOWN | 1 | "CHoCH DOWN" | 1 | 1:1 |
| APLUS | 4 | "A+ (LONG)"×2 + "A+ (SHORT)"×2 | 4 | 4 A+ setups; direction from composite |

## A+ grouping note

The 4 `APLUS` "A+ or better" grade triggers pair with the 4 directional composite A+ messages at the
same (or ±1 s) timestamp, giving **4 distinct A+ setups**:

| UTC timestamp | Grade trigger | Direction | Note |
|---|---|---|---|
| 2026-07-06T07:24:00Z | A+ or better | SHORT | previously seen (checkpoint window) |
| 2026-07-06T07:27:00Z | A+ or better | SHORT | previously seen |
| 2026-07-06T16:30:00Z | A+ or better | LONG | new (offline window); composite at 16:30:01Z |
| 2026-07-06T18:33:01Z | A+ or better | LONG | new (offline window) |

No `A+++` firing exists in the log at any timestamp.
