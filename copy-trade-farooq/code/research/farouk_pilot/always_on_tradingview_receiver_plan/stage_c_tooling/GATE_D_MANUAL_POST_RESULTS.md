# Gate D — Manual Cloud POST Results

**Run:** 2026-07-07 21:23 local (Italy). **Mode: ONE MANUAL CLOUD POST TEST ONLY.**
No TradingView traffic/config, no Farouk-alert edit, no QST/broker/cTrader, no broker/QST/execution
imports, no permit/lease/order, no gate change, no shadow engine. Telegram PREVIEW listener (PID 40416)
untouched. **The full secret path was never printed, echoed, or logged.**

## Outcome: PASS — one valid POST, one R2 object, verified

## Pre-test audit

- Endpoint live (`GET /` → 405). R2 bucket `farouk-tv-webhook-evidence-v1` exists, **empty (0 objects)**
  pre-test (confirmed empty at Gate C-ENDPOINT-HYGIENE; no accepted POST had ever occurred).
- Gates `MODE=PAPER`, `LISTENER_MODE=PREVIEW`, `EXECUTION_ENABLED=False`, `CTRADER_EXECUTION_ENABLED=False`.
- No permit/lease/order; Telegram listener running.

## The POST (exactly one)

- Payload: harmless JSON (`test_id`/`alert_name` = `GATE_D_MANUAL_POST_001`, symbol XAUUSD, tf 3,
  `trigger_price:"0"`, `trigger_time:"MANUAL_TEST"`). **No trade instruction, no broker details, no
  credentials.**
- Sent to the workers.dev endpoint + **real secret path** (read internally from the gitignored local
  file; secret fingerprint `e1c56bbe1346` matched, value never shown; URL never printed in full).
- **Exactly one POST** was sent.

## Response

| Field | Value |
|---|---|
| HTTP status | **200** |
| `ok` | true |
| `validation_status` | **ACCEPTED** |
| `parse_status` | **PARSED** |
| `event_id` | `c73de580-8286-48b8-b87f-40a388d4fa5d` |

## R2 write (verified)

- One append-only object written and **retrieved via `wrangler r2 object get … --remote`** (1236 bytes).
  - Key: `events/2026/07/07/c73de580-8286-48b8-b87f-40a388d4fa5d.jsonl` (event_id-keyed; date-partitioned).
  - `event_id` in object matches the POST response; `received_at_utc` = `2026-07-07T20:14:32.764Z` (UTC);
    `validation_status` ACCEPTED; `parse_status` PARSED; `raw_payload` **byte-exact** to what was sent;
    `path` = `/tv/<redacted>` (secret **not** stored); `mode` LOGGING_ONLY.
- **Exactly one object:** bucket was empty pre-test + exactly one POST was sent → one object. (wrangler
  has no object-list command; count is by construction plus the verified object.)

> **Verification note:** `wrangler r2 object get` **defaults to a LOCAL simulation store**; the first
> read attempts returned "key does not exist" until `--remote` was added, which then retrieved the real
> object. The write itself was never in doubt (the Worker returns 200 only after `await EVIDENCE.put`).

## Safety

No TradingView config; Farouk alerts untouched; no broker/QST/execution; no permit/lease/order; gates
False; risk + 1.0% cap unchanged; shadow engine not started; Telegram listener untouched;
`NOT_INTEGRATION_READY` unchanged. See `GATE_D_SAFETY_AUDIT.md` and `GATE_D_SECRET_REDACTION_AUDIT.md`.
