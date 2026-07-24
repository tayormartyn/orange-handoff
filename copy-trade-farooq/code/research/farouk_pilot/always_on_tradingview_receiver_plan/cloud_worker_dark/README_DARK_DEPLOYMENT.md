# Dark Worker — `farouk-tv-webhook-logger-v1`

Always-on TradingView **logging-only** Cloudflare Worker. Capture/evidence infrastructure only.
**No broker/cTrader/QST/execution/permit/lease/order. No outbound trading requests. No trade logic.**

## Status: DEPLOYED DARK (no public endpoint)

- Worker **uploaded** and bound to the private R2 bucket, but **not publicly routed**
  (`workers_dev = false`, "No targets deployed") — so it currently has **no reachable URL**.
- A public endpoint is **deliberately deferred**: enabling it (register a workers.dev subdomain, or
  attach a route) is a separate, Martyn-owned decision, required before Gate D (manual POST).

## Files (git-tracked, contain NO secret)

- `src/index.js` — the Worker (POST-only, PATH_ONLY auth, body cap, raw-first, UTC, event_id,
  parse/classify, append-only R2 put keyed on unique `event_id`, report-time dedupe, fail-closed).
- `wrangler.toml` — name, R2 binding (`EVIDENCE` → `farouk-tv-webhook-evidence-v1`), non-secret vars
  (`TV_WEBHOOK_ENABLED`, `TV_WEBHOOK_MAX_BODY_BYTES`), `workers_dev = false`.
- `.gitignore` — excludes `node_modules/`, `.dev.vars`, `.wrangler/`, and `LOCAL_SECRET_*.txt`.

## NOT git-tracked (gitignored)

- `LOCAL_SECRET_webhook_path.txt` — **LOCAL SECRET — DO NOT COMMIT — DO NOT PASTE TO CHAT.** Holds the
  `TV_WEBHOOK_SECRET_PATH` value and the eventual webhook URL. Needed later (Gate D/E) to build the
  webhook URL. Keep it local.

## Secrets / vars

- `TV_WEBHOOK_SECRET_PATH` — set via `wrangler secret put` (secret_text on the Worker); **never** in
  the repo. Fingerprint (sha256 first 12): `e1c56bbe1346`; length 43.
- `TV_WEBHOOK_ENABLED` = `"1"` (kill switch → `"0"` makes the Worker return 503).
- `TV_WEBHOOK_MAX_BODY_BYTES` = `"65536"` (64 KB cap).

## Behaviour (parity with Stage B oracle)

- `POST /tv/<secret>` with a body → 200, one append-only R2 object `events/YYYY/MM/DD/<event_id>.jsonl`.
- Wrong path → 404. Non-POST → 405. Oversize → 413. `ENABLED=0` or secret unset → 503 (fail-closed).
- The stored record **redacts the secret path** (`"/tv/<redacted>"`) so the secret never lands in R2.

## Deploy / operate (local wrangler, authenticated)

```
cd cloud_worker_dark
../stage_c_tooling/node_modules/.bin/wrangler deploy            # upload (dark; no route)
../stage_c_tooling/node_modules/.bin/wrangler secret put TV_WEBHOOK_SECRET_PATH   # set secret (stdin)
../stage_c_tooling/node_modules/.bin/wrangler deployments list  # confirm versions
```

## Kill switch / rollback

- `TV_WEBHOOK_ENABLED=0` → 503; delete the Worker → gone; rotate secret path → old URL 404s; delete
  the R2 bucket → storage gone. Any one halts capture.
