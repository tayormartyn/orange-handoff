# Next-30 Observation Plan

**Observation-only roadmap** to grow the shadow journal from 3 → 30 outcome-matched candidates. **No
trading, no broker, no execution.** Each step is offline/read-only. `NOT_INTEGRATION_READY` unchanged.

## Standing state (keep as-is)

- **Keep H1 `LIVE004_APLUS_MIRROR_GATE_H1` and H2 `LIVE005_CHOCH_DOWN_MIRROR_GATE_H2` armed** — they
  gather the rare, higher-signal families (A+, CHoCH DOWN) that the Gate G composite lacked.
- Worker stays **pure logging-only**; capture lane stays always-on.
- Telegram PREVIEW listener stays running (PID 40416); gates stay `PAPER/PREVIEW/False/False`.

## Repeat loop (per observation window / session)

1. **On H1/H2 fire:** when Martyn says "fired — H1" or "fired — H2", **verify that mirror from R2 first**
   (temp read-only list branch → confirm growth → fetch newest → check raw/UTC/INVALID_JSON/matching
   text/no-secret → revert to pure logging-only → confirm `GET ?list`→405 → tell Martyn to delete only
   that mirror). Capture-only.
2. **Daily capture review** — read the day's captured events (as in the daily monitoring report v0).
3. **Import that day's OHLC** — XAUUSD 1m per `XAUUSD_OHLC_IMPORT_SCHEMA_v0_1.md` into `price_data/`
   (a new dated file per window). UTC, no fabrication.
4. **Run the pipeline offline:**
   `raw_farouk_text_classifier_v0_2` → `shadow_candidate_detector_v0_1` → `outcome_matcher_v0_1`.
5. **Append** each outcome-matched candidate to the journal (markdown + CSV), assigning `outcome_label`
   per the schema rubric. Append-only; never edit past rows.
6. **Log** false positives (wrong hint) and any notable missed moves.

## Review gate

7. **After 30 outcome-matched candidates** (across ≥5 sessions), do the manual aggregate review against
   `NO_TRADE_TO_DEMO_EVIDENCE_THRESHOLDS_v0_1.md`: per-type hit-rate, adverse-heat profile,
   false-positive / missed-signal review, Telegram/Discord cross-check.
8. **Do NOT trade before the evidence threshold is met** — and even then, only a governance discussion
   about a *demo/paper* study, never live execution. `NOT_INTEGRATION_READY` stays until a future
   governance decision explicitly lifts it.

## Hard stops (unchanged, every step)

No broker/cTrader/QST; no permits/leases/orders; no execution-gate or risk-policy change; no order intent
/ sizing / account binding; no webhook URL / secret exposure. Outcome numbers stay descriptive price
stats.

## Status

Plan active. 3/30 logged. Continue capture-only observation; next data point comes from the next
window / H1 or H2 fire.
