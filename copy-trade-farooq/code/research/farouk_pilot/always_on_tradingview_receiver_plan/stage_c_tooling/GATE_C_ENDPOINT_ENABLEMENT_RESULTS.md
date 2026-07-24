# Gate C-ENDPOINT — Workers.dev Endpoint Enablement Results

**Run:** 2026-07-07 20:47 local (Italy UTC+1). **Mode: WORKERS.DEV ENDPOINT ENABLEMENT ONLY.**
No TradingView config, no Farouk-alert edit, no valid POST, no R2 object, no QST/broker/cTrader, no
broker/QST/execution imports, no permit/lease/order, no gate change, no shadow engine. Telegram PREVIEW
listener (PID 40416) untouched. Full secret path **not** printed.

## Outcome: endpoint ENABLED ✅

## What was done

1. Set `workers_dev = true` in `cloud_worker_dark/wrangler.toml` (subdomain registered by Martyn).
2. Redeployed the **same** logging-only Worker (no code change) → exit 0.
3. Ran only **safe negative checks** (no valid POST).

## Endpoint

| Item | Value |
|---|---|
| Endpoint enabled | **Yes** |
| Worker URL (no secret path) | **`https://farouk-tv-webhook-logger-v1.taylormartyn70.workers.dev`** |
| Latest version ID | `4701c98e-bf53-436a-91ce-4a92b0487920` |
| Bindings (unchanged) | `EVIDENCE` → `farouk-tv-webhook-evidence-v1`; `TV_WEBHOOK_ENABLED="1"`; `TV_WEBHOOK_MAX_BODY_BYTES="65536"` |
| Secret | `TV_WEBHOOK_SECRET_PATH` still set (secret_text); value not printed |

> **Note — Preview URLs:** the deploy warned that per-version **Preview URLs** are enabled by default
> (since `preview_urls` is unset). They are additional versioned URLs that still require the same
> secret path to do anything (logging-only). To tighten the surface, `preview_urls = false` can be set
> and redeployed — **not done here** (out of this gate's scope); flagged for your call.

## Negative checks (no valid POST, no R2 write)

| # | Request | Expected | Result |
|---|---|---|---|
| 1 | `GET /` | 405 (non-POST) | ✅ 405 |
| 2 | `GET /tv/some-wrong-path` | 405 (non-POST; method checked first) | ✅ 405 |
| 3 | `POST /tv/DEFINITELY-WRONG-SECRET-0000` | 404 (wrong path; **no** R2 write) | ✅ 404 |
| 4 | `PUT /` | 405 (non-POST) | ✅ 405 |
| 5 | `POST /` (root, wrong path) | 404 (**no** R2 write) | ✅ 404 |

- **No valid POST sent** — the real secret path was never used (it is not present in the shell; only in
  the gitignored local file).
- **No R2 object created** — every response returned **before** the R2 `put` code path (405 before the
  path check; 404 before the body read/put). Bucket remains **empty by construction**.

## Safety

- No TradingView config; Farouk alerts untouched; no broker/QST/execution; no permit/lease/order; gates
  unchanged; Telegram listener untouched. See `STAGE_C_ENDPOINT_SAFETY_AUDIT.md`.

## Next

Gate **D-MANUAL-POST** is now **unblocked** (endpoint exists) but is **NOT started / NOT authorised**.
See `NEXT_GATE_D_MANUAL_POST_READINESS.md`.
