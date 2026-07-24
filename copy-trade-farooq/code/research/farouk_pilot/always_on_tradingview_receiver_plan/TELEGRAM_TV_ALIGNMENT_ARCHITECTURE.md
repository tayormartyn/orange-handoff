# Telegram ↔ TradingView Alignment Architecture (§7)

**DESIGN ONLY.** How the always-on TradingView receiver sits beside the existing Telegram evidence
lane. Both are **observation-only**; neither executes; they are **never wired together at runtime**.

## The evidence lanes

| Lane | What it captures | Store | Status |
|---|---|---|---|
| **Telegram PREVIEW listener** (PID 40416) | Farouk/WhaleRoom **human messages** (raw text) | `prospective_evidence_v1.db` (append-only) | running |
| **Telegram media** | supported image bytes from those messages | `prospective_media_v1` (append-only, content-addressed) | running |
| **Phone alert batch** | manually-imported phone screenshots + alert-log CSV | `PHONE_ALERT_BATCH_001` (raw/) | imported |
| **Stage 2 webhook JSONL** | TradingView indicator alert firings (proven) | `stage1_local_receiver/logs/tradingview_webhook_events.jsonl` | 6 records, at rest |
| **Always-on TV receiver** (planned) | TradingView indicator alert firings, **24/7** | cloud append-only store | design only |

## Why they stay separate

- **Different provenance:** Telegram = a *person's narrative* ("A+ SHORT, tp1 hit"); TradingView =
  a *mechanical indicator firing* ("A+ or better setup" at a bar close). Conflating at capture loses
  that distinction.
- **Independent failure modes:** one lane down (laptop asleep, tunnel gone, function error) must not
  corrupt the other's record.
- **Each already append-only** with its own safety envelope.

## Later (offline, read-only) alignment — a study, not an integration

Once the always-on lane has 24/7 data, a **separate, read-only analysis** can align the lanes
**without connecting them at runtime**:

1. **Time-align** a Farouk Telegram signal's `posted_at` with the nearest TradingView alert
   `trigger_time` on the same symbol/timeframe, within a tolerance window. **Both are UTC** (Telegram
   timestamps UTC; TradingView `{{time}}`/`{{timenow}}` confirmed UTC in Stage 2) → clean alignment,
   **no offset guessing**.
2. **Cross-reference market outcome** using the existing shadow-mode price foundation (Phase 1a
   quotes) — still observation-only, still no execution.
3. **State-machine classification:** map aligned events to the Farouk state-machine candidates
   (sweep → CHoCH → BPR → grade) to measure whether the indicator's mechanical firings coincide with
   the human calls and with real market moves.

Output: measurement that feeds the same `NOT_INTEGRATION_READY` evidence base — **it does not enable
execution.**

## Hard boundary

- The always-on TV receiver and the Telegram lane are **never wired together at runtime.**
- Neither lane, alone or combined, may trigger a trade, size, score-for-action, or touch a
  broker/QST/permit/lease/order.
- Alignment is a **future read-only study**, not part of the always-on capture build.
- **The running Telegram PREVIEW listener (PID 40416) is not modified, stopped, or restarted by any of
  this.**
