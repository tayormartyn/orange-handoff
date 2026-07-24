# Gate G — R2 Object Write Record (PASSED)

**2026-07-09.** Many Gate G objects written (real Farouk mirror), verified via temp read-only list.

| Field | Value |
|---|---|
| Baseline count | 4 (Gate D + 2 Gate E + 1 Gate F) |
| Post-capture count | **73** |
| New Gate G objects | **69** |
| Date span of new objects | 2026-07-08 (~9) + 2026-07-09 (~60) |
| Bucket | `farouk-tv-webhook-evidence-v1` |

## Characteristics (from sample; representative of all 69)

- `validation_status: ACCEPTED` (all sampled).
- `parse_status: INVALID_JSON` (raw Farouk `alert()` text, not JSON).
- `received_at_utc` present, UTC `Z`; span ~2026-07-08T23:48Z → 2026-07-09T07:48Z+ (still growing until
  the duplicate is disabled).
- `path: /tv/<redacted>` (secret NOT stored); grep for secret across sample = 0.
- Append-only, unique event_id keys → no overwrite. Distinct events (report-time dedupe applies offline;
  nothing discarded at ingest).

## Note on volume

The mirror duplicates the **ANY_ALERT composite**, which fires on every Farouk event → 69 captures over
~10h. This is expected for that alert. Disable the duplicate to stop growth (Gate H governs ongoing
capture). All objects intact; Gate D/E/F objects unchanged.
