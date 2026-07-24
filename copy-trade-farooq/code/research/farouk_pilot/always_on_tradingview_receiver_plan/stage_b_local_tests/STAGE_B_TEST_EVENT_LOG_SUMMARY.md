# Stage B — Test Event Log Summary

Read-only summary of `STAGE_B_TEST_EVENT_LOG.jsonl` produced by `run_stage_b_tests.py` on
2026-07-07. The log is a **test artifact** (regenerated each run); it holds only the **ingested
ACCEPTED** events (rejections 404/405/413/503 are proven by HTTP status in the results doc and are not
written to the capture log).

## Records: 4 ingested, all ACCEPTED (lossless append-only)

| # | validation | parse_status | symbol | timeframe | dedupe_key (short) | raw (start) |
|---|---|---|---|---|---|---|
| 1 | ACCEPTED | PARSED | XAUUSD | 3 | `de7e33b94d2d…` | `{"schema_version": "tv-webhook-0.1", …` (P1) |
| 2 | ACCEPTED | INVALID_JSON | — | — | `057f4127b1af…` | `XAUUSD Crossing 4,134.00` (P3 default text) |
| 3 | ACCEPTED | UNRESOLVED_PLACEHOLDER | `{{ticker}}` | `{{interval}}` | `00ba3518ad03…` | `{"schema_version": "tv-webhook-0.1", …` (P2) |
| 4 | ACCEPTED | PARSED | XAUUSD | 3 | `de7e33b94d2d…` | `{"schema_version": "tv-webhook-0.1", …` (P1 duplicate) |

## Report-time dedupe

- **Raw ingested (ACCEPTED):** 4
- **Distinct events (unique `dedupe_key`):** 3 → `de7e33b94d2d`, `057f4127b1af`, `00ba3518ad03`
- **Duplicate flagged at ingest:** **False** — record #4 (a byte-identical repeat of #1) is stored
  append-only as its own `ACCEPTED` record with its own `event_id`; it shares record #1's
  `dedupe_key`, so it collapses to a single distinct event **only in this report**, never at ingest.

## What this demonstrates

- **Lossless, append-only ingest:** nothing is dropped or overwritten; duplicates are kept.
- **Report-time dedupe is the default:** distinct counting happens here (read-only), not at ingest.
- **Parser-only classification:** `parse_status` correctly distinguishes valid JSON, default text
  (INVALID_JSON), and literal-placeholder JSON (UNRESOLVED_PLACEHOLDER) — matching Stage 2.
- **Raw-first storage:** each `raw_payload` is the byte-exact body received.

## Field completeness (per record)

Every record carries: `event_id`, `received_at_utc` (UTC `Z`), `source`, `raw_payload`,
`raw_headers_safe`, `remote_addr` (127.0.0.1), `method`, `path`, `parse_status`, `event_type`,
`direction`, `grade`, `symbol`, `timeframe`, `trigger_price`, `trigger_time`, `server_time_hint`,
`dedupe_key`, `validation_status`, `notes`, `mode`.
