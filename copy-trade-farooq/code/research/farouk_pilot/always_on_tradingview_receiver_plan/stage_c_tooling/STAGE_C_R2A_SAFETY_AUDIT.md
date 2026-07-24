# Stage C-R2A — Safety Audit

**Run:** 2026-07-07 19:52 local. **Mode: READ-ONLY R2 SCOPE CHECK ONLY.** Read-only audit after the
check.

## Audit results

| Check | Result |
|---|---|
| R2 bucket created / updated / deleted | **None** (list command failed with `10042`; created nothing) |
| Worker created | **None** |
| `wrangler.toml` / Worker `src/` / `.dev.vars` | **None** |
| Deployment | **None** |
| Public endpoint | **None** |
| Route created | **None** |
| TradingView config / Farouk alert edit | **None** |
| cloudflared / receiver / worker-runtime / deploy process | **None running** |
| Broker / cTrader connection | **None** — untouched |
| QST connection | **None** — untouched |
| Execution / permit / lease / order path | **None** — untouched |
| Permit/lease/order artifacts (excluding node_modules) | **None** |
| Execution gates | `MODE=PAPER`, `LISTENER_MODE=PREVIEW`, `EXECUTION_ENABLED=False`, `CTRADER_EXECUTION_ENABLED=False` — **unchanged** |
| Risk policy / 1.0% cap | **Unchanged** |
| Shadow engine | **Not started** |
| Telegram PREVIEW listener PID 40416 | **RUNNING, untouched** |
| Token/secret printed or saved to project files | **No** |
| Retry with broader permissions | **Not performed** (per hard rules — stopped on denial) |

## New footprint from this gate

- A wrangler **log** file under `…\.wrangler\logs\` (from the failed list command). No credential, no
  resource, no project-file change.

## Conclusion

Gate C-R2A completed **safely and in scope**: a single read-only R2 list command was run; it revealed
**R2 is not enabled on the account** (`10042`), not a scope issue. **Nothing was created, deployed, or
exposed; no TradingView config; no broker/QST/execution/permit/lease/order; gates False; Telegram
listener untouched; no token exposed.** Per the rules, no retry with broader permissions was attempted.
