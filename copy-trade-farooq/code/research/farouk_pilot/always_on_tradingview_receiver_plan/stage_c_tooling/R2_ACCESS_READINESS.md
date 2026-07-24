# R2 Access Readiness

**Mode: READ-ONLY R2 SCOPE CHECK ONLY.** Snapshot after Gate C-R2A **re-check**. No secret exposed.

## R2 status — UPDATED 2026-07-07 20:05 local: AVAILABLE ✅

| Item | Status |
|---|---|
| Wrangler auth | ✅ OAuth (Gate C-LOGIN) |
| R2 enabled on account | ✅ **yes** (Martyn enabled it manually in the dashboard) |
| R2 **usable** | ✅ **yes** — `wrangler r2 bucket list` returns exit 0 (empty list; no buckets yet) |
| Buckets present | none (0) — correct; none created |

_Prior first-run status (retained for record): R2 was **not usable** — Cloudflare error `10042`
"Please enable R2 through the Cloudflare Dashboard" (product not activated, **not** a scope issue).
That is now resolved._

## Interpretation

- The earlier "no explicit r2 scope in `whoami`" flag turned out **not** to be the blocker — the token
  reached R2 (no 403). The blocker is that **R2 has not been switched on for the account**.
- This is a common first-use step: R2 must be enabled once in the dashboard (accept terms; a payment
  method may be required even for the free tier) before any bucket can be listed or created.

## What is READY vs next

- ✅ Wrangler installed + authenticated; **R2 enabled and usable**.
- ✅ Read-only `wrangler r2 bucket list` succeeds (empty list).
- ▶️ **Gate C-R2B (bucket creation) can now be considered** — but is **NOT started / NOT authorised**.

## Path forward

1. ✅ R2 enabled (done by Martyn) and confirmed via the read-only re-check.
2. **Gate C-R2B (separately authorised)** would create **one private bucket** + a **least-privilege
   binding** (write/put to that one bucket only), with append-only naming
   `events/YYYY/MM/DD/<event_id>.jsonl`. Still no Worker, no endpoint, no TradingView config at C-R2B.
3. Nothing is created without explicit Gate C-R2B approval.

## Security note

- No token/secret printed or stored in project files. The Account ID (`7173…43ad`) is an identifier,
  masked here as a courtesy; it is not a secret.
- No bucket, Worker, config, or endpoint exists. Nothing was created by the check.
