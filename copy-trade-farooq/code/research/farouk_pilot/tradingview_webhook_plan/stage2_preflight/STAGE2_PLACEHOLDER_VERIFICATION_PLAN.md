# Stage 2 — Placeholder Verification Plan

**PREFLIGHT ONLY.** How TradingView `{{...}}` placeholders will be confirmed at Stage 2 execution.
Nothing here is confirmed yet; do not treat any placeholder as guaranteed.

## Placeholders in the Stage 2 payload

| Placeholder | Field it fills | Confidence | What to verify at execution |
|---|---|---|---|
| `{{ticker}}` | `symbol` | CONFIRMED-COMMON | resolves to `XAUUSD` |
| `{{exchange}}` | `exchange` | CONFIRMED-COMMON | resolves to `PEPPERSTONE` |
| `{{interval}}` | `timeframe`/`chart_interval` | CONFIRMED-COMMON | resolves to `3` (3-minute) |
| `{{close}}` | `trigger_price` | **TO_VERIFY** | is it the bar close price? decimals/format? |
| `{{time}}` | `trigger_time` | **TO_VERIFY** | bar open or close time? timezone (CSV lane was UTC `Z`)? |
| `{{timenow}}` | `server_time_hint` | **TO_VERIFY** | alert firing time; timezone/format? |

> There is **no generic `{{alert_name}}` placeholder** in TradingView — the alert name is hardcoded in
> the message (`LIVE001_WEBHOOK_TEST_STAGE2`). This is a known constraint, not a TO_VERIFY.

## Verification method (at Stage 2 execution, not now)

1. With the local receiver running (fresh secret) and the tunnel up, let the ONE test alert fire once.
2. Open the stored JSONL record and inspect `raw_payload`:
   - Any field still containing a literal `{{...}}` → that placeholder is **unsupported** in that
     alert context; the receiver marks `parse_status = UNRESOLVED_PLACEHOLDER`. Drop/replace it.
   - Confirm `{{ticker}}` / `{{exchange}}` / `{{interval}}` resolved to `XAUUSD` / `PEPPERSTONE` / `3`.
   - Record the **exact string** `{{time}}` / `{{timenow}}` produced, and its apparent timezone.
3. Cross-check `trigger_time` against the TradingView **alert-log** timestamp for the same firing to
   settle the timezone/format (reuse the PHONE_ALERT_BATCH_001 reconciliation approach).
4. Record findings in the Stage 2 results doc; update `WEBHOOK_PAYLOAD_SCHEMA_v0.1.json` from TO_VERIFY
   to CONFIRMED where proven.

## Do-not-assume rules

- Do not claim a placeholder works until an actual firing shows it resolved.
- Do not force a timezone by guess — record the raw value and reconcile against the alert log.
- Do not add more placeholders "just in case"; keep the test payload minimal and only promote fields
  once verified.

## Timezone context (carried over, unresolved)

CSV lane = UTC (`Z`); laptop chart clock = UTC+1; indicator field = Europe/Berlin; phone ≈ UTC. The
webhook `{{time}}`/`{{timenow}}` values must be reconciled to UTC explicitly; the receiver stores the
raw value verbatim and never converts silently.
