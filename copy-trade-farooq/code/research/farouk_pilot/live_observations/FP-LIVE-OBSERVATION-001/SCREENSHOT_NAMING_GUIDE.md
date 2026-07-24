# SCREENSHOT NAMING GUIDE

Store under `FP-LIVE-OBSERVATION-001/screenshots/`. Do not modify/rename source captures after logging.

## Convention
`<step>_<phase>_<obsid-or-context>_<UTCyyyymmddThhmmZ>.png`

## Fixed context captures
- `01_chart_feed_verification_<UTC>.png`
- `02_chart_timezone_<UTC>.png`
- `03_indicator_config_snapshot_<section>_<UTC>.png` (inputs/style/visibility)
- `04_alert_setup_<condition>_<UTC>.png` (dialog BEFORE Create)

## Per-observation captures (obsid = FP-LO1-NNN)
- `05_preclose_<obsid>_<UTC>.png`
- `06_close_<obsid>_<UTC>.png`
- `07_plus1_<obsid>_<UTC>.png`
- `08_plus5_<obsid>_<UTC>.png`
- `09_message_<obsid>_<UTC>.png`  (verbatim notification/alert-log)
- `10_panel_<obsid>_<UTC>.png`
- `11_duplicate_<obsid>_<UTC>.png` (only if a duplicate occurs)
- `12_grade_<obsid>_<UTC>.png` (grade appearance/change)

## Rules
- Timestamps in **UTC** in the filename; also note the chart TZ inside the record.
- One event → its own obsid; reuse the same obsid across its 05–12 captures.
- SHA256 each screenshot into the run log if provenance matters (optional but recommended).
