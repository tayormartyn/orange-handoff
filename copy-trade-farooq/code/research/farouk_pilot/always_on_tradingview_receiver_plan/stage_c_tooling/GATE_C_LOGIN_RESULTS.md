# Gate C-LOGIN — Results

**Run:** 2026-07-07 19:45 local (Italy UTC+1). **Mode: CLOUDFLARE LOGIN ONLY.**
No deploy, no Worker, no R2 bucket, no route, no public endpoint, no TradingView config, no Farouk-alert
edit, no broker/QST/execution/permit/lease/order, no gate change, no shadow engine. Telegram PREVIEW
listener (PID 40416) untouched. **No token/secret printed or saved to any project file.**

## What was done

- Martyn ran the interactive login himself in his own session (via the `!` prefix), using the **local**
  Wrangler install: `npx wrangler login` from `stage_c_tooling/`.
- The browser OAuth flow completed → wrangler reported **"Successfully logged in."**
- I then ran only a **read-only** identity check: `wrangler whoami`.

> The first (background) attempt timed out — an interactive browser OAuth flow can't complete from a
> non-interactive background shell. Martyn's interactive-session run succeeded.

## Result

| Item | Value |
|---|---|
| Login | **Succeeded** (OAuth) |
| Auth type | OAuth token (browser flow) |
| Account identity | **"&lt;redacted-email&gt;'s Account"** (email redacted) |
| Account ID | confirmed — masked `7173…43ad` (identifier, not a secret) |
| Credentials stored at | `…\AppData\Roaming\xdg.config\.wrangler\config\default.toml` (801 bytes) — **NOT read/printed** |
| Token printed/saved in project files | **No** |

## Granted OAuth scopes (from `whoami`)

Broad wrangler default set: account(read), user(read), **workers(write)**, workers_kv(write),
workers_routes(write), workers_scripts(write), workers_tail(read), d1(write), pages(write), zone(read),
ssl_certs(write), ai/ai-search, queues, pipelines, secrets_store, artifacts, containers, cloudchamber,
connectivity(admin), email_routing/sending, browser, offline_access.

### ⚠️ Scope caveat for the next gate (R2)

- The `whoami` scope list does **not** show an explicit **`r2`** scope. The always-on receiver needs an
  **R2 bucket** (Gate C-R2). **Before/at Gate C-R2, verify R2 access works** with this OAuth token.
- If R2 operations are refused, options are: (a) re-authenticate with an R2 scope, or (b) use a
  **Cloudflare API token scoped to Workers + R2 only** (the tighter-scope route previously offered).
- This is a **readiness flag**, not a blocker for Gate C-LOGIN itself — login succeeded.

## Not created / not touched (correct for Gate C-LOGIN)

- ❌ No Worker, no R2 bucket, no route, no public endpoint, no deploy.
- ❌ No `wrangler.toml`, no `src/` Worker source, no `.dev.vars`.
- ❌ No TradingView config / Farouk-alert edit.
- ❌ No broker/cTrader/QST; no permit/lease/order; no gate change; no shadow engine.
- ✅ Telegram PREVIEW listener PID 40416 running, untouched.

## Next

Gate **C-R2** (create the private R2 bucket + least-privilege binding) can be **considered** next but is
**NOT started** and **NOT authorised** here. See `NEXT_GATE_C_R2_READINESS.md`.
