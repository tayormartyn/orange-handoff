# Cloudflare Auth Readiness

**Mode: CLOUDFLARE LOGIN ONLY.** Post-login readiness snapshot. No secret exposed.

## Authenticated

| Item | Status |
|---|---|
| Wrangler | 4.107.1 (local devDependency) |
| Login | ✅ authenticated (OAuth token) |
| Account | "&lt;redacted-email&gt;'s Account" (email redacted) |
| Account ID | masked `7173…43ad` |
| Credential store | `…\.wrangler\config\default.toml` (managed by wrangler; **not** read/committed) |

## Ready for (future, gated) actions

With this authenticated session, wrangler could later — **only under their own gates** —:
- create/bind an **R2 bucket** (**Gate C-R2**) — *pending R2-scope verification, see caveat*,
- deploy a **Worker dark** (**Gate C-DEPLOY-DARK**),
- send manual POSTs to the deployed URL (**Gate D-MANUAL-POST**).

None of these is done or authorised here.

## R2 scope — verify before Gate C-R2

The granted OAuth scopes (from `whoami`) include `workers(write)` and many others, but **no explicit
`r2` scope was listed**. Action for Gate C-R2:
1. First attempt a **read-only R2 check** (e.g. `wrangler r2 bucket list`) to see whether the token can
   access R2.
2. If refused → re-auth with R2 scope, or switch to a **Workers+R2-scoped API token**.
3. Only then create the private bucket.

## Security posture

- **No token printed or saved** to any project file. The OAuth token lives only in wrangler's own
  credential store (`default.toml`), which is **not** in the repo and **not** read by these reports.
- `.gitignore` in `stage_c_tooling/` already excludes `node_modules/`, `.dev.vars`, `.wrangler/`.
- The secret path for the receiver (a separate future secret) does **not** exist yet and will never be
  committed — it will live in the Worker secret store at deploy time.

## Readiness verdict

**Authenticated and ready for Gate C-R2 consideration**, with the **R2-scope verification** as the first
sub-step of that gate. Nothing proceeds without explicit **Gate C-R2** approval.
