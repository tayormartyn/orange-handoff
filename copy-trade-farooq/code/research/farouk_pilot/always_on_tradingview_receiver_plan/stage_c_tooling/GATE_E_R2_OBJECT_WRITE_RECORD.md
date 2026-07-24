# Gate E — R2 Object Write Record (PASSED)

**2026-07-08.** Two Gate E objects written and verified via `wrangler r2 object get … --remote`.

| Field | Value |
|---|---|
| Pre-Gate-E count | 1 (Gate D object) |
| Post-Gate-E count | **3** (Gate D + 2 Gate E captures) |
| Bucket | `farouk-tv-webhook-evidence-v1` |

## Objects

| Key | Origin | received_at_utc | bytes |
|---|---|---|---|
| `events/2026/07/07/c73de580-…jsonl` | Gate D manual POST (intact) | 2026-07-07T20:14:32Z | 1236 |
| `events/2026/07/08/3a7b62ab-2a91-48e2-8107-2db0b7fe42f7.jsonl` | Gate E fire #1 | 2026-07-08T16:42:05Z | 1323 |
| `events/2026/07/08/f1543b21-2627-472e-983c-047b4175f0e4.jsonl` | Gate E fire #2 (tail-captured 200) | 2026-07-08T16:54:12Z | 1323 |

## Both Gate E objects

- `validation_status: ACCEPTED`, `parse_status: PARSED`, `mode: LOGGING_ONLY`.
- `source: TradingView`, `symbol: XAUUSD`, `exchange: PEPPERSTONE`, `timeframe: 1`.
- `received_at_utc` present (UTC `Z`); `raw_payload` byte-preserved; `path: "/tv/<redacted>"` (secret
  NOT stored; grep for secret = 0).
- Append-only, unique-event_id keys → no overwrite. Two distinct events (report-time dedupe; not
  discarded at ingest).

## Note

Two objects exist because two corrected-URL fires both succeeded. Both are legitimate captures. Expected
in a single-fire test: exactly one; here two fires → two objects.
