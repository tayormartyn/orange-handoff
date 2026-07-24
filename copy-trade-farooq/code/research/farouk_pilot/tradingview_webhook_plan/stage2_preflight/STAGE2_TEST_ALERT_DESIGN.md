# Stage 2 — Safest Test-Alert Design

**PREFLIGHT ONLY — proposed design, not executed.** Goal: prove one real TradingView alert can reach
the logging-only receiver, with zero risk to production Farouk alerts, the listener, or execution
gates.

## Design principles

1. **One NEW harmless test alert only.** Do **not** edit, duplicate-then-modify, or delete any
   existing Farouk production alert. The test alert is independent and clearly named.
2. **Keep phone/app notification ON.** The webhook is *added*, not swapped in. Verifies both channels
   coexist.
3. **Webhook URL on the TEST alert only.** No production alert ever gets a webhook in Stage 2.
4. **Logging-only receiver.** Same Stage-1 `receiver.py`, LOGGING_ONLY, no execution surface.
5. **Fire once, then tear down.** Prefer "Once" trigger; stop receiver + tunnel and remove the test
   alert immediately after one event is captured.
6. **Auth by secret path, not header.** **X-TV-Token header is valid for manual local POST tests only.
   Real TradingView Stage 2 must authenticate by exact long random secret path unless custom header
   support is independently confirmed.** Run the receiver in `PATH_ONLY` mode for this test.

## Proposed alert

| Item | Value | Note |
|---|---|---|
| Alert name | `LIVE001_WEBHOOK_TEST_STAGE2` | unmistakably a test; not a Farouk signal |
| Symbol / feed | XAUUSD / Pepperstone | matches the observed lane |
| Timeframe | 3m | matches the observed lane |
| Condition | a trivial, soon-firing, harmless condition (e.g. a one-shot price crossing that will trigger on the next bar) — **TO_VERIFY** which is quickest/quietest | must not depend on Farouk indicator logic; a plain price/candle condition is fine |
| Trigger frequency | **Once** (single fire) if available | keeps the test to one event |
| App/toast notification | **ON** | verify it still arrives |
| Webhook URL | the Stage-2 tunnel URL `https://<tunnel-host>/tv/<fresh-long-random-secret-path>` | **added at execution time only**, not now. The **secret path is the auth** (TradingView sends no custom header). |
| Alert message (body) | contents of `STAGE2_PAYLOAD_TEMPLATE.json` | no secrets, no broker instruction |

## Flow (execution-time, for reference — not run now)

1. Start local receiver in **`PATH_ONLY`** mode with a **fresh long random secret PATH**
   (`TV_WEBHOOK_SECRET_PATH=<fresh>`, `TV_WEBHOOK_AUTH_MODE=PATH_ONLY`). No custom header required —
   TradingView authenticates by the secret path alone.
2. Start the secure tunnel → obtain the public HTTPS URL (Option A).
3. Create the ONE test alert, app notification ON, paste the tunnel webhook URL, paste the payload.
4. Let it fire once (or trigger the harmless condition).
5. Verify: 1 `ACCEPTED` JSONL record; phone notification arrived; TradingView alert-log shows a
   webhook delivery status for the test alert.
6. **Tear down:** delete/disable the test alert, stop the tunnel, Ctrl+C the receiver.
7. Confirm: no production Farouk alert changed; gates unchanged; listener PID 40416 still running.

## What this design deliberately avoids

- No edit to production Farouk alerts (their app/toast evidence stream is unaffected).
- No standing public exposure (tunnel is up only for the single test, then dropped).
- No reuse of the Stage-1 local token as a public secret (fresh secret for anything internet-facing).
- No execution/broker/QST path — the receiver is the same logging-only module, unchanged.

## Recommendation

**Adopt this design for Stage 2**, contingent on Martyn confirming the Webhook URL field exists and
the TV plan permits webhooks. It is the minimal, reversible test that answers "can TradingView deliver
to our logging-only lane?" without touching anything that matters.
