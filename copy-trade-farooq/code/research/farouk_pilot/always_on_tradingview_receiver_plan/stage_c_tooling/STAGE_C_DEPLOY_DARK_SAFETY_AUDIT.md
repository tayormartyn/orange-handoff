# Stage C-DEPLOY-DARK — Safety Audit

**Run:** 2026-07-07 20:27 local. **Mode: DARK WORKER DEPLOYMENT ONLY.** Read-only audit after the dark
deploy.

## Audit results

| Check | Result |
|---|---|
| Dark Worker deployed | **Yes** (`farouk-tv-webhook-logger-v1`, uploaded + bound) |
| Public endpoint / route / workers.dev URL | **None** (`workers_dev=false`, "No targets deployed") |
| R2 binding configured | **Yes** — `EVIDENCE` → `farouk-tv-webhook-evidence-v1` (one bucket, least-privilege) |
| Valid POST sent | **No** |
| R2 object created | **No** (bucket empty) |
| Worker imports (broker/cTrader/QST/execution/permit/lease/order) | **None** |
| Outbound trading request in Worker | **None** (only the R2 `put`) |
| Secret in git-tracked files | **No** (secret only in Worker secret store + gitignored local file) |
| Secret path/token value printed in reports | **No** (fingerprint + length only) |
| TradingView config / Farouk alert edit | **None** |
| cloudflared / receiver / local worker-runtime process | **None running** |
| Broker / cTrader connection | **None** — untouched |
| QST connection | **None** — untouched |
| Execution / permit / lease / order path | **None** — untouched |
| Permit/lease/order artifacts (excluding node_modules) | **None** |
| Execution gates | `MODE=PAPER`, `LISTENER_MODE=PREVIEW`, `EXECUTION_ENABLED=False`, `CTRADER_EXECUTION_ENABLED=False` — **unchanged** |
| Risk policy / 1.0% cap | **Unchanged** |
| Shadow engine | **Not started** |
| Telegram PREVIEW listener PID 40416 | **RUNNING, untouched** |
| `NOT_INTEGRATION_READY` | **Unchanged** |

## New footprint from this gate

- Cloudflare Worker `farouk-tv-webhook-logger-v1` (deployed dark, unrouted, bound to R2, secret set).
- Local project `cloud_worker_dark/` (git-tracked: `src/index.js`, `wrangler.toml`, `.gitignore`,
  README, operator notes) + **gitignored** `LOCAL_SECRET_webhook_path.txt`.
- Wrangler log files under `…\.wrangler\logs\`.
- R2 bucket unchanged (empty).

## Conclusion

Gate C-DEPLOY-DARK completed **safely and in scope**: a logging-only Worker is deployed **dark**
(uploaded, bound to the one private bucket, secret set) with **no public endpoint, no objects, no valid
POST, no TradingView config**; no execution surface anywhere; broker/QST/execution/permit/lease/order
untouched; gates False; secret never exposed; Telegram listener running; `NOT_INTEGRATION_READY`
unchanged.
