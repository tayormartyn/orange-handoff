# Telegram Media Capture Fix Plan (design/diagnosis — no changes made)

**Mode: TELEGRAM MEDIA CAPTURE FIX PLAN ONLY.** Read-only diagnosis + plan. The running listener was **not**
modified or restarted; no broker/cTrader/QST; no permit/lease/order; no gate change; no TradingView touch.
PREVIEW-only behaviour preserved. `NOT_INTEGRATION_READY` unchanged.

## Diagnosis (read-only, from code + DB + the listener's own log)

- Media capture **is enabled**: `media_capture/config.py` → `TELEGRAM_MEDIA_CAPTURE_ENABLED = True`, and the
  PID 16608 startup banner printed "Supported Telegram IMAGE bytes ARE preserved…".
- **Photos are NOT being downloaded.** `prospective_media_v1/` is empty; `prospective_media_v1.db` has only
  **12 `UNSUPPORTED_MEDIA_TYPE`** rows — all **`MessageMediaWebPage`** (link previews, correctly unsupported).
  Today's trade **photos (`MessageMediaPhoto`)** have **no media record at all**.
- **Root cause (from the listener stdout log):** every photo prints
  **`[media] MEDIA_HANDLING_ERROR:AttributeError`** — 24× in this run (+1 `UNSUPPORTED_MEDIA_TYPE` webpage).
  In `media_capture/live_adapter.py::preserve_live`, an **`AttributeError` in the photo path** is caught by
  the outer `except` (line ~90); it then calls `STORE.record_failure(...)`, **which itself raises** (contained
  at line ~94), so the function returns the string `"MEDIA_HANDLING_ERROR:AttributeError"` and **writes no
  DB row and no file** — a **silent drop**. (Webpages survive because they return early via the `UNSUPPORTED`
  branch before the photo-specific code.)
- Note: the AttributeError is **not** in `stream_download` (that path is separately caught → would record
  `MEDIA_DOWNLOAD_FAILED`). It is in the non-download portion — `build_descriptor` / `classify` /
  `media_db.exists` / `preserve_bytes` — **and** the fallback `record_failure`→`media_db.append(_rec(...))`
  raises the same class. Exact attribute is to be pinned by the diagnostic test below (do not guess the line).

## Impact

- Text evidence is **fully intact** (photos never block text — by design). Only the **image bytes** were not
  preserved. Today's trade screenshots (SOL/BTC/XAUUSD posts) reference photos that were **not stored**.

## Smallest safe fix

1. **Pin the exact AttributeError (offline diagnostic test).** Add a test that feeds a realistic
   Telethon-photo-shaped object (as `tests/test_phase2b.py` already mocks `MessageMediaPhoto`/`_Photo`/`_Size`)
   through `preserve_live` with a stub client/`media_db`, and asserts the current behaviour reproduces
   `MEDIA_HANDLING_ERROR:AttributeError`. Capture the traceback to identify the offending attribute.
2. **Targeted one-line-class fix** in `media_capture/` only (no trading code touched) — e.g. correct the
   attribute/API access the traceback names (candidates: the `client.iter_download(message.media)` arg vs
   `download_media`, a `PhotoSizeProgressive` size access, or an `_rec(...)`/`media_db.append` field). Fix the
   specific attribute; change nothing else.
3. **Harden the fallback so a failure is NEVER silently dropped** (resilience): make `record_failure`’s
   `_rec(...)` construction defensive so `MEDIA_HANDLING_ERROR` is always at least recorded (a row with
   status + reason), even when the primary path errors. This guarantees future issues are visible in the
   media DB, not just stdout.
4. Confine ALL edits to `campaign_extractor/media_capture/` (`live_adapter.py` / `store.py` / `media_db.py`).
   **Do not touch** `module_a_telegram.py`’s trading handoff, gates, recorder, or the text path.

## PREVIEW-only + no-broker guarantees (unchanged by the fix)

- **Image bytes only.** No OCR, no vision, no interpretation, no parsing, no signal handoff (the module_b
  handoff stays commented/disabled). The fix only makes existing byte-preservation work.
- **No broker/execution surface introduced** — `media_capture/` imports stdlib + Telethon only; no
  broker/cTrader/QST/order/permit/lease code. Media failure never affects the text row or gates.
- Gates stay `PAPER/PREVIEW/False/False`; `NOT_INTEGRATION_READY` unchanged.

## Storage / naming / hash / provenance / metadata (existing scheme — fix just makes it write)

- **Path:** `campaign_extractor/prospective/data/prospective_media_v1/` (isolated from every text/evidence DB).
- **Naming:** content-addressed **`<sha256>.<ext>`** (`store.py`: `f"{sha}.{ext}"`), ext from sniffed image
  type (`jpg/png/webp/bmp`; GIF/animation excluded). Write-once, atomic, path-jail checked.
- **Hash/provenance:** `content_sha256` + `storage_relative_path` + `telegram_media_reference`
  (`media:MessageMediaPhoto:<id>`) + `content-addressed` dedup (`media_db.exists`).
- **Metadata (`media_records` schema, already present):** `platform, channel_id, message_id,
  message_revision_number, grouped_media_id, media_index, media_type, mime_type, safe_extension, byte_count,
  content_sha256, storage_relative_path, capture_status, failure_reason, telegram_posted_at_utc,
  listener_received_at_utc, media_download_started/completed_at_utc, schema_version, created_at`.
- Size cap 10 MiB (streaming), album cap 10 — unchanged.

## Tests

- **Reproduction:** the diagnostic test above (asserts current `MEDIA_HANDLING_ERROR:AttributeError`).
- **Fix verification:** a mock `MessageMediaPhoto` + a stub client whose `iter_download`/`download` yields
  valid JPEG/PNG bytes → `preserve_live` returns **`CAPTURED`**, a file `<sha256>.jpg` exists, and a
  `media_records` row has `capture_status=CAPTURED`, correct `content_sha256`, `byte_count`,
  `storage_relative_path`, `telegram_media_reference`.
- **Resilience:** force an error in the primary path → assert a `MEDIA_HANDLING_ERROR` **row is recorded**
  (never a silent drop).
- **Regression:** existing `tests/test_phase2a.py` + `test_phase2b.py` still pass (UNSUPPORTED webpage/video
  still recorded; dedup/atomic/size-cap/allowlist unchanged); text path unaffected.

## Restart requirement (task 8)

- **A listener RESTART IS REQUIRED** for the fix to take effect. Python has the current (buggy) `live_adapter`
  bytecode loaded in PID 16608; editing the file does **not** hot-reload it. Per the hard rules, the running
  listener is **not** modified or restarted here.
- **No-restart-now plan:** implement + test the fix **offline in the files** (all green), then hand to Martyn;
  the fix activates only on the **next deliberate, Martyn-authorised restart** of the PREVIEW listener
  (rollback = revert the media_capture edits and restart; text-only PREVIEW is unaffected either way).
- **Backfill (optional, separate authorised step):** the missed photos are still on Telegram (message IDs
  preserved, e.g. 45620/45624/45636/45638/45641 in channel −1001902136163). A **read-only, image-only**
  backfill script (using the same store, a short authorised Telegram connection) can re-fetch and preserve
  them after the fix — no re-processing of text, no interpretation. Not part of the minimal fix.

## Safety confirmations

- Read-only diagnosis; **no code changed, listener not restarted/modified**; evidence/media DBs not modified.
- No broker/cTrader/QST; no permit/lease/order; no TradingView touch; Worker not deployed; R2 not accessed.
- Telegram PREVIEW listener **PID 16608 running/untouched**; gates `PAPER/PREVIEW/False/False`.
  `NOT_INTEGRATION_READY` unchanged.

## Next step

Get approval to implement the fix (steps 1–4) offline with the tests above; then Martyn does one deliberate
listener restart to activate it, and (optionally) authorises the image-only backfill for today's missed trade
screenshots. Until then, PREVIEW text capture continues unaffected.
