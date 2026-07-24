# Stage C — Dark Deployment Checklist

**Mode: PREFLIGHT ONLY.** This checklist is to be **executed later, only if each gate is approved.**
Writing it deploys nothing. "Dark" = the Worker exists but **no TradingView alert points at it** and it
receives no real traffic.

## Pre-conditions (all must hold before Stage C executes)

- [ ] Stage B PASS (done — 10/10).
- [ ] **Gate C-INSTALL** approved (if using wrangler; else deploy via dashboard).
- [ ] **Gate C-LOGIN** approved (Cloudflare account access).
- [ ] **Gate C-R2** approved (bucket creation).
- [ ] **Gate C-DEPLOY-DARK** approved (deploy the Worker dark).
- [ ] Secret path + kill-switch env prepared locally (never committed/logged).

## Cloudflare account

- [ ] Confirm Martyn's Cloudflare account is ready (free tier OK).
- [ ] Auth via `wrangler login` (OAuth) or a Workers+R2-scoped API token. **No login in preflight.**

## wrangler install (only if missing — it is)

- [ ] Install wrangler (e.g. as a dev dependency in an isolated Worker project folder) — **Gate
  C-INSTALL**. Do **not** install globally without cause; keep it scoped to the Worker project.
- [ ] `.gitignore` any local secret/dev-vars files.

## R2 bucket

- [ ] Create a **private** R2 bucket (no public access) — **Gate C-R2**.
- [ ] Bind it to the Worker with a **least-privilege** binding (write/put to this bucket only).
- [ ] Confirm append-only object naming: `events/YYYY/MM/DD/<event_id>.jsonl`, keyed on unique
  `event_id` (put never overwrites).

## Worker secrets / vars

- [ ] `TV_WEBHOOK_SECRET_PATH` — set as a Worker **secret** (generated locally via CSPRNG; record only
  its hash fingerprint in results, never the value).
- [ ] `TV_WEBHOOK_ENABLED` = `"1"` (kill switch; `"0"` → 503).
- [ ] `TV_WEBHOOK_MAX_BODY` = `65536` (64 KB) — optional.

## Worker source (logic == Stage B oracle)

- [ ] LOGGING_ONLY handler: POST-only; exact secret path (constant-time); body cap; raw-first;
  UTC stamp; safe-header whitelist; parser-only; event_id; append-only R2 write; `ENABLED` flag.
- [ ] **No broker/QST/execution imports.** Cold-start import firewall (fail-closed). No `fetch()` to
  any trading host — only the R2 write.
- [ ] Fail-closed on R2 write error (return 5xx, never accept-without-store).
- [ ] Health check returns static `200 {"ok":true}` with no secret/data; does not accept bodies.

## Deploy dark

- [ ] `wrangler deploy` (or dashboard) — **Gate C-DEPLOY-DARK**.
- [ ] **Do NOT put the Worker URL into any TradingView alert.** It stays dark.
- [ ] **No Farouk production alert changed.**

## Dark verification (no real data)

- [ ] `GET /` and `GET /<secret path>` → 405.
- [ ] `POST /<wrong path>` → 404.
- [ ] `POST /<secret path>` oversize → 413.
- [ ] `TV_WEBHOOK_ENABLED=0` → 503; restore to `1`.
- [ ] Worker source review + grep: no broker/cTrader/QST/execution/permit import; only R2 outbound.
- [ ] R2 binding is write-only to its own bucket; no other permission.
- [ ] No secret in code or logs; secret only in Worker secret store.

## Record the dark deploy (results doc, later)

- [ ] Worker name, R2 bucket name, region, secret-path **fingerprint (hash, not value)**, deploy time
  (UTC). No live TradingView traffic yet.

## Explicit NON-actions in Stage C

- ❌ No TradingView alert points at the Worker (it stays dark).
- ❌ No Farouk production alert changed.
- ❌ No manual POST *from TradingView* — first real POST is **Gate D-MANUAL-POST** (a hand-crafted
  POST by Martyn/us), then **Gate E** for a harmless TradingView test alert.
- ❌ No broker/QST/cTrader; no permit/lease/order; no execution-gate change; no shadow engine.

## Rollback (any one = complete stop)

- Delete the Worker → endpoint gone.
- Delete/disable the R2 bucket → storage gone.
- Set `TV_WEBHOOK_ENABLED=0` → 503.
- Rotate `TV_WEBHOOK_SECRET_PATH` → old URL 404s.
