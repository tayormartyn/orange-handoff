# Gate G — wrangler tail Diagnostic

**2026-07-09.** Ran `wrangler tail farouk-tv-webhook-logger-v1` (read-only) at the start of the Gate G
wait.

## Result: tail unreliable for a multi-hour wait; R2 used as source of truth

- The tail dropped its **keep-alive** connection early in the long wait (WebSocket "connection lost,
  reconnecting…") — as in Gate E. For an open-ended "wait for a natural trigger" that may be hours away,
  `wrangler tail` is not a dependable capture channel.
- **This did not affect verification:** TradingView reported "Webhook successfully delivered," and the
  **R2 objects are the definitive record** — 69 new objects were confirmed via the temp read-only list
  branch and sampled via `wrangler r2 object get … --remote`, all `ACCEPTED`, raw Farouk text preserved.

## Takeaway for ongoing capture (Gate H)

- Do **not** rely on `wrangler tail` for long waits. Verify from R2 (list + fetch), which is strongly
  consistent. Tail is useful only for a short, watched, immediate re-fire (as in Gate F).
