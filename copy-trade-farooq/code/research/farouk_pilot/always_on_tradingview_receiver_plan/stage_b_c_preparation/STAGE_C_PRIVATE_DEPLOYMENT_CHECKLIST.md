# Stage C — Private / Unconfigured Cloud Receiver — Deployment Checklist

**Mode: PREPARATION ONLY.** This is the **checklist to be executed later, only if separately
authorised.** Writing it deploys nothing. **Do not deploy, do not expose a public endpoint, do not
point any TradingView alert at it, do not change any Farouk alert** as part of Stage C. Telegram
PREVIEW listener (PID 40416) untouched.

## Purpose of Stage C

Have a **deployed but effectively-dark** cloud receiver: the Worker exists with its secret path set,
but **no TradingView alert points at it**, so it receives no real traffic. It answers probes correctly
(404/405) and its safety properties are verified. This de-risks Stage D (manual POST) and beyond.

## Pre-deploy gates (all must be true before Stage C runs)

- [ ] Stage B unit tests all green (`STAGE_B_LOCAL_UNIT_TEST_PLAN.md`).
- [ ] Martyn has **separately authorised deployment** (this checklist does not self-authorise).
- [ ] Provider account chosen (Cloudflare) and Martyn controls it.
- [ ] Secret path + secrets prepared per `SERVERLESS_RECEIVER_ENVIRONMENT_VARIABLES.md` (never
  committed, never logged).

## Deployment checklist (execute later, in order)

1. [ ] **Create the R2 bucket** (private; no public access) for append-only event objects.
2. [ ] **Author the Worker** in LOGGING_ONLY: POST-only, exact secret path, body cap, raw-first,
   UTC stamp, safe-header whitelist, parse (read-only), event_id + dedupe, append-only R2 write,
   `ENABLED` flag, import firewall. (Logic == Stage B oracle.)
3. [ ] **Bind** the Worker to the R2 bucket with a **least-privilege** binding (write/append to this
   bucket only; no other permission).
4. [ ] **Set secrets** as Worker secrets/env (not in code): `TV_WEBHOOK_SECRET_PATH`,
   `TV_WEBHOOK_ENABLED`, optional `TV_WEBHOOK_MAX_BODY`. (See env-vars doc.)
5. [ ] **Deploy** to a Worker URL, but **do NOT put the URL into any TradingView alert.** It stays
   unconfigured/dark.
6. [ ] **Disable/omit any dev preview** that would expose a guessable URL; rely on the secret path.
7. [ ] **Probe verification (no real data):**
   - [ ] `GET /` and `GET /<secret path>` → 405.
   - [ ] `POST /<wrong path>` → 404.
   - [ ] `POST /<secret path>` oversize → 413.
   - [ ] `POST /<secret path>` valid (manual, Stage D) → 200 ACCEPTED, one R2 object. *(Stage D step,
     listed here for continuity — not part of Stage C's dark verification.)*
8. [ ] **Safety verification:**
   - [ ] Worker source imports nothing broker/cTrader/QST/execution/permit (grep + review).
   - [ ] R2 binding is append/write-only to its own bucket; no other cloud permission.
   - [ ] No secret in code or logs; secret only in Worker secret store + the (future) alert URL.
   - [ ] `ENABLED=false` returns 503.
9. [ ] **Record** the deploy: Worker name, bucket name, region, secret-path fingerprint (hash, not the
   secret), deploy time (UTC) — into a Stage C results doc.

## Explicit NON-actions in Stage C

- ❌ No TradingView alert points at the Worker.
- ❌ No Farouk production alert changed.
- ❌ No public/guessable endpoint beyond the secret path.
- ❌ No broker/QST/execution/permit/lease/order; no gate change; no shadow engine.

## Rollback

- Delete the Worker → endpoint gone. Delete/disable the R2 bucket → storage gone. Rotate the secret
  path → old URL 404s. Any one is a complete, immediate stop.

## Exit criteria (Stage C → Stage D)

Worker deployed dark, all probe + safety checks green, deploy recorded, and Martyn's explicit
"proceed to Stage D (manual POST)." Real TradingView traffic does not begin until Stage E, gated.
