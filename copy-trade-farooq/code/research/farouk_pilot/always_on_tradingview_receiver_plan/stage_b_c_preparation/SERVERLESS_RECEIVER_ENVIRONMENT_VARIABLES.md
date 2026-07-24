# Serverless Receiver — Environment Variables & Secrets

**Mode: PREPARATION ONLY.** Lists what a *future* deployment would need. **No real values here** — all
are placeholders/descriptions. No secret is generated, stored, or committed by this document.

## Principles

- Secrets live in the **Worker secret store** (e.g. `wrangler secret put`), **never** in code, never
  in the repo, never in logs.
- The **only** auth secret is the **path segment**. There is **no** broker/API/account credential in
  this lane — by design there is nothing of that kind to store.
- Bindings (R2) are configured in the Worker config, least-privilege.

## Required

| Name | Type | Purpose | Notes |
|---|---|---|---|
| `TV_WEBHOOK_SECRET_PATH` | secret | the long random path segment; endpoint = `/tv/<value>` | ≥ 32 bytes URL-safe (`secrets.token_urlsafe(32+)`); rotates on leak; never in query string or body |
| `TV_WEBHOOK_ENABLED` | var | soft kill switch (`"1"` on / `"0"` off) | `"0"` → Worker returns 503 + logs the hit |
| **R2 binding** (e.g. `EVENTS`) | binding | append-only event storage | least-privilege: write/put to this one bucket only; no other permission |

## Optional

| Name | Type | Purpose | Notes |
|---|---|---|---|
| `TV_WEBHOOK_MAX_BODY` | var | body size cap in bytes | default 65536 (64 KB) |
| `TV_WEBHOOK_RATE_LIMIT` | var/binding | per-path/IP burst cap | if platform rate-limiting is used |
| `TV_WEBHOOK_SCHEMA_VERSION` | var | tag stored on records | e.g. `tv-webhook-0.1` |

## Explicitly NOT present (must never exist in this lane)

- ❌ No broker/cTrader API key, client id, or secret.
- ❌ No QST credential.
- ❌ No account id / login.
- ❌ No `EXECUTION_ENABLED` / order/permit/lease config — this lane has no execution surface at all.
- ❌ No secret in the URL query string; none in the alert body.

## Handling

- Generate `TV_WEBHOOK_SECRET_PATH` locally with a CSPRNG; set it via the Worker secret store; record
  only its **fingerprint (hash)** in any results doc, never the value.
- On suspected leak: rotate (new secret path), update the few mirrored alert URLs, retire the old path
  (it 404s). See `ALWAYS_ON_RECEIVER_ROTATION_AND_KILL_SWITCH_SPEC.md`.
- `.gitignore` any local `.dev.vars` / wrangler secret files so nothing lands in the repo.
