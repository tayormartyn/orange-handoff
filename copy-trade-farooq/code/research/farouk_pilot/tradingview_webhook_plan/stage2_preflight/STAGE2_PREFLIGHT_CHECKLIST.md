# Stage 2 — Preflight Checklist

**Mode: PREFLIGHT ONLY.** Nothing is configured, started, exposed, or saved. This is a readiness
checklist for a *future* Stage 2 (one harmless TradingView alert → the logging-only receiver), to be
executed only after Martyn confirms the preflight items and explicitly authorises Stage 2.

Stage 1 result: **PASSED** (localhost receiver logs valid POST, rejects bad-auth/non-POST, dedupes).
Telegram PREVIEW listener: **RUNNING PID 40416 — must not be touched.**

## A. TradingView account / feature availability

- [x] **Alert dialog shows a "Webhook URL" field** — **CONFIRMED by Martyn 2026-07-07** (manual look
  only: no URL pasted, no alert saved, no Farouk production alert edited). See
  `STAGE2_MARTYN_MANUAL_CHECKLIST.md`.
- [ ] **TV plan permits webhooks** (field is present; confirm it is enabled/usable, not greyed-out /
  upgrade-prompted). **TO_VERIFY** at Stage 2 execution.

> **HOLD:** Webhook URL field confirmed present, but **Stage 2 is NOT started.** Per Martyn's
> instruction, proceed no further until the explicit Stage 2 authorisation prompt is given. No tunnel,
> no public URL, no test alert, no receiver start.
- [ ] Confirm whether the account allows the number of alerts needed to add ONE test alert without
  disturbing the existing Farouk alerts.

## B. Test-alert strategy (do not touch production)

- [ ] Use **one NEW harmless test alert** — do **NOT** edit any existing Farouk production alert.
- [ ] Keep **phone/app notification ON** for the test alert (webhook is additive, not a replacement).
- [ ] Proposed alert name: **`LIVE001_WEBHOOK_TEST_STAGE2`** (clearly a test; not a Farouk signal).
- [ ] Proposed test symbol/timeframe: **XAUUSD · Pepperstone · 3m** (matches the observed lane) — or
  a deliberately trivial condition so it fires once quickly. **TO_VERIFY** which harmless condition
  fires soonest without noise (e.g. a one-shot "crossing" that triggers on the next bar).
- [ ] Alert set to **"Once"** (fire a single time) if available, to keep the test to one event.

## C. Payload

- [ ] Use `STAGE2_PAYLOAD_TEMPLATE.json` as the alert message body.
- [ ] Payload contains **no** API keys, **no** broker instruction, **no** secret (the secret lives in
  the **URL path**, not the body — see auth correction below).
- [ ] Expected resolved placeholders and TO_VERIFY items: see
  `STAGE2_PLACEHOLDER_VERIFICATION_PLAN.md`.

## D. Receiver + endpoint (LOCAL FIRST; do NOT start tunnel in preflight)

- [ ] Local receiver command (unchanged from Stage 1):
  `python research/farouk_pilot/tradingview_webhook_plan/stage1_local_receiver/receiver.py`
- [ ] Endpoint path uses a **fresh long random secret PATH** for Stage 2 (not the Stage-1 local test
  token). **TO_SET at execution time** via `TV_WEBHOOK_SECRET_PATH`.
- [ ] Run the receiver in **`PATH_ONLY`** mode for the TradingView test
  (`TV_WEBHOOK_AUTH_MODE=PATH_ONLY`) — the exact secret path authenticates; **no custom header
  required.**
- [ ] **Tunnel / public URL:** required for TradingView to reach the receiver, but **NOT started in
  preflight.** Option A (local + secure tunnel) per `WEBHOOK_DEPLOYMENT_OPTIONS.md`. Only started at
  Stage 2 execution, after explicit go-ahead.

> **AUTH CORRECTION (Stage 2 / TradingView):** **X-TV-Token header is valid for manual local POST
> tests only. Real TradingView Stage 2 must authenticate by exact long random secret path unless
> custom header support is independently confirmed.** TradingView cannot be assumed to send custom
> headers, so the **long random secret path is the PRIMARY (and, for TradingView, the only required)
> auth control.** No secret in the query string; no broker credentials/API keys in the URL; no
> credentials in the alert body. HTTPS-only via the tunnel; body-size cap; POST-only; receiver accepts
> only the exact secret path and rejects all other paths.

## E. Expected outcomes to verify at Stage 2 execution

- [ ] **JSONL:** exactly **one** new `ACCEPTED` record for the single test firing (plus any
  TradingView retries visible as `DUPLICATE`).
- [ ] **Raw payload** stored byte-exact; `received_at_utc`, safe headers, event_id, dedupe_key,
  classification fields present.
- [ ] **TradingView alert-log "Webhook status"** column shows a delivery status for the test alert
  (previously empty because no webhook existed). **TO_VERIFY** exact status text TradingView reports
  on success/failure.
- [ ] **Phone/app notification** for the test alert still arrives.

## F. Rollback / stop

- [ ] Follow `STAGE2_ROLLBACK_PLAN.md`: stop receiver (Ctrl+C), drop the tunnel, delete/disable the
  test alert, confirm no production alert changed, confirm gates unchanged, confirm listener PID 40416
  still running.

## G. Safety invariants (must all hold before, during, after)

See `STAGE2_SAFETY_GATES.md`. Summary: no broker/QST/execution/permit/lease/order; no execution-gate
change; listener untouched; logging-only; no production Farouk alert edited.

## Preflight status

- Stage 1 (PATH_AND_HEADER local test): PASSED.
- **PATH_ONLY local compatibility test: PASS** (2026-07-07). Header-less POST to the exact long random
  secret path accepted (200/ACCEPTED); wrong path → 404; GET → 405; exactly +1 JSONL record; no
  broker/QST/execution path; no permit/lease/order; gates unchanged; listener PID 40416 untouched.
  - **Result file:**
    `research/farouk_pilot/tradingview_webhook_plan/stage1_local_receiver/STAGE1B_PATH_ONLY_LOCAL_TEST_RESULTS.md`
- Webhook URL field: CONFIRMED present + usable by Martyn (see section A).
- **Stage 2 attempt #1 (earlier 2026-07-07): HALTED** — no safe tunnel tool available at the time.
  See `STAGE2_BLOCKED_NO_SAFE_TUNNEL.md`.
- **Stage 2 attempt #2 (2026-07-07): EXECUTED — PASS.** cloudflared installed (winget, with explicit
  approval); one NEW harmless alert `LIVE001_WEBHOOK_TEST_STAGE2`; two firings — firing 1 sent
  TradingView's default text (finding), firing 2 (JSON retest) parsed cleanly with **all placeholders
  resolved** and **timezone confirmed UTC**; PATH_ONLY auth worked against real TradingView; exactly
  one accepted event per firing; no broker/QST/execution/permit/lease/order; gates unchanged; listener
  PID 40416 untouched. **Tunnel + receiver torn down** (public URL dead). See
  `STAGE2_TEST_RESULTS.md`.
- **Remaining on Martyn:** delete/disable the `LIVE001_WEBHOOK_TEST_STAGE2` test alert in TradingView
  (Farouk production alerts untouched).
- **Stage 2 objective met.** Does **not** change the `NOT_INTEGRATION_READY` verdict (capture only).
