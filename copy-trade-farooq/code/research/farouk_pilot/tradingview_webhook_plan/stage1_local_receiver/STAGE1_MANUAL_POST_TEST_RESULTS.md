# Stage 1 — Manual POST Test Results

**Run:** 2026-07-07 08:44 local (Italy UTC+1). **Mode: STAGE 1 LOCAL MANUAL-POST TEST ONLY.**
Localhost only. No TradingView config, no public URL, no tunnel, no broker/QST/execution, no
permit/lease/order, no execution-gate change. Telegram PREVIEW listener left untouched.

## Receiver

- **File:** `research/farouk_pilot/tradingview_webhook_plan/stage1_local_receiver/receiver.py`
- **Stack:** Python standard library only (`http.server`) — no framework (justified: a single
  localhost logging endpoint needs no more).
- **Bind:** `127.0.0.1:8787` (localhost only). **POST path:** `/tv/tv-local-test-path`.
  **Auth header:** `X-TV-Token` (local test value; not a real secret).

> **Auth-model note (added post-run):** Stage 1 ran in the default **`PATH_AND_HEADER`** mode, where
> the `X-TV-Token` header was required (hence the missing-header POST correctly returned 401). **This
> header requirement is for manual local POST tests only.** Real TradingView Stage 2 must authenticate
> by the **exact long random secret path** (`PATH_ONLY` mode) unless custom header support is
> independently confirmed — TradingView cannot be assumed to send custom headers. The Stage 1 results
> below remain valid for the local test as run.
- **Start-up import firewall:** passed (no broker/cTrader/QST/execution/permit module loaded).
- **Compile check:** `python -m py_compile receiver.py` → OK.

## Commands used

**Start (localhost):**
```
python research/farouk_pilot/tradingview_webhook_plan/stage1_local_receiver/receiver.py
```

**Manual POSTs** (from the `stage1_local_receiver/` folder):
```
# (1) VALID — correct secret header
curl -s -X POST "http://127.0.0.1:8787/tv/tv-local-test-path" \
  -H "X-TV-Token: tv-local-test-secret" -H "Content-Type: application/json" \
  --data-binary @sample_payloads/manual_post_valid.json

# (2) INVALID — missing X-TV-Token header
curl -s -X POST "http://127.0.0.1:8787/tv/tv-local-test-path" \
  -H "Content-Type: application/json" \
  --data-binary @sample_payloads/manual_post_invalid.json

# (3) NON-POST GET
curl -s "http://127.0.0.1:8787/tv/tv-local-test-path"

# (4) VALID again — duplicate (dedupe test)
curl -s -X POST "http://127.0.0.1:8787/tv/tv-local-test-path" \
  -H "X-TV-Token: tv-local-test-secret" -H "Content-Type: application/json" \
  --data-binary @sample_payloads/manual_post_valid.json
```

## Results

| # | Request | HTTP | Stored record | validation_status |
|---|---|---|---|---|
| 1 | Valid POST (correct secret) | **200** | yes | **ACCEPTED** (PARSED → A_PLUS / A+ / LONG / XAUUSD / 3) |
| 2 | POST, no `X-TV-Token` | **401** | yes (rejection logged, no trade path) | **REJECTED_AUTH** |
| 3 | GET (non-POST) | **405** | **no record** (correct — no side effect) | — |
| 4 | Valid POST repeated | **200** | yes | **DUPLICATE** (dedupe_key matched) |

- **JSONL records total:** 3 (`ACCEPTED` ×1, `REJECTED_AUTH` ×1, `DUPLICATE` ×1).
- **Distinct ACCEPTED events:** **1** (the duplicate correctly did not add a second accepted event).
- Raw payload stored **byte-exact**; `received_at_utc`, `event_id`, `raw_headers_safe`
  (content-type/length/user-agent only), `remote_addr` (127.0.0.1), `method`, `path`,
  `parse_status`, `event_type`, `direction`, `grade`, `symbol`, `timeframe`, `dedupe_key`,
  `validation_status`, `notes` all present.
- **Log:** `logs/tradingview_webhook_events.jsonl`.

## Post-test read-only safety check

- **Python/Node processes:** only `python.exe` PID **40416** = the Telegram PREVIEW listener.
  `receiver.py` stopped cleanly (Ctrl+C-equivalent kill).
- **Telegram PREVIEW listener:** **RUNNING, PID 40416, UNAFFECTED** (started 08:14:54, still up).
- **Broker/cTrader/QST/execution processes:** **NONE** (only Windows `msedge …SearchIndexerInterface
  Broker` and `UserOOBEBroker.exe` matched the word "broker" — OS/Edge, unrelated).
- **Permit/lease/order artifacts:** **NONE created** (no runtime permit/lease/order files anywhere;
  none in the webhook plan folder).
- **Execution gates (read-only):** `MODE=PAPER`, `LISTENER_MODE=PREVIEW`, `EXECUTION_ENABLED=False`,
  `CTRADER_EXECUTION_ENABLED=False` — **all unchanged**.
- **No broker/QST/execution path exists** in `receiver.py` (imports: `hmac, http.server, json, os,
  sys, uuid, datetime, hashlib` only; no outbound HTTP client; no engine import).

## Verdict

Stage 1 **PASSED**. The localhost logging-only receiver captures a valid TradingView-shaped POST,
rejects a missing-secret POST, rejects non-POST, and dedupes a repeat — all append-only, with no
execution surface and no impact on the running listener or the execution gates.
