# PHONE_ALERT_BATCH_001 — Source Location Note

Read-only note. No files moved, renamed, or altered.

## Canonical naming

- **`PHONE_ALERT_BATCH_001`** is the canonical evidence-batch name.
- **`phone_capture_001`** — **superseded wording.** It was the planned subfolder name in the earlier
  `ONLINE_RESUME_NOTICE` / `MONITORING_RESUME_STATUS` drafts. It is retained here only as an alias so
  older references resolve; do not use it going forward.

## Where the files actually are

The 10 PHONE_ALERT_BATCH_001 files live in the **top level** of:

`research/farouk_pilot/live_observations/FP-LIVE-OBSERVATION-001/FP-LIVE-OBSERVATION-001/raw/`

They are **not** in a `phone_alert_batch_001` (or `phone_capture_001`) subfolder.

## Why they were NOT relocated

The batch was already **inventoried, SHA256-hashed, and processed from these top-level `raw/` paths**.
Those exact paths are recorded in the batch reports and cross-referenced against `SOURCE_MANIFEST.json`
by hash. Moving or renaming them now would break manifest / hash / path integrity for no benefit.

- No relocation performed.
- No rename performed.
- Original paths preserved exactly as processed.

## The 10 files (PHONE_ALERT_BATCH_001), all in `raw/` top level

1. `TradingView_Alerts_Log_2026-07-06.csv` (8945c35b…)
2. `Screenshot_20260706_183055_TradingView.jpg` (c0b878c1…)
3. `Screenshot_20260706_184339_TradingView.jpg` (9b5c24e9…)
4. `Screenshot_20260706_190323_Gallery.jpg` (fca6ff24…)
5. `Screenshot_20260706_193900_TradingView.jpg` (43aab37a…)
6. `Screenshot_20260706_195926_TradingView.jpg` (135bb3da…)
7. `Screenshot_20260706_203135_TradingView.jpg` (dbe75c97…)
8. `Screenshot_20260706_203403_TradingView.jpg` (f4dde628…)
9. `Screenshot_20260706_203706_TradingView.jpg` (26c8d14a…)
10. `Screenshot_20260706_204622_TradingView.jpg` (df678b46…)

## If a subfolder is ever wanted

Any future relocation into a `PHONE_ALERT_BATCH_001/` subfolder must be a deliberate, separately
authorised step that **re-hashes and re-manifests** the moved copies — not a silent move. Until then,
the top-level `raw/` paths above are authoritative.

_Reports for this batch: `PHONE_ALERT_BATCH_001_REPORT.md`, `_EVENT_LOG.csv`, `_EVENT_LOG.jsonl`,
`_DEDUPLICATION.md`, `_A_PLUS_A_TRIPLE_PLUS_SUMMARY.md`, `_LIMITATIONS.md`._
