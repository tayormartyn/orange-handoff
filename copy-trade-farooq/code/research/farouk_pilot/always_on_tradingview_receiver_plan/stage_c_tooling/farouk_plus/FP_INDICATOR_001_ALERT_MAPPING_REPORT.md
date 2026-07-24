# FP-INDICATOR Alert Mapping Report (Recovery Item 2)

**Mode: INDICATOR ALERTS → LANE-6 MAPPING ONLY — SINGLE-SESSION.** Observation-only. Date 2026-07-11.
No TradingView alert was touched; this is a mapping of already-captured evidence. Machine-readable:
`fp_indicator_001_alert_mapping.json`. Gates `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged.

## 0. Provenance correction (important)

FP-INDICATOR-001 (Dec-2025 session) documents the **[kyle] v1/v2 + POC era** — settings, ORB windows, POC
plots, SFP markers — and explicitly notes the CHoCH/OB panel was **not** present there. The current alert
surface belongs to **"Farouk's Playbook — Smart Money Suite" (FP-INDICATOR-005 per R-INDICATOR-PANEL)**,
evidenced by: the Jul-5 alert-conditions screenshot (`farouk_indicator_alert_conditions.png`), the numeric
panel (CHoCH/Asia-break/OB-retest/Current-OB/Fresh-OB with prices), and the live Gate-G/H alert-lane
captures (real CHoCH/Sweep/A payloads, A+ capture). The mapping below uses the CURRENT suite; the
[kyle]-era records contribute settings context (ORB windows, POC) and the repaint-UNKNOWN caveat that
motivated F5.

## 1. Alert-condition mapping (13 visible named conditions + Any alert())

| alertcondition (visible Jul-5) | direction hint | Lane-6 relevance | pre-mark usefulness |
|---|---|---|---|
| **Sweep low / Sweep high** | LONG / SHORT bias onset | liquidity-sweep context (the setup trigger frame) | **HIGH** — sweeps define the manipulated extreme a STRONG level needs (R-STRONGWEAK); anchor for `stop_outside_zone` (beyond the swept extreme) |
| **CHoCH up / CHoCH down** | LONG / SHORT | structure shift; the panel publishes the exact CHoCH price | **HIGH** — with the panel value = a numeric pre-mark anchor + confluence rank #1 (BOS/CHoCH class) |
| **Bullish/Bearish BPR formed** | LONG / SHORT | OB/FVG/BPR zone context | **HIGH** — a formed BPR is a constructible zone (his EDU-002 A+ setup basis) |
| **Bullish/Bearish Engulfing** | LONG / SHORT | candle confirmation (EDU-022) | **MEDIUM-LOW** — confirmation input, not a level; noisy alone |
| **Asia Trap Bearish / Bullish** | SHORT / LONG | Asia H/L liquidity frame (his core "lose Asia low" rule) | **HIGH** — session-liquidity context; pairs with Asia-break panel field |
| **A+++ setup / A+ or better** | via payload | graded confluence stack (ratified) | **MEDIUM** — grade formula invisible (R-AGRADES watchlist): record + correlate, weight 0 |
| **Any alert() function call** | payload-dependent | catch-all; script-controlled timing | **REQUIRED for payload-borne events** (see §2) but timing is script-side → repaint guard mandatory |

**Panel numeric fields** (bar-close snapshot when captured at close): `CHoCH <price>` · `Asia break
LOW/HIGH/X` · `OB retest <price/X>` · `Current OB <price>` · `Fresh OB <price>` — **the primary numeric
level source for pre-marks** (this is how `indicator_price_level_extraction` becomes concrete).

## 2. A LONG / A SHORT detectability

Directional "A" entries were observed in the Gate-G/H alert-lane captures (CHoCH→Sweep→A sequences;
GATE_H1 A+ capture) — i.e. **they arrive as alert payload text, via `Any alert()` or below-the-fold named
conditions; the visible dropdown shows only the graded forms (A+++ / A+ or better)**. Conclusion: A
LONG/SHORT is detectable **through payloads, not (confirmed) as a dedicated named condition** — payload
parsing stays in the builder spec, and the first forward captures will settle whether dedicated A-LONG/
A-SHORT conditions exist below the fold. Marked UNCONFIRMED_BELOW_FOLD.

## 3. Insufficient / noisy for pre-marking

Engulfing alerts alone (no level, high frequency) · A-grades without the formula (record-only) · [kyle]-era
POC "T-variants" (meaning UNKNOWN — never answered; do not use) · SFP markers (source attribution
unconfirmed) · anything intra-bar/repaintable (excluded by F5, below).

## 4. Repaint guard application (F5 — binding)

Repaint/intrabar behaviour was **never demonstrated** for any of these objects (FP-INDICATOR-001's explicit
caveat). Therefore: a pre-mark may cite an indicator value ONLY when it is **bar-close-confirmed** — an
alert-lane payload timestamped at/after bar close, or a panel value read from a closed bar. Any uncertain
alert → `PRE_MARK_INSUFFICIENT_CONTEXT`. Uncertainty costs evidence, never adds risk.

## 5. Safety confirmation

Mapping of captured evidence only; no alerts touched/created/modified; no execution surface; no
permits/leases/orders; gates unchanged; listener PID 87988 running; no Worker/R2/secret action.
`NOT_INTEGRATION_READY` unchanged.
