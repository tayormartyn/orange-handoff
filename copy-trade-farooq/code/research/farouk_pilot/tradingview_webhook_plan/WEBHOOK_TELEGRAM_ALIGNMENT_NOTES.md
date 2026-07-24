# Webhook ↔ Telegram Listener — Alignment Notes

**DESIGN ONLY.** How the TradingView webhook lane sits beside the running Telegram PREVIEW listener.
Both are **observation-only evidence lanes**; neither executes.

## Two lanes, two kinds of evidence

| | Telegram PREVIEW listener (running, PID 40416) | TradingView logging webhook (planned) |
|---|---|---|
| **Lane** | Authorised **provider / message** evidence | **Technical alert** evidence |
| **Captures** | Farouk/WhaleRoom **human messages** (raw text/images) | Farouk Playbook **indicator alert firings** |
| **Trigger** | A person posting in the channel | An indicator condition on the chart |
| **Store** | `prospective_evidence_v1.db` (append-only) | `data/tv_webhook/` JSONL/SQLite (append-only) |
| **Timing** | `telegram_posted_at` / receipt | `received_at_utc` + payload trigger/bar time |
| **Executes?** | No | No |
| **Touches broker/QST?** | No | No |

## Why keep them separate

- Different provenance and failure modes: a Telegram message is a *narrative* ("A+ SHORT, tp1 hit");
  a TradingView alert is a *mechanical* firing ("A+ or better setup" at a bar close). Conflating them
  at capture would lose that distinction.
- Independent capture means one lane down (e.g. laptop asleep, tunnel dropped) doesn't corrupt the
  other's record.
- Each already has its own append-only store and its own safety envelope.

## Later (offline, read-only) comparison — not an integration

Once both lanes have data, a **separate, read-only analysis** can align them **without connecting them
at runtime**:

- Match a Telegram signal's `posted_at` to the nearest TradingView alert `trigger_time` on the same
  symbol/timeframe, within a tolerance window.
- Cross-reference both against **market outcome** using the existing shadow-mode price foundation
  (Phase 1a quotes) — still observation-only, still no execution.
- Surface: did the indicator alert precede/coincide with the human call? Did either align with a real
  market move? This is *measurement*, feeding the same NOT_INTEGRATION_READY evidence base.

## Timezone caution (carried over)

Alignment must respect the unresolved timezone references already flagged: TradingView CSV times were
**UTC (Z)**; the laptop chart clock was **UTC+1**; the indicator field was **Europe/Berlin**; phone
clock **≈UTC**. The webhook payload's `trigger_time`/`server_time_hint` are **TO_VERIFY** for
timezone. Any Telegram↔TradingView alignment normalises everything to **UTC** and records the
assumption; it never forces a single offset by guess.

## Hard boundary

- The webhook lane and the Telegram lane are **never wired together at runtime**.
- Neither lane, alone or combined, may trigger a trade, size, score-for-action, or touch a
  broker/QST/permit/lease/order.
- This alignment is a **future read-only study**, not part of the LOGGING_ONLY build being proposed.
- **The running Telegram PREVIEW listener is not modified, stopped, or restarted by any of this.**
