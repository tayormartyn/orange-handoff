# Raw Text Normalisation Rules v0.1

**DESIGN / OFFLINE ONLY.** Rules for turning captured Farouk **raw text** payloads into **candidate
fields** for observation. **Raw payload is the source of truth. No execution meaning of any kind.**

## Non-negotiable constraints

Extracted fields are **candidate/advisory only**. The normaliser **must never** emit or imply:
- ❌ execution interpretation / "actionable" flag
- ❌ order intent / order params
- ❌ broker route / venue
- ❌ lot size / position size
- ❌ account ID
- ❌ risk sizing / SL/TP as instructions
- ❌ permit / lease / order

It only **describes what fired**, never **what to do**. Runs **offline, read-only** over R2 — never in
the Worker's ingest path.

## Input

Each R2 object's `raw_payload`. For Gate G captures this is a Farouk `alert()` string, e.g.
`Farouks Playbook: A SHORT on XAUUSD 3`. `parse_status` = `INVALID_JSON` (raw text) — expected.
(JSON/PARSED payloads, if a future alert is condition-based, use their fields directly.)

## Extraction rules (raw text → candidate fields)

Match case-insensitively; **order matters** (check `a+++` before `a+`, `a+ long` before `a long`):

| Pattern in raw text | `event_family` | `direction` |
|---|---|---|
| `a+++` | `A_TRIPLE_PLUS` | — |
| `a+ or better` | `A_PLUS_OR_BETTER` | — |
| `a+ long` / `a+ short` | `A_PLUS` | LONG / SHORT |
| `\ba long\b` / `\ba short\b` | `A_LONG` / `A_SHORT` | LONG / SHORT |
| `choch up` / `choch down` | `CHOCH_UP` / `CHOCH_DOWN` | bullish / bearish |
| `bullish engulfing` / `bearish engulfing` | `ENGULFING` | bullish / bearish |
| `bpr formed` | `BPR_FORMED` | — |
| `bpr tapped` | `BPR_TAPPED` | — |
| `sweep high` / `sweep low` | `SWEEP_HIGH` / `SWEEP_LOW` | bearish / bullish |
| (none matched) | `UNKNOWN` | — (leave null; flag `notes`) |

Other candidate fields:
- `symbol`: from text (`XAU`/`XAUUSD`) or JSON `symbol`/`ticker` → e.g. `XAUUSD`.
- `timeframe`: from `on XAUUSD 3` → `3`, or JSON `interval`.
- `grade`: `A+`/`A` if present; **`A+++` only if literally present** (never inferred).
- `event_time_utc`: JSON `trigger_time` if present; else `received_at_utc` — **flag which** (receipt time
  ≠ bar time).
- `provenance`: `PARSED` (JSON) or `RAW_TEXT` (INVALID_JSON).

## Rules of honesty

- **Never invent** a field the text doesn't support → null + `notes`.
- **Never upgrade** a grade (a "tapped" BPR is not "formed"; "A" is not "A+"; nothing is "A+++" unless
  literal).
- **Timezone:** store verbatim; normalise to UTC only for comparison. TradingView `{{time}}`/`{{timenow}}`
  are UTC; the Farouk indicator TZ field is Europe/Berlin — reconcile explicitly, never guess.
- **Dedup:** report-time only, on `(event_time, event_family, direction)`; **never** discard raw at
  ingest (append-only holds).

## Output

A read-only derived view/report (e.g. a per-day summary) alongside — never replacing — the raw objects.
Feeds the `NOT_INTEGRATION_READY` evidence base; enables no execution path.

## Status

v0.1 — design only. Not implemented. Validated informally against the 74 Gate G captures (all classified
cleanly: Engulfing, A LONG/SHORT, CHoCH, Sweep, BPR tapped; 0 unknown; 0 A+/A+++).
