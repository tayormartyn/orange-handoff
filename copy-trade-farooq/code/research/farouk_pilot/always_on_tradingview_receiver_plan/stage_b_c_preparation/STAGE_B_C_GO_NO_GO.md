# Stage B/C — GO / NO-GO

**Mode: PREPARATION ONLY.** Gate criteria for advancing. Nothing here deploys anything; it defines
when each step *may* proceed, subject to Martyn's explicit authorisation.

## Current position

- Approved direction: **Cloudflare Workers + R2**, append-only raw-first, IP omitted by default,
  logging-only, `NOT_INTEGRATION_READY` unchanged, no production Farouk webhooking yet.
- Stage B/C **preparation documents:** COMPLETE (this folder).
- Deployed/exposed anything: **NO.**
- Telegram PREVIEW listener (PID 40416): **running, untouched.**

## Stage B — Local unit test → GO criteria

**GO when:**
- [ ] Test cases B1–B10 (`STAGE_B_LOCAL_UNIT_TEST_PLAN.md`) all pass locally (Python oracle, and/or
  local Worker harness bound to localhost — no exposure).
- [ ] Invariants green: no broker/QST/execution path; no permits/leases/orders; gates
  `PAPER/PREVIEW/False/False`; raw captured; UTC; dedupe; no TradingView involved; listener untouched.
- [ ] Martyn authorises running Stage B.

**NO-GO if:** any test fails, any invariant red, or authorisation absent. Fix + re-run; never proceed
on a red.

## Stage C — Private/unconfigured deployment → GO criteria

**GO when:**
- [ ] Stage B is GO (all green).
- [ ] Martyn **separately authorises deployment** (Stage C does not self-authorise).
- [ ] Cloudflare account ready; R2 bucket plan + least-privilege binding defined.
- [ ] Secret path + env prepared per the env-vars doc (never committed/logged).
- [ ] The deployment checklist (`STAGE_C_PRIVATE_DEPLOYMENT_CHECKLIST.md`) is followed exactly, and
  **no TradingView alert points at the Worker** (it stays dark).

**NO-GO if:** Stage B not green, no separate deploy authorisation, or any safety check (import
firewall, least-privilege R2, no secret in code/logs, `ENABLED=0`→503) fails.

## Hard stops (apply to both stages)

- ❌ No public endpoint wired to TradingView.
- ❌ No Farouk production alert changed.
- ❌ No QST/broker/cTrader; no permit/lease/order; no execution-gate change; no shadow engine.
- ❌ No deploy in Stage B; no real traffic in Stage C.
- 🔒 Telegram PREVIEW listener untouched.

## What is explicitly deferred (needs its own authorisation)

- Stage D (manual POST to cloud), Stage E (harmless TV alert → cloud), Stages F–H (Farouk mirroring),
  Stage I (reports), Stage J (shadow). Each is separately gated per `ALWAYS_ON_VALIDATION_ROLLOUT.md`.

## Decision record (to be filled at execution time)

- Stage B run date / result: ______
- Stage C deploy authorised (Y/N) / date: ______
- Worker + bucket names, secret-path fingerprint (hash), region: ______
