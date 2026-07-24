# FAROUK STATE-MACHINE CANDIDATES — v0.1

**DESCRIPTIVE ONLY. NOT FINAL. NO CODE. NOT CONNECTED TO QST.**
A candidate map of observable states distilled from FP-INDICATOR-001/002/003/004 (the [kyle] v1/v2 indicator
teaching). This is an evidence-scaffold to decide *what a future detector would need to measure* — it is not a
detector, not a strategy, and not wired to any execution/risk/QST path. Every state is provisional; several
depend on thresholds and repaint facts that are **still UNKNOWN**.

The natural narrative it encodes (design-stage only):
`session opens → range/ORB forms → range locks → liquidity approached → sweep/breakout → close confirms or
rejects → value/VWAP/POC alignment checked → SFP/candle trigger checked → candidate qualified or vetoed`.

For each candidate state: **Evidence** | **Entry condition** | **Exit condition** | **Required data** |
**Unresolved threshold** | **Deterministic now?**

---

### OUTSIDE_SESSION
- Evidence: [kyle] v1 ORB / [kyle] v2 sessions are time-gated (FP-004, FP-002 dialogs).
- Entry: wall-clock outside every configured session window. Exit: a session window opens.
- Required data: session clock windows + **canonical timezone**. Unresolved threshold: **which timezone** (v2=GMT vs v1=GMT+1). Deterministic now? **NO** — timezone unresolved.

### ORB_FORMING
- Evidence: FP-004 "first 15 minutes … full scalp".
- Entry: session open tick. Exit: 15 minutes elapsed. Required: session open time, bar clock.
- Unresolved threshold: exact per-session open times + timezone. Deterministic now? **PARTIAL** (mechanic clear; times/timezone pending).

### ORB_LOCKED
- Evidence: FP-004 range fixed after the opening window; "inside the orb, don't do anything".
- Entry: 15-min window closes → ORB high/low/mid frozen. Exit: price breaks + retests (→ BREAKOUT_*).
- Required: ORB high/low/mid. Unresolved: does the ORB **repaint/redraw** after lock? Deterministic now? **NO** — repaint unknown.

### LIQUIDITY_APPROACH
- Evidence: FP-003 liquidity pools; FP-002 session-box extremes; equal highs/lows / POC / VAH-VAL.
- Entry: price approaches a marked level (ORB edge / VAH / VAL / POC / session box / equal highs-lows).
- Exit: level swept or rejected. Required: the level set. Unresolved: proximity threshold. Deterministic now? **PARTIAL**.

### SWEEP_DETECTED
- Evidence: FP-003 "swept liquidity … fail to go higher"; SFP dot line; FP-002 "swept this high".
- Entry: wick pierces a level then price trades back inside (no close beyond). Exit: reversal confirms (→ SFP_*) or level accepts.
- Required: wick/high-low vs level; bar close. Unresolved: wick-depth / '8-bar' lookback exactness; **intrabar vs close timing**. Deterministic now? **NO** — dot-print/repaint timing unknown.

### BREAKOUT_UNCONFIRMED
- Evidence: FP-002/FP-004 break of box/ORB before a close.
- Entry: price prints beyond the box/ORB level intrabar. Exit: candle closes beyond (→ CONFIRMED) or back inside (→ FAILED).
- Required: level + live price + bar close. Unresolved: wick-vs-close rule for the ORB specifically. Deterministic now? **PARTIAL**.

### BREAKOUT_CONFIRMED
- Evidence: FP-002 "candle close below/above"; FP-004 "lost the orb = short".
- Entry: a candle CLOSES beyond the level. Exit: retest holds (→ ENTRY_ZONE_ACTIVE) or fails.
- Required: closed-bar price vs level. Unresolved: none major (close rule is stated). Deterministic now? **YES-ish** (given the level + closed bars).

### FAILED_BREAKOUT
- Evidence: FP-004 "double top … failed to go higher"; FP-002 fakeout.
- Entry: break then close back inside the range. Exit: opposite setup forms. Required: level + closes.
- Unresolved: how many bars define 'failed'. Deterministic now? **PARTIAL**.

### RETURN_TO_VALUE
- Evidence: FP-003 "retest … below VAL bearish, reclaim VAH bullish".
- Entry: price returns into the value area (VAH↔VAL) or to a POC. Exit: acceptance or rejection.
- Required: VAH/VAL/POC per period. Unresolved: **value-area % / calculation**; POC 'T' meaning. Deterministic now? **NO** — value-area calc + T unknown.

### VALUE_REJECTION
- Evidence: FP-003 "retest is short" from below VAL; rejection from a POC.
- Entry: price tags a value level and reverses (with a rejection candle). Exit: reversal continues or fails.
- Required: value levels + candle. Unresolved: rejection-candle definition. Deterministic now? **PARTIAL**.

### SFP_CANDIDATE
- Evidence: FP-003 SFP = wick through swing, no close.
- Entry: wick beyond a prior swing high/low with close back inside. Exit: retest confirms (→ SFP_CONFIRMED) or reclaim invalidates.
- Required: prior swing + wick + close. Unresolved: swing-detection basis; **repaint of the dot**. Deterministic now? **NO**.

### SFP_CONFIRMED
- Evidence: FP-003 "sweep retest long/short"; combine with volume candles.
- Entry: post-SFP retest holds (optionally + high relative-volume candle). Exit: target or invalidation.
- Required: SFP level + retest + (rel-vol). Unresolved: confirmation strictness. Deterministic now? **PARTIAL**.

### VWAP_BIAS_ALIGNED
- Evidence: FP-002 "above VWAP bullish, below bearish".
- Entry: price on the trade-direction side of the chosen VWAP(s). Exit: crosses VWAP. Required: VWAP series.
- Unresolved: which VWAP timeframe is authoritative; anchor/reset time; **repaint at session reset**. Deterministic now? **PARTIAL**.

### ENTRY_ZONE_ACTIVE
- Evidence: FP-002/004 "wait for retest" at the broken level / ORB edge.
- Entry: price re-enters the retest zone after a confirmed break. Exit: trigger fires or zone invalidated.
- Required: broken level + zone width. Unresolved: zone tolerance. Deterministic now? **PARTIAL**.

### WAITING_FOR_TRIGGER
- Evidence: FP-002/003 trigger = rejection/relative-volume/SFP at the level.
- Entry: in an active zone, no trigger yet. Exit: a trigger candle closes. Required: candle + rel-vol/SFP.
- Unresolved: exact trigger definition (candle pattern vs rel-vol vs SFP). Deterministic now? **PARTIAL**.

### QUALIFIED_CANDIDATE
- Evidence: FP-004 "combine — VWAP + POC + liquidity"; multi-factor confluence.
- Entry: break+retest + VWAP/POC/value alignment + trigger all true. Exit: hands off to evaluation / vetoed.
- Required: all component states. Unresolved: **how many factors are mandatory** (confluence count). Deterministic now? **NO** — confluence rule unquantified.

### VETOED
- Evidence: FP-004 "inside the orb, don't do anything"; FP-002 chop/sideways-VWAP "weakened".
- Entry: price inside range/ORB, or chop, or against VWAP bias. Exit: condition clears. Required: range + VWAP + regime.
- Unresolved: chop/regime classifier. Deterministic now? **PARTIAL**.

### INVALIDATED
- Evidence: FP-002/003/004 close beyond the stop side / SFP reclaim / ORB reclaim.
- Entry: price closes through the invalidation level. Exit: terminal. Required: invalidation level + close.
- Unresolved: exact stop placement (never numerically stated). Deterministic now? **PARTIAL**.

### MANAGED_TO_BREAKEVEN
- Evidence: FP-001 "+50 pips move SL to entry / staircase"; docs.
- Entry: price reaches the breakeven trigger (+50 pips / +structure). Exit: runner continues or stops at BE.
- Required: entry + live price + pip convention (0.10=1pip). Unresolved: BE trigger exactness in THIS module. Deterministic now? **PARTIAL**.

### COMPLETED
- Entry: target hit or stopped (BE/loss). Exit: terminal. Required: fills. Deterministic now? **YES** (given fills).

---

## Feasibility summary
- **Blocking unknowns before ANY deterministic build:** canonical **timezone**, the **value-area / POC calculation** (+ 'T' variant), the **confluence-count** that turns components into a QUALIFIED_CANDIDATE, and — critically — **repaint / intrabar vs closed-bar timing** for SFP, liquidity, ORB and VWAP objects (none stated in any video).
- **Closest-to-deterministic** (given levels + closed bars): BREAKOUT_CONFIRMED, INVALIDATED, COMPLETED.
- **Not deterministic yet:** OUTSIDE_SESSION, ORB_LOCKED, SWEEP_DETECTED, RETURN_TO_VALUE, SFP_CANDIDATE, QUALIFIED_CANDIDATE — all gated on the unknowns above.

**This document is provisional and is NOT connected to QST, risk, broker or execution logic. No detector code exists.**
