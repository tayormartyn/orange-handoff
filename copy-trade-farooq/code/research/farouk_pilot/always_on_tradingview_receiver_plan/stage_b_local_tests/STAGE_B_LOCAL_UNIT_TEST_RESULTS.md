# Stage B — Local Unit Test Results

**Run:** 2026-07-07 18:19 local (Italy UTC+1). **Mode: LOCAL UNIT TEST ONLY.**
Localhost only (127.0.0.1, ephemeral port, in-process). No deployment, no public URL, no tunnel, no
Cloudflare, no TradingView traffic, no broker/QST/execution imports, no permits/leases/orders, no
execution-gate change. Telegram PREVIEW listener (PID 40416) untouched.

## Verdict: PASS (10/10)

The always-on receiver logic reproduces the Stage-2-proven behaviour locally, with **report-time
dedupe** as the default (lossless, append-only ingest).

## How it was tested

- **Harness:** `run_stage_b_tests.py` — starts a localhost HTTP server on an ephemeral port and drives
  requests in-process via `http.client`.
- **Oracle parity:** the harness **reuses the proven receiver's own functions** (`_classify`,
  `_dedupe_key`, `_now_utc`, `SAFE_HEADER_KEYS`, `_startup_safety_check`) from
  `tradingview_webhook_plan/stage1_local_receiver/receiver.py`, so classification/dedupe/UTC behave
  identically to Stage 1/2.
- **Report-time dedupe:** ingest stores **every** accepted POST as `ACCEPTED` (duplicates too); it
  **never** flags/discards a duplicate at ingest. Distinct events are computed afterwards by grouping
  on `dedupe_key`.

## Results

| Test | Description | Expected | Result |
|---|---|---|---|
| B1 | valid JSON → correct secret path, no header | 200 ACCEPTED / PARSED | ✅ PASS |
| B2 | wrong path | 404, no record | ✅ PASS |
| B3 | GET (non-POST) | 405, no record | ✅ PASS |
| B4 | default text body (`XAUUSD Crossing 4,134.00`) | 200 ACCEPTED / INVALID_JSON, raw stored | ✅ PASS |
| B5 | literal `{{...}}` placeholders | 200 ACCEPTED / UNRESOLVED_PLACEHOLDER | ✅ PASS |
| B6 | duplicate of B1 | ACCEPTED append-only; distinct unchanged (report-time) | ✅ PASS |
| B7 | body over 64 KB | 413, no record | ✅ PASS |
| B8 | kill switch (`enabled=false`) | 503, no accept | ✅ PASS |
| B9 | import firewall (forbidden module present) | refuses (fail-closed) | ✅ PASS |
| B10 | UTC receiver ts + provider time verbatim + raw byte-exact + event_id | all true | ✅ PASS |

## Additional verifications (all ✅)

- **Raw payload stored byte-exact** — B10 confirmed the stored `raw_payload` == the exact bytes sent.
- **`event_id` generated** — UUIDv4 per record.
- **`received_at_utc` generated** — ISO-8601 ending in `Z` (UTC).
- **Path-secret auth works** — B1 accepted on exact secret path with **no** header (PATH_ONLY).
- **Wrong path rejected** — B2 → 404.
- **Non-POST rejected** — B3 → 405.
- **No outbound trading request possible** — harness + oracle import stdlib only; the only write is to
  the local Stage B JSONL; no `fetch`/broker/trading host call exists in the code path.
- **No broker/cTrader/QST/execution module imported** — harness imports: stdlib + the oracle receiver
  (itself stdlib-only). B9 proves the fail-closed firewall.
- **No permit/lease/order artifacts created** — post-run scan: none.
- **Execution gates remain False** — `MODE=PAPER`, `LISTENER_MODE=PREVIEW`, `EXECUTION_ENABLED=False`,
  `CTRADER_EXECUTION_ENABLED=False` (unchanged).
- **Telegram PREVIEW listener untouched** — PID 40416 running; no stray Stage B / receiver process
  after the run (in-process server shut down cleanly).

## Report-time dedupe evidence

- `raw_ingested_accepted = 4`
- `distinct_events (by dedupe_key) = 3`
- `duplicate_flag_at_ingest = False` (lossless ingest — nothing discarded/flagged at ingest)
- P1 ingested **2×** (B1 + B6) → collapses to **1** distinct only in the report, not at ingest.

See `STAGE_B_TEST_EVENT_LOG.jsonl` (4 records) and `STAGE_B_TEST_EVENT_LOG_SUMMARY.md`.

## Note on B9 output

During the run you will see a line: `REFUSING TO START — forbidden module(s) loaded:
['ctrader_fake_injected']`. **That is B9 succeeding** — the harness deliberately injects a fake
forbidden module and the receiver's import firewall refuses (fail-closed), exactly as required.
