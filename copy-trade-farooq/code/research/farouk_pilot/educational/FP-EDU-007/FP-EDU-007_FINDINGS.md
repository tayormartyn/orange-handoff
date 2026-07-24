# FP-EDU-007 — FINDINGS (interim)
Scalping Strategy on the 1-, 5-, and 15-Minute Charts — Farouk & Vishal. NOT_A_TRADE; cross-asset; excluded
from Gold statistics. No detector; no methodology/state-machine spec edit.

## Headline
This is a **different, EMA-based scalping method** (Vishal's **Craters Reality / TR-Main**) — **NOT** the
[kyle] v1/v2 / Smart Zones SMC panel of FP-INDICATOR-001–004. Farouk hosts and runs a **parallel** VWAP/own
system on **gold**; Vishal demos on **SUIUSDT.P (Binance)**.

## Timeframe roles (as TAUGHT — not the assumed standard)
- **1H = direction / daily bias** (price vs the **50 EMA**: below = bearish). *(bias is on 1H, NOT 15m.)*
- **15m = intermediate confluence** (bridge to 1H).
- **5m = context / post-entry monitoring** (watched together with 1m).
- **1m = ENTRY / execution** ("I usually take trades on the one minute").
- **3m and 4H = NOT used** here (contrast: Campaign 004's [kyle] method used 3m OB + H4 BOS).
- Sequence: **1H → 15m → 5m → 1m**, then monitor 1m+5m together. A top-down read is described; **strictness not stated**.

## Confirmation / entries
Signals are **EMA position/cross + stochastic**, NOT SMC candle-close confirmations. Candle-close requirement
UNRESOLVED; a hint of **live/intrabar** 1m entries (WEAK). **No minimum confluence count** stated.

## Stop / target
Stop = structure-based; **breakeven after 1%** ("SL to entry, then get more"). Target = **200 EMA + 50 EMA
aligning**, "take 90% out". Money-management: **1–3%/day**, then stop; **compounding** via the shared
"Building Capital" spreadsheet (Crypto + Gold tabs; ~500→11,795 over 300 days at ~1%/day).

## Farouk vs Vishal (kept separate)
- **Agree:** multi-TF low-TF scalping (1/5/15), 1–3%/day + quick scalps, breakeven after ~1%, compounding, "works on gold".
- **Differ:** Vishal = **EMAs** (Craters Reality/TR-Main) on **crypto (SUI)**; Farouk = **VWAP + his SMC/[kyle] system** on **gold**.

## Campaign cross-reference
Campaign 004's **H4 BOS + H1 nBOS + 3m OB + 5m OB** is the **[kyle] SMC** stack — **not** corroborated here
(different method). CHoCH-absence is **not addressed** (this method has no CHoCH). What DOES transfer as a
general principle: **HTF direction/bias + LTF execution** layering (1H bias + 1m entry ≈ C004's H1 preferred
zone + LTF entry). **F_CONFLUENCE_UNKNOWN is NOT narrowed** — no confluence count, and a different object set.

## State-machine impact (see FP-EDU-007-vs-STATE-MACHINE-v0.1.json)
NARROWED: BIAS_CHANGED (concrete 1H/50-EMA bias, method-specific). SUPPORTED: ARMED, VETOED (general
principles). UNCHANGED: STRUCTURE_FOUND, ZONE_REGISTERED, WAITING_FOR_TRIGGER, INVALIDATED. **STILL_BLOCKED:
QUALIFIED_CANDIDATE** (F_CONFLUENCE_UNKNOWN). Suggests a **separate EMA-scalp family** may be warranted.

## XAUUSD applicability
**SUPPORTED (verbally + a Gold spreadsheet tab)** but **demoed on crypto** — so gold applicability is stated,
not directly demonstrated in this video.
