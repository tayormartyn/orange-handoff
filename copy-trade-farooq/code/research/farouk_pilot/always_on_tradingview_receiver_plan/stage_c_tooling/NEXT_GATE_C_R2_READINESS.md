# Next Gate — C-R2 Readiness

**Mode: CLOUDFLARE LOGIN ONLY (this gate is complete).** Describes what **Gate C-R2** would involve.
**C-R2 is NOT started and NOT authorised here.**

## Prerequisites — met

- [x] Stage B PASS.
- [x] Gate C-INSTALL — Wrangler 4.107.1 local.
- [x] **Gate C-LOGIN — authenticated (OAuth).**

## What Gate C-R2 would do (later, only if approved)

- Create **one private R2 bucket** (no public access) for append-only event objects.
- Configure a **least-privilege binding** so the future Worker can only `put`/write to that one bucket.
- Confirm append-only object naming: `events/YYYY/MM/DD/<event_id>.jsonl` (keyed on unique `event_id`
  so `put` never overwrites).

## First sub-step of Gate C-R2 — verify R2 scope

Because the granted OAuth scopes did **not** show an explicit `r2` scope (see `GATE_C_LOGIN_RESULTS.md`):
1. Run a **read-only** check first: `wrangler r2 bucket list` (lists buckets; creates nothing).
2. If it works → proceed to create the private bucket (with approval).
3. If it's refused (missing R2 permission) → re-authenticate with an R2 scope, **or** switch to a
   **Cloudflare API token scoped to Workers + R2 only**. Decide before creating anything.

## Hard boundaries for C-R2 (when it runs)

- Private bucket only (no public access); least-privilege binding (write/put to the one bucket).
- Still **no** Worker deployed, **no** public endpoint, **no** TradingView config at C-R2.
- No broker/QST/execution/permit/lease/order; no gate change; no shadow engine; listener untouched.
- No secret committed; the receiver's future secret path lives in the Worker secret store, not the repo.

## Gate sequence from here

`C-INSTALL ✅ → C-LOGIN ✅ → C-R2 (next, not started) → C-DEPLOY-DARK → D-MANUAL-POST →
E-TRADINGVIEW-TEST` — each a separate explicit approval
(`../stage_c_preflight/STAGE_C_APPROVAL_GATES.md`).

## What Martyn approves next (the immediate decision)

- **Gate C-R2** — authorise the R2-scope check + private bucket creation (+ least-privilege binding).
  If the R2-scope check fails, decide between re-auth-with-R2 or a Workers+R2-scoped API token.

**Until Gate C-R2 is explicitly approved, nothing further happens.** `NOT_INTEGRATION_READY` remains
unchanged; the lane stays capture-only.
