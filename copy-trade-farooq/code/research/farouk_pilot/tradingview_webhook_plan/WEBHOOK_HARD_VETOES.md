# Webhook Hard Vetoes

**DESIGN ONLY.** These are non-negotiable. If a future build cannot honour every one, it is not built
and not run. They apply to LOGGING_ONLY and to every later promotion state.

## Absolute prohibitions

1. **No direct TradingView-to-broker execution.** The webhook lane never places, modifies, or cancels
   an order, and never forwards an alert to anything that could.
2. **No webhook payload containing broker credentials.** Ever.
3. **No webhook payload containing API keys or secrets.** The transport secret lives in the endpoint
   path/header, never in alert content; nothing in the body is a credential.
4. **No execution if SL (stop-loss) is missing.** (Restated as a standing rule for any future,
   separately-authorised execution lane — a webhook alert never carries or implies an executable
   trade, and certainly not one without a stop.)
5. **No execution from an A+ / A+++ alert alone.** A grade alert is evidence, not an instruction.
6. **No execution from CHoCH / Sweep / BPR alerts alone.** Structure alerts are evidence, not
   instructions.
7. **No QST connection.** The receiver never imports/connects QST.
8. **No broker / cTrader connection.** The receiver never imports/connects a broker or cTrader.
9. **No permit / lease / order creation.** The receiver never creates or writes any permit, lease, or
   order artifact.
10. **No execution-gate changes.** `EXECUTION_ENABLED`, `CTRADER_EXECUTION_ENABLED`, `MODE`,
    `LISTENER_MODE` are never modified by this lane; they stay False / PAPER / PREVIEW.
11. **No live-money trading.** Full stop. This lane exists to *capture*, never to *act*.

## Structural guarantees that enforce the vetoes

- **Import firewall:** the receiver package cannot import any broker/cTrader/QST/execution/permit
  module; a start-up allowlist check fails closed if one is present.
- **No outbound trading calls:** LOGGING_ONLY makes no outbound network calls at all.
- **Append-only, engine-separate storage:** captured events land in `data/tv_webhook/`, never in the
  paper log, archive, or shadow DB, and can never become a trade record.
- **Mode is one-way locked:** the lane cannot self-promote; every promotion is a documented human
  step.

## Relationship to the execution verdict

**None of these vetoes are relaxed by adding the webhook.** The TradingView lane staying observation-
only is *why* it is safe to add now. The moment any veto would need to be weakened, the work stops and
returns to Martyn for a separate, deliberate decision under the full safety regime.

**The TradingView webhook does NOT change the `NOT_INTEGRATION_READY` execution verdict.**
