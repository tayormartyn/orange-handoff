# Workers.dev Endpoint Record

**Gate C-ENDPOINT. 2026-07-07.**

| Field | Value |
|---|---|
| Worker | `farouk-tv-webhook-logger-v1` |
| Endpoint (base URL, no secret path) | `https://farouk-tv-webhook-logger-v1.taylormartyn70.workers.dev` |
| Subdomain | `taylormartyn70.workers.dev` (registered by Martyn in the dashboard) |
| Routing | `workers_dev = true` |
| Version ID | `4701c98e-bf53-436a-91ce-4a92b0487920` |
| Preview URLs | enabled by default (per-version); can be disabled with `preview_urls = false` if wanted |
| Auth | PATH_ONLY — `POST https://…workers.dev/tv/<secret path>` (secret path only in gitignored local file) |
| Bindings | `EVIDENCE` → `farouk-tv-webhook-evidence-v1`; vars `TV_WEBHOOK_ENABLED=1`, `TV_WEBHOOK_MAX_BODY_BYTES=65536` |

## Reachability confirmed

- The base URL responds (our Worker answered 405/404 to negative checks) → endpoint live.
- Without the exact secret path, POSTs get 404; non-POST gets 405 — nothing is stored.

## Webhook URL (for later, Gate E)

- The full webhook URL = `https://farouk-tv-webhook-logger-v1.taylormartyn70.workers.dev/tv/<secret_path_value>`.
- The `<secret_path_value>` lives only in the gitignored `cloud_worker_dark/LOCAL_SECRET_webhook_path.txt`
  (marked DO NOT COMMIT / DO NOT PASTE TO CHAT). It is **not** reproduced here.

## Status

Endpoint enabled and reachable; logging-only; no TradingView pointed at it; bucket empty. Ready for a
**future, separately-authorised** Gate D manual POST.
