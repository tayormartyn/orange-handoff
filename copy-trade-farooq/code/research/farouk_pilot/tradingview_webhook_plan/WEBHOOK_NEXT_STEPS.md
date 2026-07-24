# Webhook — Next Steps & Promotion Gates

**DESIGN ONLY.** Nothing here is built. This is the decision path after Martyn reviews the plan.

## Promotion gates (each is a separate, human-approved step)

The lane may only occupy one state at a time, and may only advance one gate at a time, with explicit
sign-off:

1. **LOGGING_ONLY** — receive + store raw + safe headers. No parsing decisions. *(This build's ceiling
   for a first cut.)*
2. **PARSER_ONLY** — add read-only classification (symbol/event/grade/direction). Still no action,
   still engine-isolated.
3. **SHADOW_OBSERVATION_ONLY** — captured events may feed shadow-mode *measurement* (no execution, no
   archive mutation without its own gate). Separate authorisation required.
4. **HUMAN_APPROVAL_ONLY** — a human reviews aligned evidence; still no automated action.
5. **DEMO_BROKER_LATER** — far future; demo-only, under the full existing safety regime; out of scope
   here and not implied by anything above.

**Stated plainly: the TradingView webhook does NOT change the `NOT_INTEGRATION_READY` execution
verdict.** Capture ≠ readiness.

## What is authorised by this plan

- **Only the writing of these 9 design documents.** No receiver, no endpoint, no alert change, no
  tunnel, no cloud resource has been created.

## Recommended path (if Martyn approves)

1. **Approve LOGGING_ONLY scope** (or amend it).
2. **TO_VERIFY first:** confirm the TradingView plan tier actually permits webhook alerts, and check
   the real Farouk Playbook alert placeholders ({{ticker}}, {{exchange}}, {{interval}}, {{close}},
   {{time}}, {{timenow}}) resolve as expected.
3. **Stage 1 build:** local receiver (Option A) + manual POST tests only. No TradingView involvement.
4. Proceed Stage-by-Stage per `WEBHOOK_VALIDATION_TEST_PLAN_v0.1.md`, each behind explicit sign-off.
5. Once validated, move the always-on lane to **Option C (serverless)** for laptop-off capture.

## Final report — the five questions

1. **Is a logging-only TradingView webhook recommended now?**
   **Yes** — as an observation/evidence lane only. It closes the "missed firings between manual CSV
   exports" gap with no execution risk, *provided* the safety spec and hard vetoes are implemented
   exactly.

2. **What is the fastest safe first implementation?**
   **Option A:** a local receiver behind a secure tunnel, running **LOGGING_ONLY**, storing
   **append-only JSONL**, authenticated by a **long random secret path** (primary; the shared-secret
   `X-TV-Token` header is a manual-local-test-only extra, since TradingView cannot be assumed to send
   custom headers), **POST
   only**, with the **import firewall** (no broker/cTrader/QST/execution/permit modules) and a **kill
   switch**. Upgrade to serverless (Option C) later for 24/7 capture.

3. **What must remain absolutely prohibited?**
   Any broker/cTrader/QST connection; any permit/lease/order; any execution-gate change; any
   TradingView→broker path; any credential in the URL or alert body; any execution from an alert
   (including A+/A+++/CHoCH/Sweep/BPR alone, or with SL missing); any live-money trading. See
   `WEBHOOK_HARD_VETOES.md`.

4. **Does this change the NOT_INTEGRATION_READY execution verdict?**
   **No. Unchanged.** This lane is capture only.

5. **What should Martyn do next after reviewing the plan?**
   Review the 9 documents; approve or amend the LOGGING_ONLY scope; verify the TradingView plan/
   placeholders (TO_VERIFY items); then authorise **Stage 1 only** (local receiver + manual POST).
   Nothing is built until that explicit go-ahead — and the running Telegram PREVIEW listener stays
   untouched throughout.

## Document set (this plan)

`TRADINGVIEW_LOGGING_WEBHOOK_PLAN_v0.1.md` · `WEBHOOK_RECEIVER_SAFETY_SPEC_v0.1.md` ·
`WEBHOOK_PAYLOAD_SCHEMA_v0.1.json` · `WEBHOOK_STORAGE_SCHEMA_v0.1.md` ·
`WEBHOOK_DEPLOYMENT_OPTIONS.md` · `WEBHOOK_VALIDATION_TEST_PLAN_v0.1.md` · `WEBHOOK_HARD_VETOES.md` ·
`WEBHOOK_TELEGRAM_ALIGNMENT_NOTES.md` · `WEBHOOK_NEXT_STEPS.md`
