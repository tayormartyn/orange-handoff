# ALERT CREATION CHECKLIST (perform LATER — not now)

**Do NOT create any alert while preparing this protocol.** This checklist governs the eventual live window.
No webhook. App/Toast notifications only. No broker action.

## Pre-flight
- [ ] Chart = XAUUSD, Pepperstone feed, 3m confirmed (Steps 1–2 done, screenshots taken).
- [ ] Indicator config snapshot captured (Step 3).
- [ ] Chart timezone recorded verbatim.

## Per named condition (A+++ setup, A+ or better, Sweep low, Sweep high, CHoCH up, CHoCH down)
- [ ] Condition = **Farouk's Playbook — Smart Money Suite → <the named condition>**.
- [ ] Trigger / frequency = **Once per bar close**.
- [ ] Message = **leave the default (plain text)** — do NOT add JSON/placeholders (we are capturing the native payload).
- [ ] Notifications = **App + Toast ONLY**. **Webhook URL = EMPTY / unchecked.**
- [ ] Expiration = short (e.g. end of the test window).
- [ ] Screenshot the dialog **before** pressing Create → `04_alert_setup_<condition>`.
- [ ] Press Create. Log the alert name + creation time in the run log.

## For "Any alert() function call"
- [ ] Condition = **Any alert() function call**.
- [ ] **Do NOT try to set a frequency** — timing & payload are **script-controlled** (there is no Trigger row).
- [ ] Message = leave as-is (the runtime payload comes from the script's alert()).
- [ ] Notifications = App + Toast only. Webhook empty.
- [ ] Screenshot before Create → `04_alert_setup_any_alert`.

## Hard stops
- [ ] NO webhook URL is ever entered.
- [ ] NO order/broker/QST action of any kind.
- [ ] If TradingView requires a paid tier for "Once per bar close" server-side alerts, STOP and record the
      limitation rather than downgrading to intrabar without noting it.
- [ ] All created alerts are listed for deletion in CLEANUP_CHECKLIST.
