# Webhook Validation & Test Plan v0.1

**DESIGN ONLY.** Staged plan. **No stage past Stage 0 runs without Martyn's explicit approval of that
stage.** Every stage carries the same invariant checks (Section "Per-stage invariants").

## Per-stage invariants (checked at EVERY stage)

At each stage, before and after, verify:
- **No broker/QST/execution path exists** — receiver's import list contains none; no outbound trading
  call made.
- **No permit/lease/order files created** — scan the permit/lease/order artifact locations; must be
  unchanged.
- **No execution gates changed** — `EXECUTION_ENABLED`, `CTRADER_EXECUTION_ENABLED`, `MODE`,
  `LISTENER_MODE` all unchanged (PAPER / False / PREVIEW).
- **Raw payload captured** — every accepted POST has a byte-exact `raw_payload`.
- **Dedupe works** — duplicate deliveries collapse in distinct-event counts (still stored, flagged).
- **Failed delivery is visible where possible** — non-2xx / TradingView webhook-status reconciled.
- **Phone/app notification still works** — the TradingView alert's app/toast notification continues
  to fire independently (webhook is additive, not a replacement).

## Stage 0 — Design only  *(this document; DONE)*

- Produce the 9 design docs. No code, no endpoint, no alert change.
- Exit check: docs reviewed by Martyn; LOGGING_ONLY scope approved.

## Stage 1 — Local receiver + manual POST

- Build the LOGGING_ONLY receiver (Option A), **not yet exposed to TradingView**.
- Test by sending **hand-crafted POSTs from localhost** (curl-style) using the payload template.
- Verify: POST-only (GET/PUT → 405), secret path/header enforced (bad token → 401/404), body cap,
  raw stored, `received_at_utc` set, event_id + dedupe_key assigned, parser classifies the sample,
  append-only store grows by exactly one record per accepted POST.
- Confirm import allowlist self-check refuses to start if any engine/broker module is importable.
- **No TradingView involvement yet.**

## Stage 2 — One harmless TradingView alert → webhook

- **Precondition TO_VERIFY:** TradingView plan permits webhooks.
- Expose the receiver (tunnel) and configure **one NEW test alert** (a **duplicate** of a harmless
  alert, or a throwaway test alert) to POST to the secret URL. **Do not edit the live Farouk alerts
  in this stage.**
- Fire it once (or wait for one benign firing). Verify the receiver stored it and the **phone/app
  notification still arrived**.
- Confirm the payload contained **no** secret/API key/broker instruction.

## Stage 3 — Reconcile TradingView log vs receiver store

- Export the TradingView alert log (as with PHONE_ALERT_BATCH_001) for the test window.
- Diff the TradingView rows against the receiver's stored events: counts match, timestamps reconcile
  (resolve the UTC/format TO_VERIFY from the payload schema), no drops, no phantom events.
- Document any timezone/format normalisation needed.

## Stage 4 — Duplicate & retry behaviour

- Force duplicate/retry deliveries (re-send the same payload; simulate TradingView retry).
- Verify `dedupe_key` collapses them in distinct counts, duplicates are stored + flagged
  `validation_status = DUPLICATE`, and no double-counting occurs.
- Verify a deliberately malformed body → `parse_status = INVALID_JSON`/`UNRESOLVED_PLACEHOLDER` but
  the **raw is still captured** and nothing downstream happens.

## Stage 5 — Laptop-off / cloud receiver

- Stand up the always-on receiver (Option C serverless preferred) in LOGGING_ONLY.
- Point the test alert there; put the laptop to sleep; confirm firings are **still captured** while
  the laptop is off.
- Re-run Stage 3 reconciliation against the cloud store.

## Stage 6 — Parser-only summary report

- Add a **read-only** report that reads the store and prints counts by event_type/grade/direction
  (mirroring the PHONE_ALERT_BATCH_001 report), plus dedupe stats and any `TO_VERIFY`/anomaly notes.
- Report writes only its own output file; imports no engine; makes no decision.

## Stage 7 — Shadow-only integration (LATER, separate build)

- **Out of scope for this plan.** Only after all above pass and under the existing shadow-mode safety
  regime, the captured TradingView events could feed **SHADOW_OBSERVATION_ONLY** analysis (no
  execution, no persistence into the immutable archive without its own gate).
- Requires a fresh, separate authorisation. Nothing here pre-approves it.

## Gate between stages

Advancing from stage N to N+1 requires: all per-stage invariants green, the stage's specific checks
green, and **Martyn's explicit "proceed to Stage N+1."** Any red invariant halts the plan and is
reported, not worked around.
