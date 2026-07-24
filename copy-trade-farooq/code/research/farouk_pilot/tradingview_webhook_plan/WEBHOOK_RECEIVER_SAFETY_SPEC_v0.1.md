# Webhook Receiver — Safety Spec v0.1

**DESIGN ONLY.** Hard controls the logging-only receiver MUST satisfy before it is ever built or run.
If any control cannot be met, the receiver is not built.

## A. Isolation controls (no execution surface)

1. **No broker imports.** The receiver module must not import any broker client.
2. **No cTrader imports.** No `ctrader_*`, no `ctrader-open-api`, no protobuf order types.
3. **No QST imports.** No QST client/library of any kind.
4. **No execution modules loaded.** Must not import `module_execution.py`, `module_c_risk.py`
   (sizing), `module_d_logger.py` (paper log), `pipeline.py`, `run.py`, `archive.py`, or any
   `shadow_*` module. The receiver lives in its own package with **no path to the engine**.
5. **No permit / lease / order creation.** Must not import or call
   `campaign_extractor/demo_executor/*` (`management_permit.py`, `one_shot_permit.py`,
   `activation_lease.py`) or write any permit/lease/order artifact.
6. **No outbound trading requests.** The receiver makes **no outbound network calls at all** in
   LOGGING_ONLY mode — it only *receives*. (A later report stage may read its own DB; still no
   outbound trading calls, ever.)
7. **Static import allowlist.** A start-up self-check enumerates loaded modules and **refuses to
   start** if any broker/cTrader/QST/execution/permit module is present. Fail closed.

## B. Endpoint & authentication controls

8. **POST only.** Any method other than `POST` (GET/PUT/DELETE/HEAD/OPTIONS…) → **405**, logged as a
   rejected attempt. No side effects on rejection.
9. **Secret in transport, never in trade data.** Authenticate with **either** a **random secret
   endpoint path** (e.g. `/tv/<long-random-token>`) **and/or** a **shared-secret header** (e.g.
   `X-TV-Token: <secret>`) compared in constant time. Reject (401/404) on mismatch.
10. **No credentials in the webhook URL query string** (they land in logs/proxies). Prefer secret in
    the **path segment** + header, over `?token=`.
11. **No credentials in the TradingView alert body.** The payload carries **no** API keys, no broker
    secrets, no account IDs. (The shared secret is a header/path value, not alert content.)
12. **HTTPS only.** Plaintext HTTP refused. TLS terminated at the tunnel/host.
13. **Body size cap.** Reject payloads over a small limit (e.g. 64 KB) → 413. Prevents log-flooding.
14. **Rate / burst guard.** Soft cap on requests/minute; excess is logged and dropped, never queued
    to anything downstream (there is no downstream).

## C. Data-handling controls

15. **Raw-first, append-only.** The **raw payload is stored byte-exact before any parsing**. Parsing
    failure never loses the raw record.
16. **Append-only store.** Records are only ever inserted. No update, no delete in normal operation
    (JSONL append, or SQLite `INSERT` only with no `UPDATE`/`DELETE` code path).
17. **Read-only parser mode.** The classifier reads the raw payload and writes derived fields to a
    *new* record/columns; it never mutates the raw payload and never makes a decision that acts on
    the world. Parser cannot import the engine (control #4).
18. **Safe headers only.** Persist a whitelist (content-type, content-length, user-agent, a request
    id). **Never** persist Authorization/secret headers or cookies.
19. **Deduplication.** Compute a `dedupe_key` (see storage schema) and mark duplicates; duplicates are
    still stored (append-only) but flagged, so retries are visible without double-counting.

## D. Operational controls

20. **Kill switch.** A single, obvious way to stop the receiver instantly:
    - process-level (Ctrl+C / stop the PID), **and**
    - a config flag `RECEIVER_ENABLED = False` that makes it refuse all requests (returns 503) while
      still logging that it was hit, **and**
    - tunnel-level (drop the tunnel) to revoke reachability.
21. **LOGGING_ONLY mode flag.** An explicit mode constant, default `LOGGING_ONLY`. There is **no code
    path** for any other mode in this build; PARSER_ONLY adds only read-only classification.
22. **No auto-restart into a higher mode.** The receiver can never promote its own mode. Promotion is
    a human, documented step (see promotion gates).
23. **Separate storage from the engine.** Its DB/JSONL lives in its own directory
    (e.g. `data/tv_webhook/`), never in `paper_log.csv`, the archive DB, or `shadow.db`.
24. **Observability of failure.** Delivery failures TradingView reports (non-2xx) and locally-visible
    errors are logged; where TradingView exposes per-alert webhook status, that is reconciled at
    Stage 3.

## E. Fail-closed principle

25. If **any** safety control cannot be verified at start-up (import allowlist, POST-only, secret
    present, append-only store reachable, mode = LOGGING_ONLY), the receiver **refuses to start** and
    prints exactly what failed. It never starts in a degraded/unknown state.

## F. Explicit non-goals (restated as controls)

- It is **not** a trading webhook. It is **not** a TradingView *strategy* auto-trader.
- It does **not** validate, approve, or forward any signal for action.
- It does **not** connect the TradingView lane to the Telegram lane at runtime (comparison is a
  later, offline, read-only analysis).
