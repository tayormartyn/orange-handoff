# R2 Bucket — Evidence Storage Record

**Created:** 2026-07-07 (Gate C-R2B). **Mode: R2 BUCKET CREATION ONLY.** Record of the append-only
evidence bucket for the always-on TradingView logging-only receiver.

## Bucket

| Field | Value |
|---|---|
| Name | **`farouk-tv-webhook-evidence-v1`** |
| Provider | Cloudflare R2 |
| Storage class | Standard |
| Created (UTC) | 2026-07-07T19:10:22Z |
| Account ID | masked `7173…43ad` (identifier, not a secret) |
| Public access | **No** (private by default; no public domain/binding configured) |
| Objects | **0** (empty; no uploads yet) |
| Worker binding | **Not yet** (deferred to Gate C-DEPLOY-DARK) |

## Intended use (future, gated)

- Store **append-only raw TradingView webhook evidence objects** written by the future logging-only
  Worker.
- **Planned object naming:** `events/YYYY/MM/DD/<event_id>.jsonl` — one object per event, keyed on the
  unique `event_id` so `put` never overwrites an existing object (append-only guarantee).
- Each object body = the single JSON record whose `raw_payload` field holds the byte-exact TradingView
  body, plus parsed metadata (per `../ALWAYS_ON_STORAGE_SCHEMA_v0.1.md`).

## Must-never (by design)

- ❌ No broker/QST/execution data.
- ❌ No credentials/secrets/account tokens.
- ❌ No public access / public URL.
- ❌ No trade instruction, no sizing, no account IDs in stored objects.
- ❌ No update/delete of objects (append-only; `put` keyed on unique `event_id`).

## Binding (to be set at Gate C-DEPLOY-DARK, not now)

- Suggested binding name (from wrangler's snippet, **not applied**): `farouk_tv_webhook_evidence_v1`.
- At deploy time the Worker will get a **least-privilege** binding: write/put to **this one bucket
  only**, no other cloud permission. Recorded here for planning; **no `wrangler.toml` exists yet.**

## Status

Bucket exists, private, empty, unbound. It holds nothing until the Worker is deployed (Gate
C-DEPLOY-DARK) and, later, real events arrive (Gate E onward). `NOT_INTEGRATION_READY` unchanged.
