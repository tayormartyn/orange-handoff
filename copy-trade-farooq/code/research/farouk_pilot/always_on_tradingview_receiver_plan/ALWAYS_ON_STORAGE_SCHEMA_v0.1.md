# Always-On Storage Schema v0.1 (§3)

**DESIGN ONLY.** Append-only storage for the always-on logging-only receiver. Same raw-first,
engine-separate discipline as Stage 1/2, adapted for a cloud backend.

## Required fields (one record per received request)

| Field | Type | Source | Notes |
|---|---|---|---|
| `event_id` | string (uuid/ulid) | receiver | Primary key; dedupe/idempotency anchor. |
| `received_at_utc` | ISO-8601 `Z` | server clock | Authoritative capture time (UTC). |
| `source` | string | constant | `"TradingView"`. |
| `raw_payload` | string/blob | request body | **Byte-exact**, stored before parsing. |
| `raw_headers_safe` | JSON | request | Whitelist: content-type, content-length, user-agent, request-id. **No** secrets/cookies. |
| `alert_name` | string / null | parser | e.g. `LIVE001_APLUS_XAUUSD_3M`. |
| `symbol` | string / null | parser | `{{ticker}}` → e.g. `XAUUSD`. |
| `exchange` | string / null | parser | `{{exchange}}` → e.g. `PEPPERSTONE`. |
| `timeframe` | string / null | parser | `{{interval}}` → e.g. `3` (Stage 2 test read `1`; = chart interval). |
| `trigger_price` | string/number / null | parser | `{{close}}` if present; never invented. |
| `trigger_time` | string / null | parser | `{{time}}` (Stage 2: UTC `Z`); stored verbatim. |
| `server_time_hint` | string / null | parser | `{{timenow}}` (Stage 2: UTC `Z`). |
| `event_type` | string / null | parser | A_PLUS / SWEEP_HIGH / CHOCH_DOWN / ENGULFING / BPR_TAPPED / ANY_ALERT / … |
| `direction` | string / null | parser | LONG / SHORT / bullish / bearish / NA. |
| `grade` | string / null | parser | A / A+ / NA (A+++ never observed). |
| `parse_status` | enum | parser | PARSED / PARTIAL / UNPARSED / UNRESOLVED_PLACEHOLDER / INVALID_JSON. |
| `validation_status` | enum | receiver | ACCEPTED / REJECTED_METHOD / REJECTED_PATH / REJECTED_SIZE / DUPLICATE / REJECTED_DISABLED. |
| `dedupe_key` | string | receiver | See below. |
| `provider_meta_safe` | JSON / null | receiver | **Only if safe:** e.g. request-id, edge region. **Source IP:** store only a **coarse/hashed** form if retained at all — treat as PII; default is **omit** unless there is a security reason, and never store it alongside the secret. |
| `notes` | string / null | receiver/parser | anomalies, unresolved placeholders, auth note, TO_VERIFY. |

## Dedupe key

`dedupe_key = sha256(alert_name | symbol | timeframe | trigger_time | event_text_normalised)`

- Collapses TradingView **retries** of the same firing; keeps genuinely distinct firings separate
  (mirrors the 111→90 CSV dedup and the Stage-2 behaviour).
- If `trigger_time` missing → fall back to a coarse `received_at_utc` bucket **and** flag
  `notes="dedupe_degraded_no_trigger_time"` (never silently).
- Duplicates are **stored** (append-only) with `validation_status=DUPLICATE`; excluded from distinct
  counts at report time, not dropped at ingest.

## Backend comparison

| Backend | Pros | Cons | Fit |
|---|---|---|---|
| **JSONL object storage** (append/newline objects in a bucket) | dead-simple, truly append-only, cheap, portable, matches Stage 1/2 format exactly | querying needs a read+scan; concurrent appends need per-object writes (one object per event or per day) | **Recommended first** — write one object per event keyed by `event_id`, or append to a daily object; identical mental model to the local JSONL |
| **SQLite** (on a VPS) | rich queries, single file, WAL | needs a host (Option B), not ideal for serverless (no persistent local disk) | good for Option B VPS only |
| **Small hosted database** (managed Postgres/row store) | queryable, durable, indexes | a standing dependency + credential to manage; overkill at this volume | later, if analysis needs SQL |
| **Cloud table / KV store** | managed, cheap, serverless-native | KV overwrites by key → **must key on unique `event_id`** to stay append-only; scans limited | good with Option A/C — key strictly on `event_id` |

**Recommendation:** start with **append-only JSONL in object storage** (one object per event, name =
`event_id`, or a per-day append object) — it preserves the exact raw-first, append-only guarantee and
is portable to SQL later without losing the raw record. A managed table/KV is a fine alternative on
Option A/C **provided** records are keyed on `event_id` so nothing is overwritten.

## Retention & privacy

- **Raw payloads** are evidence — retain append-only; never edit.
- **Source IP / provider metadata:** default **omit**; if kept for security, store **coarse or
  hashed**, never next to the secret, and document why. It is not needed for the capture goal.
- No secrets, tokens, cookies, or account identifiers are ever stored.
- No derived *decision* (no "would-trade" flag) — the store records **what fired**, never **what to
  do**.
