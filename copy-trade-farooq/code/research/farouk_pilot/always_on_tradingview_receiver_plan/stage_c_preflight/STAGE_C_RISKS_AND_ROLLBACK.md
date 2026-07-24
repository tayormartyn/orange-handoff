# Stage C — Risks & Rollback

**Mode: PREFLIGHT ONLY.** Risk assessment + rollback plan for a *future* dark deployment. Nothing is
deployed; this is planning.

## Risk assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Worker URL leaks | low | **low** — logging-only; worst case is junk log entries (no execution, no broker reach, no data exfiltration) | long random secret path; rotate on leak; body cap; rate limit; audit |
| Accidental TradingView wiring in Stage C | low | medium — would start real capture early | checklist explicitly keeps it **dark**; Gate E is separate |
| wrangler install pulls unexpected deps | low | low | install scoped to an isolated Worker project; review lockfile; not global |
| Cloudflare login/token over-scoped | low | medium | use a token scoped to **Workers + R2 only**; or OAuth; revoke after |
| R2 binding over-permissioned | low | medium | least-privilege: write/put to one bucket only |
| Secret committed to repo | low | medium | secret only in Worker secret store; `.gitignore` dev-vars; record only a hash |
| Storage write fails silently | low | medium | fail-closed: 5xx on R2 error, never accept-without-store |
| Execution-surface creep | very low | **high (unacceptable)** | import firewall (fail-closed); no broker/QST/execution import; no outbound trading call; hard vetoes |

**Overall:** the **bounded blast radius** (logging-only, no execution, no credentials) keeps Stage C
low-risk. The one thing to guard hardest is **execution-surface creep**, which the import firewall +
hard vetoes structurally prevent.

## Rollback (any ONE is a complete, immediate stop)

1. **`TV_WEBHOOK_ENABLED=0`** → Worker returns 503 to all requests (fastest, reversible).
2. **Delete/disable the Worker** → endpoint gone.
3. **Rotate `TV_WEBHOOK_SECRET_PATH`** → old URL 404s.
4. **Delete/disable the R2 bucket** → storage gone.
5. **Revoke the Cloudflare token / logout** → no further deploys.
6. **Uninstall wrangler / delete the Worker project folder** → local toolchain removed.

## What rollback preserves / does not touch

- **Preserved:** any captured evidence objects already written (append-only; legitimate evidence).
- **Never touched by rollback:** broker/QST/execution (none exists in this lane), permits/leases/orders
  (none), execution gates (unchanged), risk policy, the 1.0% cap, the shadow engine, and the Telegram
  PREVIEW listener.

## Post-rollback verification (to run at the time)

- Worker deleted/disabled (404/none); R2 bucket state as intended; no secret left in repo; gates still
  `PAPER/PREVIEW/False/False`; Telegram listener PID 40416 untouched.
