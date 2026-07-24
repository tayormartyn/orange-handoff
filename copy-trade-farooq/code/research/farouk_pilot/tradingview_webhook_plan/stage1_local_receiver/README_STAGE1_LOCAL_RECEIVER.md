# Stage 1 — Local Manual-POST Receiver (README)

**Mode: STAGE 1 LOCAL MANUAL-POST TEST ONLY.** Localhost only. Logging/observation only. No public
URL, no tunnel, no TradingView config, no broker/QST/execution/permit/lease/order, no execution-gate
change. Kill switch = Ctrl+C.

## What this is

A `stdlib-only` (`http.server`) receiver that accepts a **localhost** POST, stores the raw body
byte-exact plus a UTC receipt time and safe headers, classifies for metadata (read-only), dedupes,
and appends one line to an append-only JSONL log. Nothing else.

**Why no framework:** a single localhost logging endpoint needs only `http.server` from the standard
library. Adding Flask/FastAPI would introduce dependencies and a larger surface for zero benefit at
this scope, so stdlib is used deliberately.

## Files

- `receiver.py` — the receiver.
- `sample_payloads/manual_post_valid.json` — a valid test payload (no credentials).
- `sample_payloads/manual_post_invalid.json` — a body used for the missing/incorrect-secret test.
- `logs/tradingview_webhook_events.jsonl` — append-only event log (created at runtime).
- `STAGE1_MANUAL_POST_TEST_RESULTS.md` — recorded test run + safety check.

## Configuration (env; safe local defaults, NOT real secrets)

| Env var | Default (local test) | Meaning |
|---|---|---|
| `TV_WEBHOOK_SECRET_PATH` | `tv-local-test-path` | **PRIMARY auth** — secret path segment → POST to `/tv/<path>` |
| `TV_WEBHOOK_SHARED_SECRET` | `tv-local-test-secret` | `X-TV-Token` header value — **manual local test only** |
| `TV_WEBHOOK_AUTH_MODE` | `PATH_AND_HEADER` | `PATH_AND_HEADER` (local test) or `PATH_ONLY` (TradingView-compatible) |
| `TV_WEBHOOK_PORT` | `8787` | localhost port |
| `TV_WEBHOOK_ENABLED` | `1` | set `0` for soft kill (refuse + log) |

> The defaults are **local placeholders, not real credentials**. No real secret is used anywhere in
> Stage 1.

> **AUTH NOTE (important):** **X-TV-Token header is valid for manual local POST tests only. Real
> TradingView Stage 2 must authenticate by exact long random secret path unless custom header support
> is independently confirmed.** TradingView alerts cannot be assumed to send custom headers, so the
> **long random secret path is the primary authentication control.** For Stage 1 local tests the
> default `PATH_AND_HEADER` mode also requires the header (which is why the missing-header POST
> returns 401). For a real TradingView test, the receiver would run in `PATH_ONLY` mode where the
> exact secret path alone authenticates and the header is optional.

## Run it (localhost)

```
python research/farouk_pilot/tradingview_webhook_plan/stage1_local_receiver/receiver.py
```

It binds `127.0.0.1:8787` and prints the POST path + log location. Ctrl+C stops it.

## Manual test POSTs

**Valid (should log, HTTP 200):**
```
curl -s -X POST "http://127.0.0.1:8787/tv/tv-local-test-path" \
  -H "X-TV-Token: tv-local-test-secret" \
  -H "Content-Type: application/json" \
  --data-binary @sample_payloads/manual_post_valid.json
```

**Invalid — missing/incorrect secret (should reject, HTTP 401, not stored as ACCEPTED):**
```
curl -s -X POST "http://127.0.0.1:8787/tv/tv-local-test-path" \
  -H "Content-Type: application/json" \
  --data-binary @sample_payloads/manual_post_invalid.json
```

**Non-POST (should reject, HTTP 405):**
```
curl -s "http://127.0.0.1:8787/tv/tv-local-test-path"
```

## Safety properties (enforced in code)

- Binds `127.0.0.1` only; non-localhost remote → 403.
- POST only; GET/PUT/DELETE/HEAD/OPTIONS/PATCH → 405.
- **Exact secret path is the primary auth** (constant-time compare). `X-TV-Token` header is an
  *additional* control required only in the default `PATH_AND_HEADER` (local-test) mode; in
  `PATH_ONLY` (TradingView) mode the path alone authenticates and the header is optional.
- 64 KB body cap.
- Append-only JSONL; raw stored before parsing; parser never decides anything.
- Start-up import firewall refuses to start if any broker/cTrader/QST/execution/permit module is
  loaded.
- **No** broker/QST imports, **no** outbound calls, **no** permit/lease/order creation, **no**
  execution path anywhere in this module.
