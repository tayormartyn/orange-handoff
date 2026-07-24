# Stage 2 — Safety Gates

**PREFLIGHT ONLY.** These gates must ALL hold before Stage 2 starts, throughout, and after. If any
cannot be satisfied, Stage 2 does not run.

## Pre-conditions (before any Stage 2 action)

1. Martyn has **confirmed the Webhook URL field exists** in the TV alert dialog (manual check).
2. Martyn has **confirmed the TV plan permits webhooks**.
3. Martyn has given **explicit authorisation** to run Stage 2.
4. The Stage-1 receiver is unchanged and still passes its import firewall (logging-only).
5. A **fresh long random secret PATH** is set for Stage 2 (not the Stage-1 local test token), and the
   receiver runs in **`PATH_ONLY`** mode (secret path is the auth; no custom header required for
   TradingView).

## Hard gates (unchanged from the plan's vetoes)

- **No broker / cTrader connection.** No such import or process.
- **No QST connection.**
- **No permit / lease / order creation.**
- **No execution-gate change:** `MODE=PAPER`, `LISTENER_MODE=PREVIEW`, `EXECUTION_ENABLED=False`,
  `CTRADER_EXECUTION_ENABLED=False` stay as-is.
- **No TradingView→broker path.** The webhook targets only the logging-only receiver.
- **No production Farouk alert edited/duplicated-then-modified/deleted.** One NEW test alert only.
- **No secret in URL query string or payload body.** Secret is the **long random path segment**
  (primary auth). **X-TV-Token header is valid for manual local POST tests only; real TradingView
  Stage 2 authenticates by exact long random secret path unless custom header support is
  independently confirmed.**
- **No live-money trading.** This is capture only.
- **Telegram PREVIEW listener (PID 40416) not stopped/restarted/modified.**

## During-test gates

- Receiver runs LOGGING_ONLY; no outbound trading call; append-only JSONL only.
- Tunnel is up **only for the single test** and forwards to `127.0.0.1` only.
- Phone/app notification remains ON for the test alert.
- Only ONE test alert exists with a webhook; all Farouk alerts remain app/toast-only.

## Post-test gates (verify all)

- Exactly one `ACCEPTED` event logged (retries visible as `DUPLICATE`).
- Test alert deleted/disabled; tunnel dropped; receiver stopped.
- No production Farouk alert changed.
- No permit/lease/order artifact created.
- Execution gates unchanged.
- Listener PID 40416 still running.

## Fail-closed rule

If any gate is red at any point, **halt Stage 2 immediately**, tear down (rollback plan), and report
the exact failure. Never work around a red gate.
