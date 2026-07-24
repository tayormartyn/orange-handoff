# Next Gate — C-DEPLOY-DARK Readiness

**Mode: R2 BUCKET CREATION ONLY (this gate, C-R2B, is complete).** Describes **Gate C-DEPLOY-DARK**
(deploy the logging-only Worker **dark**). **C-DEPLOY-DARK is NOT started and NOT authorised.**

## Prerequisites

- [x] Stage B PASS (receiver logic proven locally).
- [x] Gate C-INSTALL (Wrangler 4.107.1 local).
- [x] Gate C-LOGIN (authenticated).
- [x] Gate C-R2A (R2 AVAILABLE).
- [x] **Gate C-R2B — private bucket `farouk-tv-webhook-evidence-v1` created (empty, unbound).**
- [ ] Worker source authored (LOGGING_ONLY; logic == Stage B oracle) — **not yet**.
- [ ] `wrangler.toml` with the **least-privilege R2 binding** — **not yet**.
- [ ] Worker secrets prepared (`TV_WEBHOOK_SECRET_PATH`, `TV_WEBHOOK_ENABLED`) — **not yet**; never
  committed.
- [ ] Explicit **Gate C-DEPLOY-DARK** approval.

## What Gate C-DEPLOY-DARK would do (later, only if approved)

- Author the LOGGING_ONLY Worker (POST-only, exact secret path, body cap, raw-first, UTC stamp,
  safe-header whitelist, parser-only, event_id, **append-only R2 put keyed on `event_id`**,
  `ENABLED` flag, cold-start import firewall). Logic reproduces the Stage B oracle.
- Bind it to `farouk-tv-webhook-evidence-v1` with a **least-privilege** binding (write/put to that one
  bucket only).
- Set the secret path + kill-switch as Worker **secrets** (generated locally; only a hash fingerprint
  recorded; never committed).
- **Deploy dark** — the Worker URL exists but **no TradingView alert points at it**; it receives no
  real traffic.
- Verify dark: 404 (wrong path) / 405 (non-POST) / 413 (oversize) / 503 (`ENABLED=0`); import-firewall
  review; least-privilege R2 confirmed; no secret in code/logs.

## Hard boundaries for C-DEPLOY-DARK

- Deploy a Worker + bind R2 **only** — still **no** TradingView pointing at it, **no** Farouk-alert
  change, **no** manual POST yet (that's Gate D-MANUAL-POST).
- No broker/QST/execution/permit/lease/order; no gate change; no shadow engine; listener untouched.

## Gate sequence

`C-INSTALL ✅ → C-LOGIN ✅ → C-R2A ✅ → C-R2B ✅ (bucket) → C-DEPLOY-DARK (next — not authorised) →
D-MANUAL-POST → E-TRADINGVIEW-TEST`.

## What Martyn approves next

- **Gate C-DEPLOY-DARK** — author + deploy the logging-only Worker dark, bound to the bucket. Nothing
  is authored or deployed without that explicit approval. (This is the first gate that creates Worker
  source + `wrangler.toml`.)

**Until Gate C-DEPLOY-DARK is explicitly approved, nothing further happens.** `NOT_INTEGRATION_READY`
unchanged; the lane stays capture-only.
