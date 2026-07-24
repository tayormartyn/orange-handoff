# LIVE VALIDATION PLAN — v0.1 (for FP-LIVE-OBSERVATION-001)

Forward-only, observation-only capture to resolve what static evidence cannot. **No orders, no webhooks
activated, no QST.** Ranked P1 > P2 > P3.

## P1 — alert trust + timing (highest value; gates any integration)
1. **Actual A+++ runtime payload** — capture the real message an `A+++ setup` alert delivers (vs the plain
   default). 
2. **Actual Any alert() runtime payload** — capture what the script's `alert()` emits (schema? JSON?).
3. **Bar-close vs intrabar timing** — does each alert fire only at bar close or intrabar? (per condition).
4. **Repaint / post-alert mutation** — after firing, does the marker/zone move or disappear on the closed bar
   or on reload? (the core non-repainting question).
5. **Duplicate alerts** — does the same event fire more than once (per bar / on refresh)?
6. **Confluence-grade behaviour** — do A+++ / A+ grades change after the bar? what precedes each grade?

## P2 — thresholds + terminology
7. **Numeric mitigation** — how deep / how many touches counts as mitigated (and when a zone is "spent").
8. **FVG fill + IFVG conversion** — partial vs full fill validity; when an FVG becomes an IFVG.
9. **Setup expiry** — how long an OB/FVG/POI stays valid.
10. **Timeframe-conflict handling** — behaviour when HTF bias and LTF trigger disagree.
11. **nBOS definition** — capture a case Farouk labels "nBOS" (nested BOS?).
12. **POC "T" + value-window** — the profile period behind VA=68% and the "T" variant.

## P3 — expectancy (after sufficient data)
13. **Prospective shadow retention** — log qualified candidates forward without acting; measure edge retention.
14. **False-positive rate** — of A+++/A+ alerts and of each setup family.
15. **Campaign expectancy** — only after enough samples; never from the current n=4 campaigns.

## Method (all P-levels)
Forward capture with wall-clock (UTC) + bar-open/close stamps; snapshot indicator objects intrabar and at
close; re-open historical bars later to diff for repaint. Store under `prospective/…`. Observation only.
