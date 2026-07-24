# TradingView Alert Mirroring Plan (§5)

**DESIGN ONLY — do NOT do any of this now.** How to *later* add webhook URLs to Farouk alerts safely,
once the always-on receiver is deployed and validated. Every step here is gated behind explicit
authorisation and the validation rollout.

## Principle: duplicate first, don't edit production blindly

- **Prefer duplicating** a Farouk alert, adding the webhook to the **duplicate**, and verifying it —
  rather than editing the live production alert directly. This keeps the proven production alert
  untouched while the mirror is validated.
- If duplication isn't practical for a given alert, editing a production alert to **add** a webhook
  (leaving its condition and app/notification untouched) is the fallback — but only after the receiver
  is proven and only with explicit sign-off, one alert at a time.
- **Never** change a Farouk alert's condition, price, or app-notification settings as part of
  mirroring. Webhook is **added**, nothing else changes.

## First batch size

- **Start with ONE** real Farouk alert mirrored to the webhook (e.g. the `ANY_ALERT` composite, which
  carries the most information), after the harmless/duplicate test stages pass.
- Then expand in **small batches** (e.g. the dedicated grade/structure alerts) — not all at once —
  verifying capture + no disruption at each step.
- **Full set only at the final stage**, after batches are clean.

## Keep phone/app notification ON

- Every mirrored alert keeps **Notify in app ON**. The webhook is **additive**; the existing
  phone/CSV evidence lanes must keep working unchanged (Stage 2 confirmed both coexist).

## Alert message JSON template (proven in Stage 2)

Paste as the alert **Message** (replace any default text entirely; secret stays in the URL):

```json
{
  "schema_version": "tv-webhook-0.1",
  "source": "TradingView",
  "lane": "LOGGING_ONLY",
  "alert_name": "<hardcode the alert's name, e.g. LIVE001_ANY_ALERT_XAUUSD_3M>",
  "symbol": "{{ticker}}",
  "exchange": "{{exchange}}",
  "timeframe": "{{interval}}",
  "event_text": "<hardcode or leave as the alert's descriptive text>",
  "trigger_price": "{{close}}",
  "trigger_time": "{{time}}",
  "server_time_hint": "{{timenow}}"
}
```

## Placeholder set — PROVEN in Stage 2

| Placeholder | Stage 2 result |
|---|---|
| `{{ticker}}` | resolved → `XAUUSD` |
| `{{exchange}}` | resolved → `PEPPERSTONE` |
| `{{interval}}` | resolved → `1` **(= the chart interval the alert lives on)** |
| `{{close}}` | resolved → `4142.14` |
| `{{time}}` | resolved → `2026-07-07T16:15:00Z` (**UTC**) |
| `{{timenow}}` | resolved → `2026-07-07T16:15:38Z` (**UTC**) |

- **Note on `{{interval}}`:** the Stage 2 test read **`1`** because the test alert was on a **1-minute**
  chart. It reflects the **actual chart interval** of the alert.
- **For Farouk production alerts: confirm the intended chart interval before enabling.** The Farouk
  lane is **3m** — so a mirrored Farouk alert should live on the **3m** chart and will then emit
  `{{interval}} = 3`. Verify each alert's chart interval at mirroring time; don't assume.

## No trade instruction in the payload

- The message is **evidence metadata only** — symbol, timeframe, event text, prices, times. **No**
  buy/sell/size/SL/TP instruction, **no** account ID, **no** credentials. (See hard vetoes.)

## Order of operations (later, gated)

1. Receiver deployed + validated (Stages A–D).
2. One **harmless** test alert → cloud receiver (Stage E).
3. One **duplicate Farouk-style** test alert (not production) (Stage F).
4. **One real Farouk alert** mirrored, app notifications still ON (Stage G).
5. **Full Farouk set** mirrored in batches (Stage H).

Each step verifies capture + **no production disruption** before the next.
