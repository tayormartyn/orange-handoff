# Gate F — Farouk-STYLE Cloud Webhook Test — PLAN (NOT STARTED)

**Mode: GATE F PLAN ONLY.** Nothing configured/fired. Requires Martyn's explicit approval before
execution. This is a **Farouk-STYLE** test — a NEW harmless test alert shaped like a Farouk signal —
**NOT a real Farouk production alert**.

## Objective

Confirm the proven always-on capture lane (Gate E: TradingView → Worker → R2, 200, placeholders
resolved) correctly handles a **realistic signal-shaped payload** with Farouk-style observational
fields — still logging-only, no execution meaning.

## Design

- **NEW alert only.** Name: **`LIVE002_FAROUK_STYLE_CLOUD_WEBHOOK_TEST_GATE_F`**.
- **Endpoint:** the SAME proven workers.dev URL + secret path as Gate E (`LOCAL_ONLY_GATE_F_WEBHOOK_URL.txt`,
  copy-proof; identical to the Gate E URL). No new deploy, no Worker change.
- **Message:** `LOCAL_ONLY_GATE_F_TRADINGVIEW_MESSAGE.json` (below).
- **Harmless / observational only:** `test: true`, `lane: LOGGING_ONLY`, `execution_allowed: false`,
  `broker_execution_allowed: false`, `qst_allowed: false`. **No** lot size, account ID, order intent,
  permit, lease, or broker route. The Farouk-style fields (`strategy_family`, `candidate_event`,
  `direction_hint`, etc.) are **strings for observation** — the Worker stores them in `raw_payload`;
  they carry no execution effect.

## The JSON message (paste verbatim into the alert's Message box)

```json
{
  "schema_version": "tv-webhook-0.1",
  "source": "TradingView",
  "lane": "LOGGING_ONLY",
  "test": true,
  "test_id": "GATE_F_FAROUK_STYLE_TEST_001",
  "alert_name": "LIVE002_FAROUK_STYLE_CLOUD_WEBHOOK_TEST_GATE_F",
  "symbol": "{{ticker}}",
  "exchange": "{{exchange}}",
  "timeframe": "{{interval}}",
  "event_text": "Gate F Farouk-STYLE cloud webhook test only - harmless, observational, no signal, no instruction",
  "trigger_price": "{{close}}",
  "trigger_time": "{{time}}",
  "server_time_hint": "{{timenow}}",
  "strategy_family": "FAROUK_STYLE_TEST",
  "candidate_event": "A_PLUS_SHORT_TEST",
  "instrument": "XAUUSD",
  "session_context": "TEST_ONLY",
  "direction_hint": "SHORT_TEST_ONLY",
  "execution_allowed": false,
  "broker_execution_allowed": false,
  "qst_allowed": false
}
```

Placeholders used (proven in Gate E): `{{ticker}}` `{{exchange}}` `{{interval}}` `{{close}}` `{{time}}`
`{{timenow}}` — all resolve; times are UTC.

## Manual steps for Martyn (WHEN APPROVED — do not do yet)

1. TradingView on XAUUSD · Pepperstone → **Create alert** (a **NEW** alert; do **not** open/edit any
   Farouk production alert).
2. Name it **`LIVE002_FAROUK_STYLE_CLOUD_WEBHOOK_TEST_GATE_F`**.
3. Condition: simple XAUUSD **price crossing** near current price; **Only Once**.
4. Notifications: **Notify in app ON**; tick **Webhook URL** and paste the single bare line from
   `cloud_worker_dark/LOCAL_ONLY_GATE_F_WEBHOOK_URL.txt` (copy the line between the markers only).
   - ✅ starts with `https://farouk-tv-webhook-logger-v1.taylormartyn70.workers.dev/tv/`
   - ❌ not the old `deleted-precise-maps-reading.trycloudflare.com`.
5. **Message box:** paste the JSON from `cloud_worker_dark/LOCAL_ONLY_GATE_F_TRADINGVIEW_MESSAGE.json`.
6. Save + re-arm; fire once; tell Claude "fired".
7. **Do not touch any Farouk production alert.**

## Verification (when fired, in the execution gate)

Same method as Gate E: temporarily add the secret-gated read-only list branch (or `wrangler tail`),
find the new object, verify `ACCEPTED`/`PARSED`, raw preserved, placeholders resolved, Farouk-style
fields stored verbatim, `path: /tv/<redacted>` (no secret), then **revert to pure logging-only**.

## Classification note

The Worker classifies `event_type` from `event_type`/`event_text` only (not `candidate_event`), so this
payload parses as PARSED with `event_type=null` — the `A_PLUS_SHORT_TEST` string is retained in
`raw_payload` for observation but is **not** interpreted as a real A+ signal. No execution meaning.

## Hard guarantees

- NOT a real Farouk production alert; no Farouk alert edited; no webhook attached to any Farouk alert.
- No broker/cTrader/QST; no permit/lease/order; no execution-gate change; no risk change; no shadow
  engine; Telegram listener untouched; secret never exposed. Logging-only. `NOT_INTEGRATION_READY`
  unchanged.

## Status

**PLANNED ONLY — NOT STARTED. Awaiting Martyn's explicit approval before firing.**
