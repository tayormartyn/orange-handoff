# Gate C-DEPLOY-DARK — Results

**Run:** 2026-07-07 20:27 local (Italy UTC+1). **Mode: DARK WORKER DEPLOYMENT ONLY.**
No TradingView config, no Farouk-alert edit, no real TradingView traffic, no Stage D manual POST, no
QST/broker/cTrader, no broker/QST/execution imports, no permit/lease/order, no gate change, no shadow
engine. Telegram PREVIEW listener (PID 40416) untouched. No secret path/token value printed.

## Outcome: Worker deployed **DARK** (uploaded + bound, no public endpoint)

## What was done

1. Authored the Worker project under `../cloud_worker_dark/` (`src/index.js`, `wrangler.toml`,
   `.gitignore`, README, operator notes).
2. Pre-deploy safety: confirmed the Worker source has **no imports**, **no broker/QST/execution**, and
   **no outbound `fetch`** (the only `fetch` is the Worker's own request handler); confirmed
   authenticated + bucket exists.
3. Deployed (uploaded) the Worker; set `TV_WEBHOOK_SECRET_PATH` as a Worker **secret** (via stdin;
   value never shown); redeployed with `workers_dev = false` for a clean **dark** state (exit 0).

## Deployment record

| Item | Value |
|---|---|
| Worker deployed | **Yes** (uploaded, bound) |
| Exact Worker name | **`farouk-tv-webhook-logger-v1`** (suggested name accepted) |
| Public endpoint | **None** — `workers_dev = false`, "No targets deployed" (account has no workers.dev subdomain yet) |
| Latest version (UTC) | 2026-07-07T19:25:28Z (Version ID `8e4b693c…`) |
| R2 binding | **`EVIDENCE` → `farouk-tv-webhook-evidence-v1`** (least-privilege: one bucket) |
| Vars | `TV_WEBHOOK_ENABLED="1"`, `TV_WEBHOOK_MAX_BODY_BYTES="65536"` |
| Secret | `TV_WEBHOOK_SECRET_PATH` set (secret_text); fingerprint sha256[:12] `e1c56bbe1346`, len 43; value only in gitignored local file |
| Valid POST sent | **No** |
| R2 object created | **No** (bucket empty) |

## Dark checks

- **Worker deployment exists** — ✅ confirmed via `wrangler deployments list` (versions present).
- **Worker endpoint exists** — ❌ **No** (deliberately dark: `workers_dev=false`, no route). Therefore
  the HTTP wrong-path (404) / non-POST (405) checks **could not be run over the network** — there is no
  URL to hit. The Worker's request logic is nonetheless proven by the **Stage B oracle** (10/10,
  including 404/405/413/503), which `src/index.js` reproduces.
- **No valid POST sent** — ✅.
- **R2 bucket empty** — ✅ (no endpoint + no POST → no write; empty by construction).

## Endpoint deferral (surfaced decision)

The account has **no workers.dev subdomain** (registering one is account-global — Martyn's choice). So
the Worker is dark with no URL. Before **Gate D (manual POST)** an endpoint must be enabled — via a
workers.dev subdomain or a custom route. See `../cloud_worker_dark/DARK_DEPLOYMENT_OPERATOR_NOTES.md`.
**I did not register a subdomain or change routing.**

## Next

Gate **D-MANUAL-POST** can be **considered** next but is **NOT started / NOT authorised**, and is
**blocked** until an endpoint is enabled. See `NEXT_GATE_D_MANUAL_POST_READINESS.md`.
