# Dark Worker — Deployment Record

**Gate C-DEPLOY-DARK. 2026-07-07.**

| Field | Value |
|---|---|
| Worker name | `farouk-tv-webhook-logger-v1` |
| Account ID | masked `7173…43ad` |
| Source | `always_on_tradingview_receiver_plan/cloud_worker_dark/src/index.js` |
| Config | `.../cloud_worker_dark/wrangler.toml` |
| Compatibility date | 2026-07-01 |
| Upload size | 5.57 KiB (gzip 2.10 KiB) |
| Latest version ID | `8e4b693c-338d-4dd4-8ea7-f8e3e068ff85` (2026-07-07T19:25:28Z) |
| Public routing | **DARK** — `workers_dev = false`, "No targets deployed" (no URL, no route) |
| R2 binding | `EVIDENCE` → `farouk-tv-webhook-evidence-v1` |
| Vars | `TV_WEBHOOK_ENABLED="1"`, `TV_WEBHOOK_MAX_BODY_BYTES="65536"` |
| Secret | `TV_WEBHOOK_SECRET_PATH` (secret_text) — fingerprint `e1c56bbe1346`, len 43; value only in gitignored local file |
| Objects in bucket | 0 (empty) |

## Deploy sequence (as executed)

1. `wrangler deploy` — uploaded the Worker + bindings. (First attempt could not publish to workers.dev
   — no subdomain — so no public URL was created.)
2. `wrangler secret put TV_WEBHOOK_SECRET_PATH` — set the secret from stdin (value not shown).
3. Set `workers_dev = false` in `wrangler.toml`; `wrangler deploy` again → clean exit 0, dark
   (uploaded, no route).
4. `wrangler deployments list` — confirmed versions exist.

## State

The Worker is **live on Cloudflare (uploaded, bound, configured)** but **unreachable** (no endpoint).
It holds nothing (bucket empty). It will capture nothing until (a) an endpoint is enabled and (b) a
POST reaches the secret path — neither done in this gate. Fully reversible: delete the Worker, delete
the bucket, disable via `TV_WEBHOOK_ENABLED=0`, or rotate the secret.
