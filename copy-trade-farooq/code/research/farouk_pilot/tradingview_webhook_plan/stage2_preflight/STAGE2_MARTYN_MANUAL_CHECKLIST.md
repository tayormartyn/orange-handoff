# Stage 2 — Martyn's Manual Check (TradingView)

**PREFLIGHT ONLY — look, don't change.** This is a *read-only* look at the TradingView alert dialog to
confirm the Webhook URL field exists. **Do not paste any URL. Do not save any webhook. Do not create
or edit any Farouk alert.**

## What I need you to check

1. Open TradingView on **XAUUSD · Pepperstone · 3m** (your usual chart).
2. Open the **alert dialog**:
   - Either click the **alarm-clock (Alerts) icon → "Create alert"**, **or** open an existing alert's
     **"Edit"** screen (a Farouk one is fine to *look at* — **do not change or save it**).
3. Go to the **"Notifications"** tab of the alert dialog.
4. Look for a **"Webhook URL"** checkbox/field.

## Report back

- [ ] **Is there a "Webhook URL" field?** YES / NO.
- [ ] If YES: is it enabled/available on your plan (not greyed out / not "upgrade" prompted)?
- [ ] Note the other notification options present (App, Popup, Email, etc.) — confirm **App
  notification** can stay ON alongside a webhook.
- [ ] Optional: **screenshot** the Notifications tab (blank webhook field, nothing typed) and drop it
  into
  `research/farouk_pilot/live_observations/FP-LIVE-OBSERVATION-001/FP-LIVE-OBSERVATION-001/raw/`
  so it can be imported like other evidence.

## Do NOT do (this step)

- ❌ Do **not** paste any webhook URL.
- ❌ Do **not** tick/enable the webhook checkbox and save.
- ❌ Do **not** create a new alert yet.
- ❌ Do **not** edit or save any existing Farouk alert.
- ❌ Do **not** change any notification setting and save it.

If the dialog only lets you *see* the field without saving, that's all we need for now. Just closing
the dialog without saving changes nothing.

## Why this matters

Stage 2 (sending one harmless test alert to the logging-only receiver) can only work if TradingView
exposes a Webhook URL field on your plan. Confirming it exists is the gate that unlocks a safe Stage 2
— it does **not** itself send anything or change anything.

## After you report

- If **YES** (field exists, plan allows it): I can prepare the exact Stage-2 execution steps for your
  explicit go-ahead (one test alert, app notification on, fresh secret, tunnel up only for the test,
  then torn down).
- If **NO**: Stage 2 as designed can't proceed; we'd fall back to the always-on cloud/serverless
  receiver idea or stay on the CSV/phone evidence lanes. Nothing is lost.
