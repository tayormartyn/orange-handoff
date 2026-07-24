# Stage C — Next Decision

**Mode: PREFLIGHT ONLY.** Nothing installed, logged in, created, or deployed. This is the decision
point after Martyn reviews the Stage C preflight.

## Where we are

- Stage B: **PASS 10/10** — always-on receiver logic locally proven; report-time dedupe default;
  append-only/lossless ingest.
- Toolchain: node ✅, npm ✅, git ✅, **wrangler ❌ (absent)**.
- Cloudflare project config: **none exists** (clean slate).
- Deployment / public endpoint / TradingView config: **none**.
- Telegram PREVIEW listener (PID 40416): **untouched**.
- `NOT_INTEGRATION_READY`: **unchanged** (capture-only).

## What this preflight authorises

- **Only the writing of these Stage C preflight documents.** No install, no login, no bucket, no
  Worker, no deploy, no endpoint, no TradingView change.

## The immediate decision for Martyn

Pick the deploy route, then approve the **first** gate:

- **Route 1 — wrangler CLI:** approve **Gate C-INSTALL** (install wrangler, scoped to an isolated
  Worker project) → then C-LOGIN → C-R2 → C-DEPLOY-DARK.
- **Route 2 — Cloudflare dashboard:** skip C-INSTALL; approve **Gate C-LOGIN** (account access) →
  create Worker + R2 in the dashboard → C-R2 → C-DEPLOY-DARK.

Either way, the sequence stays gated: **C-INSTALL/C-LOGIN → C-R2 → C-DEPLOY-DARK → D-MANUAL-POST →
E-TRADINGVIEW-TEST**, each a separate explicit approval (`STAGE_C_APPROVAL_GATES.md`).

## Recommended path

1. Approve **Gate C-INSTALL** (or choose the dashboard route).
2. Approve **Gate C-LOGIN**.
3. Approve **Gate C-R2** (private bucket, least-privilege binding).
4. Approve **Gate C-DEPLOY-DARK** (Worker deployed dark — no TradingView pointing at it).
5. Verify dark (404/405/413/503, import firewall, least-privilege R2), record the deploy.
6. Later, separately: **D-MANUAL-POST**, then **E-TRADINGVIEW-TEST** (one harmless test alert).

## Final answer (restated)

1. **wrangler installed?** No — absent (node/npm/git present).
2. **Cloudflare project config exists?** No — clean slate (no wrangler.toml/.dev.vars/Worker/R2 refs;
   the one `package.json` is an unrelated TS package with no Cloudflare deps).
3. **Any deployment?** No.
4. **Any public endpoint created?** No.
5. **Any TradingView config?** No.
6. **Broker/QST/execution untouched?** Yes — untouched; no such imports anywhere in this lane.
7. **Telegram listener untouched?** Yes — PID 40416 running, untouched.
8. **What Martyn must approve next:** the deploy route + **Gate C-INSTALL** (install wrangler) — or
   **Gate C-LOGIN** if going the dashboard route. Nothing proceeds without that explicit approval.

## Document set (this preflight)

`STAGE_C_PREFLIGHT_REPORT.md` · `TOOLCHAIN_READINESS.md` · `CLOUDFLARE_RESOURCE_REQUIREMENTS.md` ·
`DARK_DEPLOYMENT_CHECKLIST.md` · `STAGE_C_APPROVAL_GATES.md` · `STAGE_C_RISKS_AND_ROLLBACK.md` ·
`STAGE_C_NEXT_DECISION.md`
