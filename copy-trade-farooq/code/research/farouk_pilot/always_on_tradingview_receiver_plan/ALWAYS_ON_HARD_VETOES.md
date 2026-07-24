# Always-On Receiver — Hard Vetoes (§8)

**DESIGN ONLY.** Non-negotiable. If a future build cannot honour every one, it is not built or
deployed. These apply to LOGGING_ONLY and every later promotion state.

## Absolute prohibitions

1. **No TradingView-to-broker path.** The webhook lane never places/modifies/cancels an order and
   never forwards an alert to anything that could.
2. **No QST connection.** The receiver never imports/connects QST.
3. **No broker / cTrader connection.** Never imports/connects a broker or cTrader.
4. **No execution modules.** No `module_execution`, sizing, paper-logger, pipeline, archive, or shadow
   module imported or invoked by the receiver.
5. **No permits / leases / orders.** Never created or written.
6. **No execution-gate changes.** `MODE`, `LISTENER_MODE`, `EXECUTION_ENABLED`,
   `CTRADER_EXECUTION_ENABLED` are never modified by this lane (stay PAPER / PREVIEW / False / False).
7. **No live-money trading.** Ever.
8. **No demo trading from the webhook.** A captured alert never drives a demo/broker order either.
9. **No execution from A+ / A+++ / CHoCH / Sweep / BPR** — alone or combined. These are evidence, not
   instructions.
10. **No payload credentials.** No API keys/secrets in the alert body (secret is the URL path only).
11. **No account IDs** anywhere in the payload or store.
12. **No lot/risk sizing in the payload.** The message is evidence metadata only — no position size,
    no SL/TP-as-instruction, no risk figures.

## Structural guarantees that enforce the vetoes

- **Import firewall (fail-closed):** the receiver cannot import any broker/cTrader/QST/execution/permit
  module; a cold-start allowlist check refuses to serve if one is present.
- **No outbound trading calls:** LOGGING_ONLY makes no outbound calls except writing to its own store.
- **Append-only, engine-separate storage:** events land in the receiver's own namespace, never in the
  paper log, archive, or shadow DB, and can never become a trade record.
- **Least-privilege storage credential:** append-only to its own store; no other cloud permission.
- **One-way mode lock:** the receiver cannot self-promote; every promotion is a documented human step.
- **Bounded blast radius:** even if the secret URL leaks, the worst case is junk log entries — no
  execution, no broker reach, no credential exposure (see `ALWAYS_ON_SECURITY_MODEL.md`).

## Relationship to the execution verdict

**None of these vetoes are relaxed by going always-on.** The lane staying observation-only is *why* it
is safe to run 24/7. The moment any veto would need weakening, work stops and returns to Martyn for a
separate, deliberate decision under the full safety regime.

**The always-on TradingView webhook does NOT change the `NOT_INTEGRATION_READY` execution verdict.**
