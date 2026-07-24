# Dark Deployment — Operator Notes

**For the operator (Martyn). Capture-only infrastructure. No execution anywhere.**

## What exists now

- Worker `farouk-tv-webhook-logger-v1` — **deployed dark** (uploaded + bound to R2, **no public URL**).
- R2 bucket `farouk-tv-webhook-evidence-v1` — private, **empty**.
- Secret `TV_WEBHOOK_SECRET_PATH` — set on the Worker (value only in the gitignored local file).

## The one decision before Gate D — enable an endpoint

The Worker has **no reachable URL** because the account has **no workers.dev subdomain** yet. To give
it an endpoint (needed so TradingView — later — and the Gate D manual POST can reach it), choose one:

- **Option 1 — workers.dev subdomain (simplest):** register a subdomain once via the Cloudflare
  dashboard onboarding (dashboard → Workers → set up a `*.workers.dev` subdomain). ⚠️ This name is
  **account-global** (every Worker uses it), so it's your choice. Then set `workers_dev = true` and
  redeploy → the Worker gets `https://farouk-tv-webhook-logger-v1.<your-subdomain>.workers.dev`.
- **Option 2 — custom route/domain:** attach a route on a domain you control (more setup).
- **Option 3 — stay dark for now:** leave it unrouted; revisit when ready.

I will not register the subdomain or change routing without your explicit say-so.

## LOCAL SECRET file — handling

- `LOCAL_SECRET_webhook_path.txt` is **gitignored**. It contains the secret path + the eventual webhook
  URL template.
- **Do not commit it. Do not paste it into chat.** When the endpoint is enabled, the webhook URL is
  `https://<endpoint>/tv/<secret_path_value>` (from that file).
- To rotate: `wrangler secret put TV_WEBHOOK_SECRET_PATH` with a new value; update the local file; the
  old path then 404s.

## What must NEVER be added

- No broker/cTrader/QST credential, no account IDs, no lot/risk sizing, no trade instruction — not in
  the Worker, not in the payload, not in R2 objects.
- No `fetch()` to any trading host; the Worker's only outbound action is the R2 `put`.

## Gate status

- Gate C-DEPLOY-DARK: **done** (Worker deployed dark, bound, secret set, no endpoint).
- Next: **Gate D-MANUAL-POST** — but it requires an endpoint first (see the decision above). Gate D is
  **not started / not authorised**.
