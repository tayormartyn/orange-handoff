# Gate C-ENDPOINT-HYGIENE — Results

**Run:** 2026-07-07 21:07 local (Italy UTC+1). **Mode: ENDPOINT HYGIENE ONLY.**
No valid POST, real secret path not used, no TradingView config, no Farouk-alert edit, no bucket
create/delete, no R2 object, no QST/broker/cTrader, no permit/lease/order, no gate change, no shadow
engine. Telegram PREVIEW listener (PID 40416) untouched. Full secret path not printed.

## Outcome: Preview URLs DISABLED ✅

## What was done

1. Added `preview_urls = false` to `cloud_worker_dark/wrangler.toml` (**config only — no Worker logic
   change**; upload size unchanged at 5.57 KiB).
2. Redeployed the same logging-only Worker → exit 0. The earlier "Preview URLs enabled by default"
   warning **no longer appears**, confirming the setting took effect.
3. Re-ran safe negative checks (no valid POST).

## Record

| Item | Value |
|---|---|
| Preview URLs | **Disabled** (`preview_urls = false`; deploy no longer warns about preview URLs) |
| Main workers.dev endpoint | **Still live** — `https://farouk-tv-webhook-logger-v1.taylormartyn70.workers.dev` |
| New version ID | `c6d17920-16bc-433c-a272-fddb7228751e` |
| Worker logic change | **None** (same code, same bindings, same secret) |
| Bindings | `EVIDENCE` → `farouk-tv-webhook-evidence-v1`; `TV_WEBHOOK_ENABLED="1"`; `TV_WEBHOOK_MAX_BODY_BYTES="65536"` |
| Valid POST sent | **No** |
| R2 object created | **No** (bucket empty) |

## Negative checks (all passed; none reached R2)

| Request | Expected | Result |
|---|---|---|
| `GET /` | 405 | ✅ 405 |
| `POST /tv/WRONG-SECRET-hygiene-0000` | 404 | ✅ 404 |
| `PUT /` | 405 | ✅ 405 |
| `GET /tv/some-wrong-path` | 405 | ✅ 405 |

The real secret path was **not** used. All responses returned before the R2 `put` → **no accepted
request reached R2**; bucket remains **empty**.

## Safety

No TradingView config; Farouk alerts untouched; no broker/QST/execution; no permit/lease/order; gates
unchanged; Telegram listener untouched. See `ENDPOINT_HYGIENE_NEGATIVE_CHECKS.md` and the audit note
in this folder.

## Next

Gate **D-MANUAL-POST** remains **unblocked but NOT started / NOT authorised**. See
`NEXT_GATE_D_MANUAL_POST_READINESS.md`.
