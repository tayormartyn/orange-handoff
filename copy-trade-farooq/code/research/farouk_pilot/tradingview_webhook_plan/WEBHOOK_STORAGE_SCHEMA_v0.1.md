# Webhook Storage Schema v0.1

**DESIGN ONLY.** Append-only storage for the logging-only receiver. Two interchangeable backends;
**JSONL recommended for the first (Stage 1) build**, SQLite as an optional structured mirror later.

## Design principles

- **Raw-first:** the exact received bytes are stored before parsing; parsing never blocks or discards
  a raw record.
- **Append-only:** inserts only. No update/delete code path. (JSONL: append a line. SQLite: `INSERT`
  only; no `UPDATE`/`DELETE` statements exist in the code.)
- **Separate from the engine:** lives under `data/tv_webhook/` — never `paper_log.csv`, the archive
  DB, or `shadow.db`.
- **Derived ≠ raw:** classification fields are derived and stored alongside; the raw payload is
  immutable.

## Required fields

| Field | Type | Source | Notes |
|---|---|---|---|
| `event_id` | string (uuid/ulid) | receiver | Assigned on receipt; primary key. |
| `received_at_utc` | string (ISO-8601 Z) | receiver clock | Server receipt time in UTC. Authoritative capture time. |
| `source` | string | constant | Always `"TradingView"`. |
| `raw_payload` | string/blob | request body | **Byte-exact** original body, stored before parsing. |
| `raw_headers_safe` | JSON object | request | Whitelist only: content-type, content-length, user-agent, request-id. **Never** secrets/cookies. |
| `symbol` | string / null | parser | e.g. `XAUUSD`. null if unparsed. |
| `feed` | string / null | parser | Exchange/feed, e.g. `PEPPERSTONE`. |
| `timeframe` | string / null | parser | e.g. `3` (3m). |
| `alert_name` | string / null | parser | e.g. `LIVE001_APLUS_XAUUSD_3M`. |
| `event_type` | string / null | parser | e.g. `A_PLUS`, `SWEEP_HIGH`, `CHOCH_DOWN`, `ENGULFING`, `BPR_TAPPED`, `ANY_ALERT`. |
| `direction` | string / null | parser | `LONG` / `SHORT` / `bullish` / `bearish` / `NA`. |
| `grade` | string / null | parser | `A` / `A+` / `NA`. (`A+++` has never been observed.) |
| `price_if_present` | number / null | parser | Trigger price if the payload carried one; else null (never invented). |
| `bar_time_if_present` | string / null | parser | Bar/trigger time from payload if present; timezone recorded verbatim, not converted. |
| `dedupe_key` | string | receiver | See below. |
| `parse_status` | enum | parser | `PARSED` / `PARTIAL` / `UNPARSED` / `UNRESOLVED_PLACEHOLDER` / `INVALID_JSON`. |
| `validation_status` | enum | receiver | `ACCEPTED` / `REJECTED_METHOD` / `REJECTED_AUTH` / `REJECTED_SIZE` / `DUPLICATE`. |
| `notes` | string / null | receiver/parser | Free-text: anomalies, unresolved placeholders, TO_VERIFY flags. |

## Dedupe key

`dedupe_key = sha256( alert_name + "|" + symbol + "|" + timeframe + "|" + bar_time_if_present + "|" + event_text_normalised )`

- Chosen so TradingView **retries** of the *same* firing collapse to one logical event, while genuine
  distinct firings (different bar time / event) stay separate — mirroring the 111→90 dedup already
  done on the CSV.
- If `bar_time_if_present` is missing, fall back to a coarse `received_at_utc` bucket (e.g. minute)
  **and** flag `notes = "dedupe_degraded_no_bar_time"` — never silently.
- Duplicates are **still stored** (append-only) with `validation_status = DUPLICATE`; they are
  excluded from distinct-event counts at report time, not dropped at ingest.

## JSONL backend (recommended first)

- One file per day: `data/tv_webhook/tv_events_YYYY-MM-DD.jsonl`.
- One JSON object per line, exactly the fields above.
- Append with `O_APPEND`; fsync per write for durability.
- Rotation by date; files are never rewritten.

## SQLite backend (optional structured mirror, later)

- `data/tv_webhook/tv_webhook.db`, WAL mode, foreign keys on, UTC timestamps.
- Table `tv_events` with the columns above; `event_id` PK; index on `dedupe_key`, `received_at_utc`,
  `alert_name`.
- **Insert-only.** No `UPDATE`/`DELETE` in code. A rebuild of derived fields (re-parse) writes a
  **new derived table**, never mutates `raw_payload`.
- Integrity check command (read-only) mirrors the archive's `integrity-check` ethos.

## What is deliberately NOT stored

- No secrets, tokens, Authorization headers, or cookies.
- No broker/account identifiers.
- No derived *decision* (no "would trade" flag) — this store records **what fired**, never **what to
  do**.
