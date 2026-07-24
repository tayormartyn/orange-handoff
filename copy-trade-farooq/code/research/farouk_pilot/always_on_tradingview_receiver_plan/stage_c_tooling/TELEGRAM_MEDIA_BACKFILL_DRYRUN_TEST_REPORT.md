# Telegram Media Image-only Backfill — Dry-run + One-message Test Report

**Mode: DRY-RUN + ONE MESSAGE TEST ONLY.** Image/media only. No message reprocessed as an executable signal.
Listener PID 81428 not stopped/restarted; no second listener; no TradingView/Worker/R2/secret/broker/QST
action; no permit/lease/order; no gate change; **full backfill NOT run.** `NOT_INTEGRATION_READY` unchanged.
Date 2026-07-10.

## 1. Listener

- PID **81428** confirmed running before **and after** the test (exactly one listener; the copied-session
  test did **not** disrupt it — no AUTH_KEY_DUPLICATED).

## 2. Reference sufficiency

- **Sufficient.** All messages carry `telegram_channel_id = -1001902136163` + a `telegram_message_id`, and a
  `media_reference_or_hash`. `client.get_messages(channel, ids=...)` resolved the target message fine.

## 3. Dry-run photo inventory (read-only; NO downloads)

| msg | time (UTC) | has MessageMediaPhoto? |
|---|---|---|
| 45641 (SOL LONG) | 15:16:51 | ✅ PHOTO |
| 45624 (BTC ride) | 10:31:51 | ✅ PHOTO |
| 45636 (BTC target hit) | 14:05:38 | ✅ PHOTO |
| 45638 (BTC Short) | 14:09:18 | ✅ PHOTO |
| 45620 (BTC liq. commentary) | 06:30:53 | ✅ PHOTO |
| **45625 (XAU/USD SELL setup)** | 12:43:32 | ❌ **NO media** |
| XAU thread 45628 / 45629 / 45630 / 45632 | 13:24–13:30 | ✅ PHOTO (gold-trades result screenshots) |

(Many other channel photos today too, e.g. 45609–45623 quant-flow/institutional albums, 45640 quant-flow.)

## 4–5. One-message test download (msg 45629, XAU "100 pips") — FAILED, image NOT saved

- Method: **copied** `whale_room.session` to a temp file (live session file untouched), short-lived
  Telethon connect (authorized, no login), `get_messages(45629)`, download via the media pipeline, disconnect,
  temp session removed.
- **Result: `MEDIA_HANDLING_ERROR` — no image downloaded, no file written** (sha256 = None, path = None).
- **BUT the fix worked as intended:** the failure is now **recorded, not silently dropped** — `media_records`
  has a row for msg 45629: `capture_status=MEDIA_DOWNLOAD_FAILED`,
  `failure_reason="MEDIA_HANDLING_ERROR:AttributeError: module 'config' has no attribute
  'PERMITTED_IMAGE_TYPES' [fallback:IntegrityError]"`.

### Root cause of the persistent photo failure (now pinpointed)

**Module-name collision.** `media_capture/store.py` (and siblings) use a bare `import config as CFG`. When the
listener has already imported the **root** `signal-terminal/config.py` (MODE/gates), `sys.modules['config']`
is the root config — which has no `PERMITTED_IMAGE_TYPES` — so the media store receives the wrong module and
raises `AttributeError`. This is why isolated tests pass (media_capture on `sys.path`, root config not
imported) but the **live listener and the backfill both fail**.

**Correction to the prior "activation" status:** the earlier restart activated the *silent-drop* fix (Bug B),
which makes failures visible — but it did **not** enable photo capture, because this `config` collision (the
real Bug A) still blocks every photo. Photo capture (live and backfill) remains broken until the collision is
fixed.

## 6. Side-record link

- No image was recovered, so **nothing is linked** to `FP-LIVE-TRADE-OBS-003_XAUUSD` yet; a diagnostic note
  was added to that record instead.

## 7. Full backfill

- **NOT run** (and it cannot succeed until the config collision is fixed).

## Safety confirmations

- Image/media path only; no message reprocessed as a signal; no OCR.
- Listener **PID 81428 running/untouched** (verified after the test); single instance; live session file
  untouched (temp copy used and removed).
- Gates `MODE=PAPER`/`LISTENER_MODE=PREVIEW`/`EXECUTION_ENABLED=False`/`CTRADER_EXECUTION_ENABLED=False`;
  broker/cTrader/QST/execution absent; no permit/lease/order; no TradingView/Worker/R2/secret action.
  `NOT_INTEGRATION_READY` unchanged.

## Next step

**Fix the `config`-module collision in `media_capture/`** (make `store.py`/`media_db.py` load
`media_capture/config.py` explicitly — e.g. import it by file path under a unique name, or a guarded
package-relative import — so it never resolves to the root `config`). Re-run the offline tests, then do one
authorised listener restart to activate, and **re-attempt the one-message backfill of msg 45629**. Only after
that captures cleanly should the fuller image-only backfill be considered. All image-only, observation-only.
