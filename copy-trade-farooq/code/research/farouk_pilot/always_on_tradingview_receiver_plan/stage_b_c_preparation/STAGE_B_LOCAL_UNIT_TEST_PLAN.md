# Stage B — Local Unit Test Plan

**Mode: PREPARATION ONLY.** This document describes the local unit tests to run **before** any cloud
deployment. **No deployment, no public URL, no TradingView config, no Farouk-alert edit, no
QST/broker/execution, no permit/lease/order, no gate change.** Telegram PREVIEW listener (PID 40416)
untouched.

## Goal

Prove the **cloud-style receiver logic** locally (same behaviour a Cloudflare Worker would run),
with **no network exposure** — so the logic is trusted before Stage C prepares deployment.

## What is under test (logic parity with the Worker)

The Worker's request handler is small and pure; Stage B validates the same decisions the deployed
Worker will make:

1. **Method routing** — POST only; GET/PUT/DELETE/HEAD/OPTIONS/PATCH → 405, no side effect.
2. **Path auth** — exact long random secret path required; any other path → 404. (PATH_ONLY, Stage-2
   proven; no header needed.)
3. **Body cap** — > 64 KB → 413.
4. **Raw-first capture** — raw body stored byte-exact before parsing.
5. **UTC stamping** — `received_at_utc` ISO-8601 `Z`.
6. **Safe-header whitelist** — content-type/length/user-agent/request-id only; never secrets/cookies.
7. **Parse (read-only)** — symbol/exchange/timeframe/price/time/event_type/direction/grade; JSON and
   non-JSON (default-text) both handled; unresolved `{{...}}` → `UNRESOLVED_PLACEHOLDER`.
8. **event_id + dedupe_key** — assigned/computed per `ALWAYS_ON_RECEIVER_EVENT_ID_AND_DEDUPE_SPEC.md`.
9. **Append-only write** — one record per accepted request; duplicates stored + flagged.
10. **Kill switch** — `ENABLED=false` → 503 + logged, no accept.
11. **Import firewall (fail-closed)** — no broker/cTrader/QST/execution/permit module importable.

## How to run it locally (two acceptable approaches)

- **Approach 1 — reuse the proven Python receiver as the logic oracle.** `stage1_local_receiver/
  receiver.py` already implements 1–11 and passed Stage 1/1B/2. Stage B can (a) re-run its
  PATH_ONLY/PATH_AND_HEADER local tests as the behavioural baseline, and (b) treat any Worker code as
  needing to reproduce these exact outcomes. **No new network exposure.**
- **Approach 2 — local Worker harness (no deploy).** If a Worker is authored, run it under the local
  dev runtime (e.g. `wrangler dev` / miniflare) **bound to localhost only**, with an **R2 binding
  pointed at a local/in-memory bucket**, and POST to `127.0.0.1`. This is a local test, not a
  deployment. (Only if Martyn authorises installing the local Worker toolchain — otherwise use
  Approach 1.)

> Stage B does **not** require installing anything or exposing anything. Approach 1 is sufficient to
> validate the logic; Approach 2 additionally validates the Worker packaging locally.

## Test cases (must all pass)

| # | Input | Expected |
|---|---|---|
| B1 | POST valid JSON to correct secret path, no header | 200 ACCEPTED, PARSED, 1 record |
| B2 | POST to wrong path | 404, no record |
| B3 | GET to correct path | 405, no record |
| B4 | POST default-text body ("XAUUSD Crossing 4,134.00") | 200 ACCEPTED, INVALID_JSON, raw stored |
| B5 | POST with unresolved `{{ticker}}` literal | 200 ACCEPTED, UNRESOLVED_PLACEHOLDER |
| B6 | POST duplicate of B1 | 200, DUPLICATE (stored, flagged), distinct count unchanged |
| B7 | POST > 64 KB | 413, no record |
| B8 | POST with `ENABLED=false` | 503, logged, no accept |
| B9 | Import firewall: simulate a forbidden module present | receiver refuses to start/serve |
| B10 | UTC check: `received_at_utc` ends in `Z`; provider `{{time}}` stored verbatim | pass |

## Invariants verified every run

- No broker/QST/execution path; no permits/leases/orders; gates `PAPER/PREVIEW/False/False`; raw
  captured; UTC stamped; dedupe works; **no production alert touched** (there is no TradingView in
  Stage B at all); Telegram listener untouched.

## Exit criteria (Stage B → Stage C)

All B1–B10 green, invariants green, and Martyn's explicit "proceed to Stage C." Stage C is
**preparation of a deployment checklist only** — still no deploy.
