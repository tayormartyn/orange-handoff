# Raw Alert Normalisation Plan (DESIGN ONLY)

**Prepared during the Gate G wait. Design only — no code, no execution meaning.** Defines how captured
TradingView webhook payloads are normalised for later **observation**, whether JSON or raw text.

## Core principle: raw is the source of truth

- The **`raw_payload`** stored byte-exact in each R2 object is the **authoritative record**.
- All derived/normalised fields are **candidate fields only** — advisory metadata for observation. They
  **never** carry execution meaning, order intent, broker routing, or risk sizing.

## Two payload shapes to support

### 1. JSON / `parse_status: PARSED`
- TradingView alert whose message is editable and set to our JSON template (Gate E/F style).
- Fields already extracted by the Worker: `symbol`, `exchange`, `timeframe`, `trigger_price`,
  `trigger_time`, `server_time_hint`, plus any custom fields (stored in raw_payload).
- Placeholders resolved (`{{ticker}}` etc.); UTC times.

### 2. Raw text / `parse_status: INVALID_JSON`
- TradingView alert whose message is **indicator-generated (`alert()`-based)** — e.g.
  `"Farouks Playbook: A+ LONG on XAUUSD 3"`. Not JSON, so the Worker stores it raw with
  `INVALID_JSON`.
- Normalisation happens **later, offline, read-only** (never in the Worker's ingest path).

## Offline normaliser (later, read-only over R2 — not built now)

A separate read-only tool would read R2 objects and emit **candidate fields** without touching raw:

| Candidate field | From JSON payload | From raw Farouk text |
|---|---|---|
| `symbol` | `symbol`/`ticker` | regex `XAU`/`XAUUSD` in text |
| `timeframe` | `timeframe`/`interval` | `on XAUUSD 3` → `3` (if present) |
| `event_type` | `event_type`/`event_text` keywords | keyword scan: `A+ LONG/SHORT`, `A+ or better`, `Sweep high/low`, `CHoCH up/down`, `BPR tapped/formed`, `Bullish/Bearish Engulfing` |
| `direction` | `direction` | `LONG`/`SHORT`/`bullish`/`bearish` in text |
| `grade` | `grade` | `A+`/`A` (never `A+++` unless literally present) |
| `event_time_utc` | `trigger_time`/`server_time_hint` | fallback `received_at_utc` (flag as receipt, not bar time) |
| `provenance` | `PARSED` | `RAW_TEXT` |

Rules:
- **Never invent** a field the payload doesn't support → leave null, flag `notes`.
- **Never** derive an order/size/route/execution field — those simply do not exist in this lane.
- Keep the **re-entry-boundary / dedupe** discipline used elsewhere (report-time dedupe on
  `(event_time, event_type, direction)`), computed offline, never discarding raw.
- Timezone: store times verbatim; normalise to UTC for comparison only (TradingView `{{time}}`/
  `{{timenow}}` are UTC; the Farouk indicator TZ field is Europe/Berlin — reconcile explicitly, never
  guess).

## What normalisation must NEVER produce

- No `execution_allowed=true`, no order/lot/account/broker/QST field derived to a truthy actionable
  value.
- No signal→action mapping. This is measurement only; it feeds the `NOT_INTEGRATION_READY` evidence
  base, not any execution path.

## Where it runs

- **Not** in the Worker (the Worker stays pure logging-only, raw-first, append-only).
- A **separate read-only report/analysis step** (Stage I) over the R2 objects — offline, no execution
  surface.
