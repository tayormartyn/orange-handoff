# Gate G — Raw Payload Capture Record

**2026-07-09.** Confirms raw Farouk alert text was captured byte-exact.

## Payload shape

- **Raw text (not JSON)** → `parse_status: INVALID_JSON`. The ANY_ALERT alert is `alert()`-based; the
  webhook body is the indicator's own message string. **Raw is the source of truth** and is preserved
  byte-exact in `raw_payload`.

## Sampled raw_payload values (verbatim)

| received_at_utc | raw_payload |
|---|---|
| 2026-07-08T23:48:03Z | `Farouks Playbook: CHoCH DOWN on XAUUSD 3` |
| 2026-07-08T23:57:02Z | `Farouks Playbook: BPR tapped on XAUUSD 3` |
| 2026-07-09T00:03:01Z | `Farouks Playbook: CHoCH UP on XAUUSD 3` |
| 2026-07-09T04:00:00Z | `Farouks Playbook: CHoCH UP on XAUUSD 3` |
| 2026-07-09T04:12:01Z | `Farouks Playbook: A LONG on XAUUSD 3` |
| 2026-07-09T04:12:01Z | `Farouks Playbook: Bullish Engulfing on XAUUSD 3` |
| 2026-07-09T04:15:05Z | `Farouks Playbook: Bearish Engulfing on XAUUSD 3` |
| 2026-07-09T07:48:01Z | `Farouks Playbook: A SHORT on XAUUSD 3` |

## Field extraction (candidate-only, offline — NOT done in the Worker)

- The Worker stores raw + `received_at_utc` + safe headers only; it does not parse the Farouk text.
- Later offline normalisation (read-only) can extract candidate `event_type`/`direction` from the text
  (A SHORT → event A, direction SHORT; Bearish Engulfing → ENGULFING/bearish; CHoCH UP/DOWN; BPR tapped)
  — **observation only, no execution interpretation** (see `RAW_ALERT_NORMALISATION_PLAN.md`).

## Integrity

- Raw preserved byte-exact; `received_at_utc` present (UTC); `path` redacted (secret not stored);
  0 secret occurrences in sampled objects.
