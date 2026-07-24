# FP-INDICATOR-005 — ALERT PAYLOAD FINDINGS

Targeted alert-interface completion pass. 10 alert screenshots (added to the package folder **after** the video
pass) were inventoried, hashed, and analysed (8 individually transcribed; 2 small crops inventoried as
consistent with the set). No alert or webhook was created or activated. Video analysis was NOT repeated.

## Farouk-specific alert conditions (13)
From the "Condition → Farouk's Playbook — Smart Money Suite" dropdown, in order:
1. **Any alert() function call** (script-controlled)
2. **Bullish BPR formed** · 3. **Bearish BPR formed**
4. **Bullish Engulfing** · 5. **Bearish Engulfing**
6. **Sweep low** · 7. **Sweep high**
8. **Asia Trap Bearish** · 9. **Asia Trap Bullish**
10. **A+++ setup** · 11. **A+ or better**
12. **CHoCH up** · 13. **CHoCH down**

## Generic TradingView conditions (separate)
Begin AFTER "CHoCH down" (visible separator): **Crossing, Crossing Up, Crossing Down**, then **SHOW MORE**
(standard: Greater Than, Less Than, Entering/Exiting Channel, Moving Up/Down %, …). These are TradingView's
built-in plot-value conditions, NOT Farouk conditions.

## Visible message payloads
- **Named alertcondition() conditions:** the Message field is **pre-filled with the condition name as plain
  text** (e.g., `A+++ setup`). Editable (`>` expander). **No `{{placeholders}}` or JSON** visible.
- **Any alert() function call:** Message shows the **indicator name** ("Farouk's Playbook — Smart Money Suite
  (Smart Money Suite)"); the **actual runtime message is whatever the script's `alert()` call emits** (Pine
  source not shown → content UNKNOWN).

## Standard-condition frequency controls
For named alertcondition() conditions, the Trigger dropdown offers the **standard TradingView set**:
- **Once only** — triggers once when the condition is met (the A+++ example was set to this)
- **Once per bar** — once per bar when met
- **Once per bar close** — **triggers at bar close** (closed-bar firing available)
- **Once per minute** — while the condition remains met

"Once per bar close" IS available (relevant to closed-bar vs intrabar alerting) but is **user-selected, not
enforced** by the indicator.

## Script-controlled Any alert() behaviour
When **"Any alert() function call"** is selected, TradingView shows **no Trigger/frequency row** → the firing
frequency is controlled **in-script** (the `alert()` call's `freq` argument, e.g. `alert.freq_once_per_bar_close`).
This means the indicator issues its own alert() events; their timing and message are set by the Pine code, which
is **not visible** here (UNKNOWN whether intrabar or bar-close, and whether the payload is structured).

## Webhook suitability
- **Webhook-CAPABLE** via TradingView's standard alert mechanism (webhook URL is a Notifications option on
  paid plans; the shown Notifications were **App, Toasts** — webhook not selected in these captures).
- **Payload structure = plain text by default** (condition name). For a webhook to carry structured data
  (JSON), either the user edits the Message field (TradingView supports `{{...}}` placeholders / custom JSON) or
  the script's `alert()` calls format JSON — **neither is demonstrated**.
- So: routing these alerts to a webhook is technically possible, but the **default payloads are just condition
  names**; structured/actionable payloads are UNVERIFIED.

## Remaining unknowns
- Exact runtime message content of the script's `alert()` calls (Pine source not shown).
- Whether any condition's Message field was customised with `{{placeholders}}`/JSON (defaults are plain names).
- The full generic-condition list (SHOW MORE not expanded).
- Alert **timing/repaint** of the underlying markers (bar-close option exists, but marker repaint is still
  UNKNOWN — needs live capture / FP-LIVE-OBSERVATION-001).
- Webhook URL configuration (not shown).
- 2 small crops (163256, 163621) not individually transcribed.
