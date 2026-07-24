# Always-On Receiver — Next Decision (§9)

**DESIGN ONLY.** Nothing here is built or deployed. This is the decision path after Martyn reviews the
plan.

## What this plan authorises

- **Only the writing of these design documents.** No receiver, no cloud resource, no endpoint, no
  tunnel, no TradingView change has been created. The Telegram PREVIEW listener (PID 40416) is
  untouched.

## The decision Martyn needs to make

1. **Approve the option:** serverless function + managed append-only store (Option A) — or the
   equal-footing edge-worker variant (Option C), or a VPS (Option B) if a full host is wanted.
2. **Pick the provider** he already trusts/uses (the design is provider-agnostic; the choice
   determines the exact deploy mechanics).
3. **Confirm the storage backend:** append-only JSONL object storage (recommended) or a managed
   table/KV keyed on `event_id`.
4. **Authorise the first build stages only:** **Stage B (local unit test)** and **Stage C (deploy
   private/unconfigured cloud receiver)**. Nothing gets a TradingView webhook until Stage E+, each
   explicitly gated.

## Recommended path (if proceeding)

1. Approve Option A + provider + JSONL storage.
2. **Stage B** — build + local unit test (POST-only, secret path, raw-first, append-only, dedupe,
   import firewall). No cloud, no TradingView.
3. **Stage C** — deploy the function private/unconfigured; verify 404/405 to probes, import firewall,
   least-privilege storage. No real traffic.
4. **Stage D** — manual POSTs to the cloud secret URL; verify capture + dedupe.
5. **Stage E** — one harmless TradingView test alert → cloud receiver; verify capture + app
   notification; delete the test alert.
6. **Stages F→H** — duplicate Farouk-style test → one real Farouk alert (app on) → full set in
   batches, each gated + reversible.
7. **Stage I** — read-only parser/deduper report.
8. **Stage J** — shadow comparison, later, separate authorisation.

## Final answer (restated)

1. **Recommended always-on option:** serverless function + managed append-only store (Option A).
2. **Why fastest & safest:** 24/7 capture, smallest standing surface, ~zero cost, trivial rollback,
   reuses the Stage-2-proven PATH_ONLY / raw-first / append-only / UTC contract.
3. **What remains prohibited:** no broker/cTrader/QST; no execution module; no permit/lease/order; no
   execution-gate change; no TradingView→broker path; no live or demo trading from a webhook; no
   execution from A+/A+++/CHoCH/Sweep/BPR; no credentials/account IDs/lot/risk in the payload.
4. **Anything built or deployed?** No — design documents only.
5. **Is Stage 2 still capture-only?** Yes.
6. **Does `NOT_INTEGRATION_READY` remain unchanged?** Yes, unchanged.
7. **What Martyn should approve next:** the option + provider + storage, then authorise Stage B and
   Stage C only. Nothing touches a TradingView webhook until the later, individually-gated stages.

## Document set

`ALWAYS_ON_TV_RECEIVER_PLAN_v0.1.md` · `DEPLOYMENT_OPTIONS_COMPARISON.md` ·
`RECOMMENDED_FIRST_IMPLEMENTATION.md` · `ALWAYS_ON_RECEIVER_SAFETY_SPEC_v0.1.md` ·
`ALWAYS_ON_STORAGE_SCHEMA_v0.1.md` · `ALWAYS_ON_SECURITY_MODEL.md` ·
`TRADINGVIEW_ALERT_MIRRORING_PLAN.md` · `ALWAYS_ON_VALIDATION_ROLLOUT.md` ·
`TELEGRAM_TV_ALIGNMENT_ARCHITECTURE.md` · `ALWAYS_ON_HARD_VETOES.md` · `ALWAYS_ON_NEXT_DECISION.md`
