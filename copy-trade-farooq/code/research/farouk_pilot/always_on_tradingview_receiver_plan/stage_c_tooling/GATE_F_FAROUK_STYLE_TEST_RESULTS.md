# Gate F — Farouk-STYLE Cloud Webhook Test Results

**Run:** 2026-07-08 22:03 local (Italy). **Outcome: PASSED ✅**

A NEW isolated test alert `LIVE002_FAROUK_STYLE_CLOUD_WEBHOOK_TEST_GATE_F` (NOT a Farouk production
alert) delivered a Farouk-style, logging-only payload to the always-on Worker → **HTTP 200** → **one**
append-only R2 object, verified.

## Transport (wrangler tail)

POST from `TradingView Webhook` to the correct secret path → **200 / outcome ok**. See
`GATE_F_WRANGLER_TAIL_DIAGNOSTIC.md`.

## R2 object (verified via `wrangler r2 object get … --remote`)

- Key: `events/2026/07/08/9d66e109-3651-4c63-9ccf-db42a0cb5e8e.jsonl` (1661 bytes).
- Count 3 → **4** (Gate D + 2 Gate E + 1 Gate F) — **exactly one new object**.
- `validation_status: ACCEPTED`, `parse_status: PARSED`, `received_at_utc: 2026-07-08T20:55:43Z` (UTC),
  `path: /tv/<redacted>` (secret NOT stored; 0 occurrences), raw_payload byte-preserved.
- `event_type: null` — the `candidate_event: A_PLUS_SHORT_TEST` string is **not** interpreted as a real
  A+ signal (Worker classifies only from event_type/event_text). Stored verbatim as observation.

## Placeholders resolved

XAUUSD / PEPPERSTONE / interval `1` / close `4078.59` / time `2026-07-08T20:55:00Z` /
timenow `2026-07-08T20:55:43Z` — all resolved, none literal, times UTC. (See
`GATE_F_PLACEHOLDER_RESOLUTION_RESULTS.md`.)

## Farouk-style fields (harmless observation, stored verbatim)

`strategy_family=FAROUK_STYLE_TEST`, `candidate_event=A_PLUS_SHORT_TEST`, `instrument=XAUUSD`,
`session_context=TEST_ONLY`, `direction_hint=SHORT_TEST_ONLY`, `execution_allowed=false`,
`broker_execution_allowed=false`, `qst_allowed=false`, `test=true`, `lane=LOGGING_ONLY`,
`test_id=GATE_F_FAROUK_STYLE_TEST_001`. **No** lot/account/order/permit/lease. No execution meaning.

## Phone/app notification

Confirmed by Martyn: **YES**.

## Safety / revert

Temp read branch removed; Worker back to **pure logging-only** (version `a7e38717…`; `GET ?list`→405,
POST wrong path→404, GET→405). No R2/S3 credentials; secret never exposed (redacted in tail + reports);
Farouk production alerts untouched; no broker/QST/execution; no permit/lease/order; gates
PAPER/PREVIEW/False/False; Telegram listener PID 40416 untouched; `NOT_INTEGRATION_READY` unchanged.

## Teardown

Martyn may delete/disable `LIVE002_FAROUK_STYLE_CLOUD_WEBHOOK_TEST_GATE_F`. Keep the R2 evidence
objects (incl. `9d66e109…`).
