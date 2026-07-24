# Always-On Receiver — Test Payloads

**Mode: PREPARATION / DESIGN ONLY.** Reference payloads for Stage B local unit tests (and later Stage
D manual POSTs). All harmless, no secrets, no broker instruction. The secret lives in the URL path,
never in these bodies.

## P1 — Valid JSON (Stage-2-proven shape) → expect ACCEPTED / PARSED
```json
{
  "schema_version": "tv-webhook-0.1",
  "source": "TradingView",
  "lane": "LOGGING_ONLY",
  "test": true,
  "alert_name": "LIVE001_WEBHOOK_TEST_ALWAYSON",
  "symbol": "XAUUSD",
  "exchange": "PEPPERSTONE",
  "timeframe": "3",
  "event_text": "always-on receiver test - harmless, no signal, no instruction",
  "trigger_price": "4142.14",
  "trigger_time": "2026-07-07T16:15:00Z",
  "server_time_hint": "2026-07-07T16:15:38Z"
}
```

## P2 — Placeholder form (as TradingView would send pre-resolution reference) → expect PARSED once resolved; UNRESOLVED_PLACEHOLDER if literal `{{...}}` survives
```json
{
  "schema_version": "tv-webhook-0.1",
  "source": "TradingView",
  "alert_name": "LIVE001_WEBHOOK_TEST_ALWAYSON",
  "symbol": "{{ticker}}",
  "exchange": "{{exchange}}",
  "timeframe": "{{interval}}",
  "event_text": "always-on placeholder test",
  "trigger_price": "{{close}}",
  "trigger_time": "{{time}}",
  "server_time_hint": "{{timenow}}"
}
```

## P3 — Default-text body (the Stage-2 firing-1 case) → expect ACCEPTED / INVALID_JSON, raw stored
```
XAUUSD Crossing 4,134.00
```

## P4 — Duplicate of P1 → expect DUPLICATE (stored, flagged; distinct count unchanged)
(identical bytes to P1)

## P5 — Oversize body (> 64 KB) → expect 413, no record
(a > 64 KB blob)

## P6 — Wrong path (any body) → expect 404, no record

## P7 — GET to correct path → expect 405, no record

## P8 — Disabled mode (`TV_WEBHOOK_ENABLED=0`) + valid P1 → expect 503, logged, no accept

## Expected classification summary

| Payload | validation_status | parse_status |
|---|---|---|
| P1 valid JSON | ACCEPTED | PARSED |
| P2 placeholders | ACCEPTED | PARSED (resolved) / UNRESOLVED_PLACEHOLDER (literal) |
| P3 default text | ACCEPTED | INVALID_JSON |
| P4 duplicate | DUPLICATE | PARSED |
| P5 oversize | REJECTED_SIZE | (none) |
| P6 wrong path | REJECTED_PATH | (none) |
| P7 GET | REJECTED_METHOD | (none) |
| P8 disabled | REJECTED_DISABLED | (none) |

## Safety note

None of these payloads contains an API key, secret, account id, or trade instruction. They exercise
transport/auth/parse/dedupe only — the receiver has no execution path to exercise.
