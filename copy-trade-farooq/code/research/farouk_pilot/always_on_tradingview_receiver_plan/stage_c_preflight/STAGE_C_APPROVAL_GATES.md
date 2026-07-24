# Stage C — Approval Gates

**Mode: PREFLIGHT ONLY.** These gates define the **separate approvals** required before each future
action. **None is approved by this document.** Each is an individual, explicit go-ahead from Martyn.

## Gate sequence

| Gate | Action it authorises | Precondition | Reversible by |
|---|---|---|---|
| **C-INSTALL** | Install wrangler (scoped to a Worker project; not global) | Stage B PASS ✅; wrangler currently **absent** | uninstall / delete project folder |
| **C-LOGIN** | `wrangler login` / provide a Workers+R2-scoped API token | C-INSTALL (or dashboard route) | revoke token / logout |
| **C-R2** | Create the private R2 bucket + least-privilege binding | C-LOGIN | delete/disable bucket |
| **C-DEPLOY-DARK** | Deploy the Worker **dark** (no TradingView pointing at it) | C-R2; Worker source reviewed | delete the Worker |
| **D-MANUAL-POST** | Send hand-crafted POSTs to the deployed secret URL (valid/wrong/oversize/disabled) | C-DEPLOY-DARK; dark verification green | it's read-only capture; disable Worker to stop |
| **E-TRADINGVIEW-TEST** | Point **one harmless NEW TradingView test alert** at the cloud receiver | D-MANUAL-POST green | delete the test alert; disable Worker |

## Rules that bind every gate

- Each gate is **explicit and separate** — approving one does **not** approve the next.
- Any gate can be declined or paused; the lane simply stays where it is.
- **No gate here touches** broker/cTrader/QST, permits/leases/orders, execution gates, risk policy, the
  1.0% cap, the shadow engine, or the Telegram PREVIEW listener.
- **No Farouk production alert** is touched through Gate E (that begins only at Stage F/G, which have
  their own gates in `../ALWAYS_ON_VALIDATION_ROLLOUT.md`).
- Everything remains **logging-only / capture-only**; `NOT_INTEGRATION_READY` is unchanged.

## What Martyn approves *next* (the immediate decision)

To move at all, the **first** approval needed is **Gate C-INSTALL** (install wrangler) — or a decision
to deploy via the Cloudflare **dashboard** instead (which skips C-INSTALL but still needs C-LOGIN).
After that, C-LOGIN → C-R2 → C-DEPLOY-DARK, each separately.

**Nothing proceeds until Martyn explicitly approves the specific gate.**
