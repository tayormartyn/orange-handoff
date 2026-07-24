# Always-On TradingView Logging Receiver — Master Plan v0.1

**Mode: DESIGN ONLY / NO BUILD.** No code, no deploy, no public URL, no cloudflared, no receiver
start, no TradingView change, no Farouk-alert edit, no QST/broker/cTrader, no permit/lease/order, no
execution-gate change, no shadow engine, no touching the Telegram PREVIEW listener (PID 40416).

## Why this milestone

Stage 2 **proved** the logging-only webhook lane end-to-end (TradingView → tunnel → local receiver,
PATH_ONLY auth, JSON parsed, placeholders resolved, **UTC** timestamps). Its **one limitation**: the
local receiver + manual tunnel only capture **while the laptop is awake/online.** An always-on
cloud/serverless receiver closes that gap so TradingView Farouk alerts are captured **24/7, even when
the laptop is off** — still **capture/observation only**, never execution.

## What carries over from Stage 2 (proven)

- **PATH_ONLY secret-path auth** works with real TradingView (no custom header needed).
- **JSON payload parses**; placeholders `{{ticker}} {{exchange}} {{interval}} {{close}} {{time}}
  {{timenow}}` resolve; `{{time}}`/`{{timenow}}` are **UTC (`Z`)**.
- Raw-first, append-only storage; ~1s delivery latency.
- **Verdict unchanged: `NOT_INTEGRATION_READY`.** This lane never changes that.

## The design, in one line

An always-on, internet-reachable, **logging-only** HTTPS endpoint that accepts a **POST to one long
random secret path**, stores the **raw payload byte-exact + received_at_utc + safe headers + parsed
metadata** to **append-only** storage, dedupes, and does **nothing else** — no engine, no broker, no
QST, no outbound trading call, ever.

## Document set (this plan)

| File | Covers |
|---|---|
| `ALWAYS_ON_TV_RECEIVER_PLAN_v0.1.md` | this master plan + final answer |
| `DEPLOYMENT_OPTIONS_COMPARISON.md` | §1 — A serverless / B VPS / C managed worker / D local-only |
| `RECOMMENDED_FIRST_IMPLEMENTATION.md` | §2 — the pick + receiver invariants |
| `ALWAYS_ON_RECEIVER_SAFETY_SPEC_v0.1.md` | receiver hard controls |
| `ALWAYS_ON_STORAGE_SCHEMA_v0.1.md` | §3 — fields + storage-backend comparison |
| `ALWAYS_ON_SECURITY_MODEL.md` | §4 — auth, rotation, kill switch, audit |
| `TRADINGVIEW_ALERT_MIRRORING_PLAN.md` | §5 — how to add webhooks to Farouk alerts LATER |
| `ALWAYS_ON_VALIDATION_ROLLOUT.md` | §6 — Stages A→J |
| `TELEGRAM_TV_ALIGNMENT_ARCHITECTURE.md` | §7 — how it sits beside the Telegram lane |
| `ALWAYS_ON_HARD_VETOES.md` | §8 — non-negotiable vetoes |
| `ALWAYS_ON_NEXT_DECISION.md` | §9 — what Martyn approves next |

## Final answer (the seven questions)

1. **Recommended always-on option:** **Option A — a serverless function endpoint + managed
   append-only storage** (see `RECOMMENDED_FIRST_IMPLEMENTATION.md`).
2. **Why fastest & safest:** no server to run/patch (smallest standing attack surface), 24/7 capture
   with effectively zero cost at a few events/day, HTTPS + secret path built in, trivial rollback
   (delete the function), and it reuses the exact Stage-2-proven contract (PATH_ONLY, raw-first,
   append-only, UTC).
3. **What remains prohibited:** any broker/cTrader/QST connection; any execution module; any
   permit/lease/order; any execution-gate change; any TradingView→broker path; any live-money or
   demo trading from a webhook; any execution from A+/A+++/CHoCH/Sweep/BPR; any credentials/account
   IDs/lot/risk sizing in the payload. See `ALWAYS_ON_HARD_VETOES.md`.
4. **Anything built or deployed?** **No.** Design documents only. Nothing built, deployed, exposed, or
   configured. No process started; the Telegram listener (PID 40416) untouched.
5. **Is Stage 2 still capture-only?** **Yes** — Stage 2 was and remains logging/observation only, and
   the always-on lane is designed to be the same.
6. **Does `NOT_INTEGRATION_READY` remain unchanged?** **Yes, unchanged.** Capture ≠ readiness.
7. **What Martyn approves next (if proceeding):** approve the **serverless option + provider choice**,
   then authorise **Stage B (local unit test)** and **Stage C (deploy private/unconfigured cloud
   receiver)** — nothing gets a TradingView webhook until later stages, each explicitly gated. See
   `ALWAYS_ON_NEXT_DECISION.md`.
