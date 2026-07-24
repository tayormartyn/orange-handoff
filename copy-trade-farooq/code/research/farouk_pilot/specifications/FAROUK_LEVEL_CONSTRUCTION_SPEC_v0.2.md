# FAROUK LEVEL-CONSTRUCTION SPECIFICATION — v0.2

**Status: DRAFT / EVIDENCE-GRADED. Descriptive only — not an algorithm, not executable.** (v0.1 preserved.)
v0.2 adds the **official documents** (FP-EDU-002 Playbook, FP-EDU-003 Whale Room Guide, FP-EDU-004 Strong
vs Weak OB) which give **explicit level definitions**, kept distinct from what is **observed** in the
campaigns. Tags: **[DOC]** documented definition · **[OBS]** seen on a campaign chart · **[OPEN]** unknown.
None of these constructions has been **reproduced from price** (no market data). No detector code.

---

## A. Charting environment
- **[OBS]** TradingView, usually **Bar-Replay**. Feeds seen: **Pepperstone, Vantage, FXCM** (and Bybit for
  crypto). Instrument mainly **XAUUSD**. Platform TZ observed **UTC+2** (FP-EDU-001). A **custom indicator
  panel** reports per-TF `CHoCH · Asia break · OB retest · Current OB · Fresh OB`.

## B. Session levels
- **[DOC]** Mark the **Asia session High/Low** (the Asian-hours range); liquidity rests above the high /
  below the low. **[DOC]** Other pools: PDH/PDL, equal highs/lows, swing highs/lows, round numbers
  (Playbook p6). **[OBS]** "Asia High"/"Asia Low" lines on every campaign chart; panel `Asia break HIGH/LOW`.
- **[DOC]** **Liquidity sweep** = a **wick breaks the level then the candle closes back inside** (grabs
  stops, then reverses) — Playbook p6, FP-EDU-004.
- **[OPEN]** Exact **session windows / timezone** used to compute the Asia range and the `Asia break` flag.
  Playbook cites "London open 08:00 UTC / NY 13:30 UTC" as best times — [DOC], not yet reconciled with the
  UTC+2 chart or the unknown Discord TZ.

## C. Order Blocks (OB)
- **[DOC]** **OB = the LAST opposing candle before a strong impulsive move** (last bearish before a bullish
  move = bullish OB) — Playbook p6. Retest of the OB = entry; SL beyond the OB body; target the prior swing.
- **[DOC]** **Quality (FP-EDU-004):** *strong* OB = **sweep → displacement → leaves an FVG**, fresh /
  first-tap, aligned with the **Trend EMA** (above for longs / below for shorts), **BPR overlap = bonus**.
  *weak* OB = lazy impulse / no FVG / tapped-multiple (mitigated/spent) / against-trend or chop / isolated.
- **[OBS]** Panel `OB retest`, `Current OB`, `Fresh OB` values (e.g. C001 4123.51; C003 4009.08 / 4009.08 /
  4379.08). C003 spoken "already mitigated" matches the *spent-OB* concept.
- **[OPEN]** The indicator's actual detection / refresh / mitigation algorithm; the difference between
  `Current OB` and `Fresh OB`; the Trend-EMA definition.

## D. Fair Value Gaps (FVG) & BPR
- **[DOC]** **Bullish FVG** = candle1 high < candle3 low (big bullish candle2 between); **Bearish FVG** =
  candle1 low > candle3 high (big bearish candle2). **Once filled → invalid** (Playbook p3). HTF FVGs
  outrank LTF.
- **[DOC]** **BPR** = a bullish FVG and a bearish FVG **OVERLAP** at the same price (a high-precision
  reaction zone; "A+ setup") — Playbook p5.
- **[OBS]** "Daily FVG" and FVG/BPR labels on campaign/edu charts (C003 Daily FVG as target). **[OPEN]** the
  exact gap-size/mitigation rules and BPR overlap tolerance.

## E. Market structure — CHoCH / MSS / BOS
- **[DOC]** **5m = structure**, **3m = MSS/BOS** (MSS = first higher-high after lows), **1m = trigger**
  (Playbook p10). Panel reports a `CHoCH` value (or `×`).
- **[OBS]** CHoCH/BOS/FVG/OB on-chart labels across campaigns. **[OPEN]** the swing-detection basis.

## F. Confirmation candles
- **[DOC]** Reversal candles (hammer, shooting star, doji variants, morning/evening star, tweezers) and
  **engulfing** (**body ≥2× prior**, entry next-open, SL beyond the engulfing wick) — Playbook p7-8. Not
  independently observable in the campaign screenshots.

## G. Higher-timeframe zones
- **[OBS]** HTF supply/demand bands + HTF OB/FVG (H4 OB, H4/M15/Weekly bearish FVG, Weekly CHoCH — C002
  frames) provide **location**; entries preferred **at** these. **[OPEN]** prioritisation when zones overlap.

## H. Pip / value convention
- **[DOC]/[OBS] CONFIRMED:** XAUUSD **0.10 price = 1 pip** (WR p3/p5: 4,500→4,505 = 50 pips; 4,514.90→
  4,515.00 = 1 pip). C003 result cards verify **value ≈ price_move × 100 × lot_size**; `buy 1/0.5/0.25`
  are lot sizes. **[OPEN]** the value **currency** (no symbol shown) — recorded UNKNOWN.

## I. Risk / sizing note (documented, NOT adopted)
- **[DOC]** The documents teach **1–2% per-trade** risk, a balance-scaled **lot table** (WR p11), BE at
  **+50 pips from the average**, a **shared stop** across **≤3** layered entries, and BE/partial schedules.
  **[CONTRA]** These are **document claims only**. The project's **LOCKED 1.0% campaign-wide risk cap is
  retained and is NOT replaced** by any figure in these documents.

## J. Open construction questions
- **[OPEN]** The **name/parameters** of the custom indicator (CHoCH/OB/Asia/FVG values); session
  timezone/windows; tick precision; "Fresh" vs "Current" OB and mitigation logic; the Trend-EMA definition.
  **None of these levels has been reproduced from tick/OHLC data** (no market data downloaded).
