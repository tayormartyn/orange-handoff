# Stage 2 — Rollback / Stop Plan

**PREFLIGHT ONLY.** The exact teardown for Stage 2, whether it succeeds or is aborted. Designed so any
step can be undone quickly and completely.

## Instant stop (kill switches, in order of reach)

1. **Stop the receiver:** Ctrl+C in its window (or stop the `receiver.py` PID). It captures nothing
   once stopped.
2. **Drop the tunnel:** stop the tunnel process → the public URL immediately stops resolving to the
   laptop. TradingView deliveries then fail harmlessly (visible as a failed webhook status).
3. **Disable/delete the test alert:** in TradingView, remove `LIVE001_WEBHOOK_TEST_STAGE2` (or toggle
   it off). No further firings.
4. **Soft kill (optional):** set `TV_WEBHOOK_ENABLED=0` so a running receiver refuses+logs instead of
   accepting.

## Full rollback checklist (leave no trace beyond the evidence log)

- [ ] Receiver stopped (no `receiver.py` process).
- [ ] Tunnel stopped (no public URL live).
- [ ] Test alert deleted or disabled in TradingView.
- [ ] **No production Farouk alert was edited** — verify each Farouk alert is unchanged (name,
  condition, notifications) and still app/toast-only (no webhook attached).
- [ ] Phone/app notifications for Farouk alerts still ON.
- [ ] No permit/lease/order artifact created (scan).
- [ ] Execution gates unchanged (`MODE=PAPER`, `LISTENER_MODE=PREVIEW`, `EXECUTION_ENABLED=False`,
  `CTRADER_EXECUTION_ENABLED=False`).
- [ ] **Telegram PREVIEW listener PID 40416 still running, untouched.**
- [ ] Stage-2 JSONL evidence preserved (append-only; the test event stays as legitimate evidence).

## If something goes wrong

- **Unexpected repeated deliveries:** drop the tunnel first (cuts reachability), then disable the
  alert. The receiver only appends; it cannot act on repeats.
- **Placeholder/format surprise:** harmless — the record is stored with `UNRESOLVED_PLACEHOLDER`;
  fix the payload, do not retry blindly.
- **Tunnel exposes more than intended:** stop the tunnel immediately; the receiver binds `127.0.0.1`
  and requires the exact **long random secret path**, so a random probe to any other path gets 404.
  (Guessing a sufficiently long random path is infeasible; this is the primary auth for the
  TradingView `PATH_ONLY` mode. The X-TV-Token header is a local-test-only extra.)
- **Any hard gate red:** halt, run this rollback, and report — do not improvise a fix.

## What is intentionally NOT rolled back

- The **append-only JSONL evidence** from a successful test firing is kept (it is legitimate captured
  evidence, not a mistake to erase).
- The Stage-1/Stage-2 design docs remain.

## Post-rollback confirmation

Re-run the read-only safety audit (processes, gates, permit/lease/order scan, listener PID 40416) and
record the result in the Stage-2 results doc.
