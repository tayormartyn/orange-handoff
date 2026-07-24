# Telegram Media Backfill — One-message Test (msg 45629) — SUCCESS

**Mode: ONE MESSAGE TEST ONLY.** Image/media only; message not reprocessed as a signal. Listener PID 87988
not stopped/restarted; no second live listener (copied-session method); no TradingView/Worker/R2/secret/
broker/QST action; no permit/lease/order; no gate change; **full backfill NOT run.** `NOT_INTEGRATION_READY`
unchanged. Date 2026-07-10.

## Result — ✅ image recovered

- **Listener PID 87988:** running before and after (single instance; the copied-session download did not
  disrupt it — no AUTH_KEY_DUPLICATED).
- **msg 45629 resolved:** yes, via `get_messages(-1001902136163, ids=45629)`.
- **MessageMediaPhoto present:** yes.
- **Download:** `preserve_live` → **`MEDIA_CAPTURED`**.
- **Saved file:** `prospective_media_v1/92fe92b76960bb3f195519c58686e837af0ed5367643c8a3c3bedf9317c0ec5f.jpg`
  - **sha256:** `92fe92b76960bb3f195519c58686e837af0ed5367643c8a3c3bedf9317c0ec5f` (verified: file hash == filename)
  - **byte_count:** 18601 · valid JPEG (`ff d8 ff`)
- **media_records row:** `MEDIA_CAPTURED` written, with `content_sha256`, `byte_count`, `storage_relative_path`,
  `telegram_media_reference=media:MessageMediaPhoto:45629`. Recorded as **message_revision_number = 2**
  (backfill re-capture) — the earlier failed revision-1 row is append-only (UPDATE **and** DELETE forbidden)
  and cannot be superseded in place; a distinct revision is the append-only-respecting way to record the
  recovered image. The old revision-1 `MEDIA_DOWNLOAD_FAILED` row is left intact (history).
- **Linked to `FP-LIVE-TRADE-OBS-003_XAUUSD`** as the "100 pips" result screenshot of the XAU/USD SELL.

Confirms both fixes work live: the config-collision fix (image validates + captures) and the silent-drop fix
(failures would still record). The test ran with the exact listener import order (root `config` first).

## Method (backfill-safe)

Copied `whale_room.session` to a temp file (the live session file untouched), short-lived Telethon connect
(authorized, no login), one `get_messages` + one image download via the media pipeline, disconnect, temp
session removed. Image-only; no OCR; no text reprocessing.

## Note (append-only retry limitation)

A previously-failed media capture cannot be cleanly "retried" in place (identity-based dedup + append-only
triggers). The backfill used `revision=2` to record the recovery. A future backfill tool should adopt a
consistent supersede/revision convention for failed→recovered media.

## Safety confirmations

- Listener **PID 87988 running/untouched** (verified after); single instance; live session file untouched.
- Gates `MODE=PAPER`/`LISTENER_MODE=PREVIEW`/`EXECUTION_ENABLED=False`/`CTRADER_EXECUTION_ENABLED=False`;
  broker/cTrader/QST/execution absent; no permit/lease/order; no TradingView/Worker/R2/secret action;
  **full backfill NOT run** (only msg 45629). `NOT_INTEGRATION_READY` unchanged.

## Next step

The pipeline is proven end-to-end. Optionally authorise the **fuller image-only backfill** of the remaining
missed photos (SOL 45641; BTC 45624/45636/45638/45620; XAU 45628/45630/45632; and other channel photos),
using the same copied-session, revision-tagged, image-only method — or rely on the now-fixed live listener to
capture new photos going forward. Observation-only.
