# Stage C — Toolchain Readiness

**Mode: PREFLIGHT ONLY.** Read-only discovery on 2026-07-07. Nothing installed, logged in, or run.

## Tools present (read-only version check)

| Tool | Status | Version | Path |
|---|---|---|---|
| node | ✅ present | v24.16.0 | `C:\Program Files\nodejs\node` |
| npm | ✅ present | 11.13.0 | `C:\Program Files\nodejs\npm` |
| git | ✅ present | 2.50.1 (windows) | `/mingw64/bin/git` |
| **wrangler** | ❌ **absent** | — | not on PATH; not in project `node_modules` |

## Interpretation

- **Node + npm are ready** — sufficient runtime to install and run wrangler later.
- **wrangler is NOT installed** — required for a Cloudflare Workers + R2 deploy (or use the Cloudflare
  dashboard). Installing it is **Gate C-INSTALL** (separately authorised; not done here).
- **git present** — available if the Worker source is version-controlled later (optional).

## No existing Cloudflare project config

Searched the project (excluding venvs/site-packages):

- `wrangler.toml` / `wrangler.jsonc` — **none**.
- `.dev.vars` / dev-vars files — **none**.
- Worker source folder — **none**.
- R2 bucket references — **none** (text hits were false positives: a `r2.db` test variable in
  `campaign_extractor/mpk/tests/` and `r2` in `test_price_foundation.py`, plus the plan/monitoring
  docs mentioning `cloudflared`/Cloudflare narratively).
- `package.json` — only `packages/alpha-contracts/package.json`, an unrelated TypeScript contracts
  package with **no** Cloudflare/wrangler/Worker/R2 dependency.

**Conclusion:** the project has **no** Cloudflare/Worker/R2 configuration today — a clean slate. A
future Stage C would create all of it from scratch, under explicit gates.

## What is needed before Stage C could run (not done now)

1. A Cloudflare account Martyn controls (**Gate C-LOGIN**).
2. wrangler installed **or** deploy via the Cloudflare dashboard (**Gate C-INSTALL** if using
   wrangler).
3. An R2 bucket + least-privilege binding (**Gate C-R2**).
4. Secret path + kill-switch env prepared (never committed/logged).

All of the above are **future, separately-authorised** steps. This document only records readiness.
