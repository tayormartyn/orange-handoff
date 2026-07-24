# Next Gate — C-LOGIN Readiness

**Mode: TOOLCHAIN INSTALL ONLY (this gate is complete).** This document describes what **Gate
C-LOGIN** would involve. **C-LOGIN is NOT started and NOT authorised here.**

## Prerequisites — met

- [x] Stage B PASS (10/10).
- [x] Stage C preflight complete.
- [x] **Gate C-INSTALL done** — Wrangler 4.107.1 installed locally; no login; no resources.

## What Gate C-LOGIN would do (later, only if approved)

- Authenticate Wrangler to a Cloudflare account **Martyn controls**, via **one** of:
  - `wrangler login` (OAuth in the browser — interactive; Martyn performs the login), **or**
  - a Cloudflare **API token scoped to Workers + R2 only** provided as an env var.
- Nothing else — no bucket, no Worker, no deploy. C-LOGIN only establishes account access.

## Hard boundaries for C-LOGIN (when it eventually runs)

- Scope the token/permissions to **Workers + R2 only** (no other Cloudflare product access).
- No secret committed to the repo; token via env/secret store only.
- Still **no** R2 bucket, Worker, public endpoint, or TradingView config at C-LOGIN.
- No broker/QST/execution/permit/lease/order; no gate change; listener untouched.

## Gate sequence from here

`C-INSTALL ✅ → C-LOGIN (next, not started) → C-R2 → C-DEPLOY-DARK → D-MANUAL-POST →
E-TRADINGVIEW-TEST` — each a separate explicit approval
(`../stage_c_preflight/STAGE_C_APPROVAL_GATES.md`).

## What Martyn approves next (the immediate decision)

- **Gate C-LOGIN** — authorise Cloudflare account access (OAuth login or a Workers+R2-scoped token).
  Because `wrangler login` is an **interactive browser** step, Martyn would perform it himself when
  authorised; I would not store any new secret without explicit instruction.

**Until Gate C-LOGIN is explicitly approved, nothing further happens.** `NOT_INTEGRATION_READY`
remains unchanged; the lane stays capture-only.
