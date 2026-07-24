# ALERT INTEGRATION BOUNDARY — v0.1

## FP-INDICATOR-005 alert surface (evidence)
Exposes alertconditions: Bullish/Bearish BPR formed, Bullish/Bearish Engulfing, Sweep low/high, Asia Trap
Bearish/Bullish, A+++ setup, A+ or better, CHoCH up/down, and **Any alert() function call**.

## Recorded facts
- Standard alertconditions **can be configured as "Once per bar close"** (user-selectable; also Once only / per
  bar / per minute).
- Standard messages are **plain, editable text** (default = the condition name).
- Default messages contain **no structured JSON or placeholders**.
- **Any alert() function call** uses **script-controlled timing and payload** (no UI Trigger row).
- Actual runtime payload, repaint, duplicate behaviour and live timing **remain UNKNOWN**.
- Webhook capability exists **in principle** (TradingView) but was not configured (Notifications = App/Toasts).
- **Current verdict: NOT integration-ready.**

## Hard boundary
- **No TradingView alert is treated as an authorised trade signal.** In the state machine, an alert is an
  `ALERT_RECEIVED` → untrusted observation, subject to validation, dedup, stale-drop and a repaint guard.
- No alert/webhook is created or activated; nothing is wired to QST; no order path exists.
- Integration preconditions (all currently unmet): known runtime payload schema, proven bar-close-only (non-
  repainting) timing, duplicate handling, explicit authorisation. Until then → BLOCKED_BY_LIVE_VALIDATION.
