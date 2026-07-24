# Always-On Receiver — Safety Spec v0.1

**DESIGN ONLY.** Hard controls the always-on receiver MUST satisfy before it is ever built or
deployed. If any control cannot be met, it is not built. These extend the Stage-1 safety spec to a
cloud/serverless context.

## A. Isolation (no execution surface)

1. **No broker imports.** 2. **No cTrader imports.** 3. **No QST imports.**
4. **No execution modules** (no `module_execution`, sizing, paper-logger, pipeline, archive, shadow).
5. **No permit/lease/order creation** (no `demo_executor/*`, no order artifacts).
6. **No outbound trading requests** — the function only *receives* and writes to its own store.
7. **Import allowlist, fail-closed** — at cold start the function verifies its loaded modules contain
   none of the forbidden markers; if any is present it **refuses to serve** (returns 503) and logs why.
8. **Least-privilege storage** — the function's storage credential can only append to its own
   store/bucket/table; it has no other cloud permissions.

## B. Endpoint & auth

9. **POST only** → any other method returns 405, no side effect.
10. **Exact long random secret path** is the primary auth (Stage 2 proven; TradingView sends no custom
    header). Any other path → 404.
11. **No credentials in the URL query string; none in the alert body.** Secret is the path segment.
12. **HTTPS only** (provider-terminated TLS).
13. **Body size cap** (e.g. 64 KB) → 413.
14. **Rate/burst guard** where the platform supports it; excess logged + dropped (nothing queued
    downstream — there is no downstream).

## C. Data handling

15. **Raw-first, append-only** — raw body stored byte-exact before parsing; failure never loses raw.
16. **Append-only store** — inserts only; keyed on `event_id`; no update/delete code path. (On KV
    stores that overwrite by key, key strictly on unique `event_id` so nothing is clobbered.)
17. **Read-only parser** — derives metadata into new fields; never mutates raw; cannot import engine.
18. **Safe headers only** — whitelist (content-type, content-length, user-agent, request-id). Never
    persist authorization/secret headers or cookies.
19. **Deduplication** — compute `dedupe_key`; duplicates stored + flagged, never double-counted.
20. **UTC everywhere** — `received_at_utc` from server clock; store provider timestamps verbatim
    (Stage 2 confirmed TradingView sends UTC `Z`).

## D. Operations

21. **Kill switch (multiple):** (a) an `ENABLED=false` config flag → function returns 503 while still
    logging it was hit; (b) delete/disable the function → endpoint gone; (c) rotate the secret path →
    old URL 404s. Any one instantly stops capture.
22. **No self-promotion** — the function has one mode (LOGGING_ONLY / later PARSER_ONLY). It can never
    escalate its own capability.
23. **Storage separate from the engine** — never writes to `paper_log.csv`, the archive DB, or
    `shadow.db`; its own namespace only.
24. **Audit trail** — every accepted/rejected request leaves a record (or metric) so delivery
    failures and probes are visible.
25. **Observability** — health check endpoint may return only a static 200/"ok" with **no** secret and
    **no** data; it must not accept POST bodies.

## E. Fail-closed principle

26. If **any** control cannot be verified at cold start (import allowlist, POST-only routing, secret
    configured, append-only store reachable, mode = LOGGING_ONLY), the function **refuses to serve**
    and surfaces exactly what failed. Never serve in a degraded/unknown state.

## F. Non-goals (restated as controls)

- Not a trading webhook; not a TradingView strategy auto-trader.
- Does not validate/approve/forward any signal for action.
- Does not connect to the Telegram lane at runtime.
- Does not hold broker/account credentials of any kind.
