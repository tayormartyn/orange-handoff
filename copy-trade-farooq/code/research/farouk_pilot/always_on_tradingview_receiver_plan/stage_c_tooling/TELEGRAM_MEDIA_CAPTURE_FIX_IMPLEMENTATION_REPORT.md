# Telegram Media Capture Fix — Implementation Report

**Mode: TELEGRAM MEDIA CAPTURE FIX IMPLEMENTATION + TESTS ONLY.** Offline code + tests. The running
listener was **not** restarted or modified; PID 16608 untouched. No broker/cTrader/QST; no permit/lease/order;
no gate change; no TradingView touch; Worker not deployed; R2 not accessed. `NOT_INTEGRATION_READY` unchanged.
Date 2026-07-10.

## Files changed (all under `campaign_extractor/media_capture/` only)

1. **`media_db.py`** — added `MEDIA_HANDLING_ERROR` to `STATUSES` **and** the `media_records` CHECK
   constraint (so new DBs accept it).
2. **`store.py`** — `record_failure` made **resilient**: it tries the requested status, and on any append
   rejection (e.g. an older DB whose CHECK predates the status) **falls back to an allowed status**, preserving
   the true status + reason in `failure_reason`. It **never raises and never silently drops**.
3. **`live_adapter.py`** — (a) `build_descriptor` photo-size loop wrapped **defensively** (a malformed size
   object can no longer crash descriptor building; `classify` still yields PHOTO on empty sizes); (b) new
   `_err(e)` helper captures the **real error message** (bounded, safe) so a failure row self-diagnoses;
   (c) `preserve_live` now records `_err(e)` and — because `record_failure` is resilient — a handling error is
   **recorded, not dropped**. The sanctioned **`iter_download`** streaming primitive is kept (the forbidden
   `download_media`/`telethon` guard still passes).
4. **`tests/test_media_capture_photo_fix.py`** — new (8 tests).

`module_a_telegram.py` (the running listener) was **NOT modified** (mtime unchanged, 2026-07-03).

## Exact root cause fixed

- **Silent drop (definitive, offline-reproduced):** on a photo error, `preserve_live` called
  `record_failure(..., "MEDIA_HANDLING_ERROR", ...)`, but `"MEDIA_HANDLING_ERROR"` was **not in the
  `media_records` CHECK constraint** → `sqlite3.IntegrityError` → the failure recorder itself threw → the
  function returned a string and **wrote no row and no file**. That is why the photos left **no trace** (while
  webpages, which exit early via the UNSUPPORTED branch, were recorded). **Fixed:** the status is now allowed
  (new DBs) **and** `record_failure` falls back on any rejection (existing prod DB) — failures are always
  recorded.
- **Primary photo `AttributeError` (Bug A):** live-Telethon-object-specific; **not** in the sanctioned
  `iter_download` path (a download error is separately caught and recorded as `MEDIA_DOWNLOAD_FAILED`), and
  not reproducible with clean mocks. It is now (i) **less likely** (defensive `build_descriptor`) and (ii)
  **self-diagnosing** — on the next live run it will produce a recorded `MEDIA_HANDLING_ERROR` /
  `MEDIA_DOWNLOAD_FAILED` row carrying the actual exception message, instead of a silent loss.

## Tests added (8) + results

`test_media_capture_photo_fix.py` — **8/8 PASS**:
- `test_photo_captured_to_disk_with_provenance` — MessageMediaPhoto → `MEDIA_CAPTURED`, `<sha256>.png` on
  disk, row has `content_sha256` / `byte_count` / `storage_relative_path` / `telegram_media_reference`.
- `test_iter_download_error_is_recorded_not_dropped` — `iter_download` raising is recorded
  (`MEDIA_DOWNLOAD_FAILED`) with the real `AttributeError` message.
- `test_failure_path_records_a_row_not_silent` — a failing download yields a recorded row (never dropped).
- `test_record_failure_media_handling_error_is_allowed_now` — new DB records `MEDIA_HANDLING_ERROR`.
- `test_record_failure_resilient_against_old_narrow_check` — simulated **old** DB (narrow CHECK): the failure
  still writes a row (fallback), true status preserved in `failure_reason`.
- `test_webpage_still_unsupported` — webpages/link previews still `UNSUPPORTED_MEDIA_TYPE`.
- `test_descriptor_defensive_on_bad_size_object` — a size object that raises on attribute access does not
  crash `build_descriptor`.
- `test_no_forbidden_imports_in_media_capture` — no `broker/ctrader/qst/execution/order/permit/lease/module_b/
  demo_executor/risk` import anywhere in `media_capture/` (no execution surface).

**Regression:** existing `test_phase2a.py` **17/17** and `test_phase2b.py` **5/5** still pass (incl. the guard
that forbids `download_media`/`telethon`/OCR/vision references in `live_adapter.py`). Text path unaffected.

## Storage / naming / hash / provenance (unchanged, now written)

Content-addressed `<sha256>.<ext>` under `prospective/data/prospective_media_v1/`; `media_records` row with
`content_sha256`, `byte_count`, `storage_relative_path`, `telegram_media_reference`, timestamps, schema
version; 10 MiB streaming cap; image-only (jpeg/png/webp/bmp); no OCR/vision/interpretation.

## Restart requirement + activation

- **A listener RESTART IS STILL REQUIRED** to activate the fix — PID 16608 holds the old `media_capture`
  bytecode; the running process was **not** restarted or modified.
- The fix is committed to the files and fully tested offline. **Next:** Martyn does one deliberate,
  authorised PREVIEW-listener restart to activate it (rollback = revert these 3 `media_capture` files +
  restart; text-only PREVIEW is unaffected either way). Optional, separate: an image-only **backfill** of the
  already-missed photos (message IDs preserved) once the fix is live.

## Safety confirmations

- Changes confined to `media_capture/` (media pipeline); image-only; no broker/QST/cTrader/execution/order/
  permit/lease code or imports introduced (asserted by test).
- Listener **PID 16608 running/untouched**; not restarted; gates `PAPER/PREVIEW/False/False`;
  `NOT_INTEGRATION_READY` unchanged. No TradingView/Worker/R2 action.
