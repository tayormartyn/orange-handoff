# Next Gate — E-TRADINGVIEW-TEST Readiness

**Gate D is complete.** Describes **Gate E-TRADINGVIEW-TEST**. **Gate E is NOT started and NOT
authorised.**

## Prerequisites

- [x] Stage B PASS.
- [x] Gate C-INSTALL / C-LOGIN / C-R2A / C-R2B / C-DEPLOY-DARK / C-ENDPOINT / C-ENDPOINT-HYGIENE.
- [x] **Gate D-MANUAL-POST** — one valid POST → one append-only R2 object, verified; secret not leaked.
- [ ] Explicit **Gate E-TRADINGVIEW-TEST** approval ← the only remaining prerequisite.

## What Gate E-TRADINGVIEW-TEST would do (later, only if approved)

- Point **one NEW harmless TradingView test alert** (like the Stage 2 `LIVE001_WEBHOOK_TEST_STAGE2`) at
  the always-on cloud endpoint's secret path, keep app notification ON, let it fire once, and verify a
  real TradingView → Worker → R2 capture (placeholders resolved, UTC, one append-only object).
- **Do NOT** edit or mirror any Farouk production alert (that's the later Gate F→H).
- Delete/disable the test alert after.

## Hard boundaries for Gate E

- **One NEW harmless test alert only**; no Farouk production alert edited/mirrored.
- Keep phone/app notification ON (webhook additive).
- The webhook URL = `https://farouk-tv-webhook-logger-v1.taylormartyn70.workers.dev/tv/<secret path>` —
  the secret path from the gitignored local file (never printed).
- No broker/QST/execution/permit/lease/order; no gate change; no shadow engine; listener untouched.

## The webhook URL for Gate E (secret redacted)

`https://farouk-tv-webhook-logger-v1.taylormartyn70.workers.dev/tv/<secret path from LOCAL_SECRET_webhook_path.txt>`

## Gate sequence

`… → C-ENDPOINT ✅ → C-ENDPOINT-HYGIENE ✅ → D-MANUAL-POST ✅ → E-TRADINGVIEW-TEST (next — not
authorised) → [later, separate] F/G/H Farouk mirroring → I reports → J shadow`.

## What Martyn approves next

- **Gate E-TRADINGVIEW-TEST** — one harmless TradingView test alert → cloud receiver. Nothing is
  configured in TradingView without that explicit approval.

**Until Gate E is explicitly approved, nothing further happens.** `NOT_INTEGRATION_READY` unchanged;
capture-only.

## Optional cleanup note

- The Gate D test object (`events/2026/07/07/c73de580….jsonl`) is a harmless manual-test record. It can
  be left as evidence of the passing test, or deleted later if a pristine bucket is preferred before
  real TradingView captures — your call (not done now).
