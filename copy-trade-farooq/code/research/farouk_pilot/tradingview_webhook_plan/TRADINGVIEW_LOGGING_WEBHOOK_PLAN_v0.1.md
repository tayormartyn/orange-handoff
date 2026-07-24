# TradingView Logging-Only Webhook — Master Plan v0.1

**Mode: DESIGN ONLY.** No code built. No TradingView alert configured. No webhook URL created. No
QST / broker / cTrader connection. No permit / lease / order. No risk change. No execution gate
change. The Telegram PREVIEW listener (PID 40416) is left untouched.

## 1. Problem & purpose

TradingView Farouk Playbook alerts are firing but only landing as **app/phone notifications** and a
manually-exported CSV. The CSV already gave **111 firings / 90 distinct events** (see
`PHONE_ALERT_BATCH_001_*`), and every row's **Webhook status was empty** — because no webhook exists.
Between manual CSV exports, firings can be missed locally.

**Goal:** design the *fastest safe* way to stop missing firings by having TradingView **POST each
alert to a logging-only receiver** that stores it append-only. **Observation/evidence only.** It must
**never** trade, size, score, connect to a broker/QST, or create a permit/lease/order.

This is the **TradingView technical-alert evidence lane**, sitting beside the **Telegram
provider-message evidence lane**. Both are observation-only (see
`WEBHOOK_TELEGRAM_ALIGNMENT_NOTES.md`).

## 2. Receiver purpose (what it does / does not do)

**Does:**
- Accept TradingView alert **POST** requests on a single logging endpoint.
- Store the **raw payload byte-exact** (before any parsing).
- Stamp **received_at_utc** (server receipt time, UTC).
- Store a **safe subset of headers** (content-type, user-agent, content-length — never secrets).
- Assign an **event_id** and compute a **dedupe_key**.
- **Parse for classification only** (symbol / timeframe / event_type / direction / grade) in a
  read-only parser mode — parsing never gates anything and never feeds an engine.
- **Deduplicate** repeat/retry deliveries.

**Never:**
- Never trades, sizes, or scores. Never hands off to any pipeline.
- Never creates permits, leases, or orders.
- Never imports or calls broker / cTrader / QST / execution modules.
- Never makes an outbound trading request.

Full controls: `WEBHOOK_RECEIVER_SAFETY_SPEC_v0.1.md`. Storage: `WEBHOOK_STORAGE_SCHEMA_v0.1.md`.
Payload: `WEBHOOK_PAYLOAD_SCHEMA_v0.1.json`. Vetoes: `WEBHOOK_HARD_VETOES.md`.

## 3. Design summary (the shape)

```
TradingView alert  ──HTTPS POST──►  [ logging-only receiver ]
   (Farouk Playbook)                   • verify shared secret (header/path)
                                       • reject non-POST
                                       • store RAW payload + received_at_utc + safe headers
                                       • assign event_id, compute dedupe_key
                                       • classify (read-only parser)  ── no engine, no execution
                                       └─► append-only store (SQLite or JSONL)
                                                     │
                                                     └─► (later) parser-only summary report
                                                     └─► (much later, separate) SHADOW observation
```

No arrow ever leaves the receiver toward a broker, QST, or order path. There is no such arrow in this
design, by construction.

## 4. Fastest safe first implementation (headline recommendation)

**Recommended first build = Option A: local receiver behind a secure tunnel, in LOGGING_ONLY mode**,
using a **long random secret endpoint path** as the **primary auth** (a shared-secret `X-TV-Token`
header is an *additional control for manual local POST tests only* — real TradingView cannot be
assumed to send custom headers; see the Stage 2 auth correction), storing to **append-only JSONL**
first (SQLite mirror optional later). Rationale and comparison: `WEBHOOK_DEPLOYMENT_OPTIONS.md`.

- Fastest to stand up, fully under Martyn's control, zero standing cloud cost.
- Honest limitation: **captures only while the laptop is awake/online** — same constraint as the
  Telegram listener. A small always-on cloud/serverless receiver (Option B/C) is the Stage-5 upgrade
  for laptop-off capture, once the local lane is proven.

## 5. Promotion gates (states this lane may occupy)

`LOGGING_ONLY → PARSER_ONLY → SHADOW_OBSERVATION_ONLY → HUMAN_APPROVAL_ONLY → DEMO_BROKER_LATER`.

Each is a **separate, deliberate, human-approved** step. The plan only authorises building up to
**LOGGING_ONLY** (and design of PARSER_ONLY). Everything past SHADOW_OBSERVATION_ONLY is out of scope
here and gated behind the existing safety regime. See `WEBHOOK_NEXT_STEPS.md`.

## 6. Verdict impact

**A logging-only webhook does NOT change the `NOT_INTEGRATION_READY` execution verdict.** It is an
evidence-capture convenience only. Integration-readiness still depends on the unresolved items (A+++
never observed, C4 repaint PARTIAL, C7 grade INSUFFICIENT, single-day scope) documented in the
FP-LIVE-OBSERVATION-001 checkpoints and `PHONE_ALERT_BATCH_001_LIMITATIONS.md`.

## 7. Final report (answers to the five questions)

1. **Is a logging-only TradingView webhook recommended now?** — **Yes**, as an observation/evidence
   lane only. It closes the "missed firings between manual CSV exports" gap with no execution risk,
   provided the safety controls and hard vetoes are implemented exactly.

2. **Fastest safe first implementation?** — **Local receiver + secure tunnel, LOGGING_ONLY,
   append-only JSONL, long random secret path (primary auth; header is local-test-only), POST-only, no execution modules
   importable.** (Option A.) Upgrade to an always-on cloud/serverless receiver later for laptop-off
   capture.

3. **What must remain absolutely prohibited?** — Any broker/cTrader/QST connection; any
   permit/lease/order; any execution-gate change; any TradingView→broker path; any credentials in the
   URL or alert body; any execution from an alert (incl. A+/A+++/CHoCH/Sweep/BPR alone, or with SL
   missing); any live-money trading. Full list: `WEBHOOK_HARD_VETOES.md`.

4. **Does this change the NOT_INTEGRATION_READY verdict?** — **No.** Unchanged. This is capture only.

5. **What should Martyn do next?** — Review these 9 documents; approve (or amend) the LOGGING_ONLY
   scope; then authorise **Stage 1** (local receiver + manual POST test) only. Nothing is built until
   that explicit go-ahead. See `WEBHOOK_NEXT_STEPS.md`.

---
*Companion documents: RECEIVER_SAFETY_SPEC, PAYLOAD_SCHEMA, STORAGE_SCHEMA, DEPLOYMENT_OPTIONS,
VALIDATION_TEST_PLAN, HARD_VETOES, TELEGRAM_ALIGNMENT_NOTES, NEXT_STEPS.*
