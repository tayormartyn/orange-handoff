# Gate D — Payload Parse Results

**2026-07-07.** How the receiver classified the manual test payload.

## Sent payload (harmless; no instruction/credentials)

```json
{
  "schema_version": "tv-webhook-0.1",
  "source": "manual-cloud-test",
  "lane": "LOGGING_ONLY",
  "test": true,
  "test_id": "GATE_D_MANUAL_POST_001",
  "alert_name": "GATE_D_MANUAL_POST_001",
  "symbol": "XAUUSD",
  "exchange": "PEPPERSTONE",
  "timeframe": "3",
  "event_text": "Gate D manual cloud POST test only - harmless, no signal, no instruction",
  "trigger_price": "0",
  "trigger_time": "MANUAL_TEST",
  "server_time_hint": "MANUAL_TEST"
}
```

## Parse result

| Field | Value | Note |
|---|---|---|
| `parse_status` | **PARSED** | valid JSON, no unresolved `{{...}}` placeholders |
| `validation_status` | **ACCEPTED** | report-time dedupe: stored as ACCEPTED, not flagged at ingest |
| `symbol` | `XAUUSD` | from payload |
| `exchange` | `PEPPERSTONE` | from payload |
| `timeframe` | `3` | from payload |
| `trigger_price` | `0` | from payload (string, stored verbatim) |
| `trigger_time` | `MANUAL_TEST` | from payload (verbatim; not a real time) |
| `server_time_hint` | `MANUAL_TEST` | from payload |
| `event_type` | `null` | no `event_type` field; event_text matched no A+/sweep/choch/bpr/engulf keyword |
| `direction` | `null` | none in payload |
| `grade` | `null` | none in payload |
| `dedupe_key` | `a272cf4bb1fb…` | sha256 over alert_name|symbol|timeframe|event_text|event_type|direction |

## Interpretation

- The Worker correctly **parsed** valid JSON and extracted metadata (symbol/exchange/timeframe/prices/
  times) exactly as the Stage B oracle does.
- `event_type`/`direction`/`grade` are `null` because this is a deliberately neutral test payload (no
  signal semantics) — as intended.
- **raw_payload** is stored byte-exact regardless of parsing, so nothing is lost.
- This confirms end-to-end cloud parity with the Stage-2 / Stage-B proven behaviour: PATH_ONLY auth →
  PARSED → append-only R2 object.
