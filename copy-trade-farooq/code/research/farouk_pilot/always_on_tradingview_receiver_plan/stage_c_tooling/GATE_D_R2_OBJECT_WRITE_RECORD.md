# Gate D — R2 Object Write Record

**2026-07-07.** One append-only object, verified via `wrangler r2 object get … --remote`.

| Field | Value |
|---|---|
| Bucket | `farouk-tv-webhook-evidence-v1` |
| Object key | `events/2026/07/07/c73de580-8286-48b8-b87f-40a388d4fa5d.jsonl` |
| Object size | 1236 bytes |
| Pre-test object count | 0 (empty) |
| Post-test object count | 1 (this object; by construction — one POST, one put) |

## Stored record (fields; secret redacted)

| Field | Value |
|---|---|
| `event_id` | `c73de580-8286-48b8-b87f-40a388d4fa5d` (matches POST response) |
| `received_at_utc` | `2026-07-07T20:14:32.764Z` (UTC, ends with `Z`) |
| `source` | `TradingView` (receiver constant) |
| `method` | `POST` |
| `path` | `/tv/<redacted>` — **secret path NOT stored** |
| `parse_status` | `PARSED` |
| `validation_status` | `ACCEPTED` |
| `symbol` / `exchange` / `timeframe` | `XAUUSD` / `PEPPERSTONE` / `3` |
| `trigger_price` / `trigger_time` / `server_time_hint` | `0` / `MANUAL_TEST` / `MANUAL_TEST` |
| `dedupe_key` | `a272cf4bb1fb…` (sha256) |
| `mode` | `LOGGING_ONLY` |
| `raw_payload` | **byte-exact** copy of the sent payload (contains `test_id: GATE_D_MANUAL_POST_001`, `source: manual-cloud-test`) |

## Append-only / naming

- Object key is date-partitioned + **keyed on the unique `event_id`** → `put` never overwrites a
  distinct object (append-only guarantee holds).
- Only one object exists (bucket empty pre-test + one POST). A future duplicate POST would create a
  **second** object with its own `event_id` (report-time dedupe; nothing discarded at ingest).

## Integrity

- `raw_payload` preserved byte-exact. `received_at_utc` present (UTC). No secret path in the object
  (path redacted; grep for the real secret = 0 occurrences).
