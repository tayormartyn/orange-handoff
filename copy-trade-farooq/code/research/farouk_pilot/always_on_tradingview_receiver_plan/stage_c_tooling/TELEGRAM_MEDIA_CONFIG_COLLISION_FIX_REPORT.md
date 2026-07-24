# Telegram Media Capture — Config-Collision Fix Report

**Mode: CONFIG COLLISION FIX + TESTS ONLY.** Offline code + tests. The running listener (PID 81428) was
**not** restarted or modified. No TradingView/Worker/R2/secret/broker/QST action; no permit/lease/order; no
gate change; **full backfill NOT run**; no message reprocessed as a signal. `NOT_INTEGRATION_READY` unchanged.
Date 2026-07-10.

## Exact collision fixed

`media_capture/store.py` (and the offline tools `pipeline.py`, `run_phase2a.py`) used a **bare
`import config as CFG`**. When the listener has already imported the **root** `signal-terminal/config.py`
(MODE/gates), `sys.modules['config']` is that root module — which has **no image settings** — so the media
store received the wrong module and raised `AttributeError: module 'config' has no attribute
'PERMITTED_IMAGE_TYPES'` on every photo. (Isolated tests passed because root config was never imported there.)

**Fix:** load media_capture's own config **by file path under a unique module name**, immune to the
`sys.modules['config']` collision and independent of import style:
```python
import importlib.util as _ilu
_cfgspec = _ilu.spec_from_file_location("media_capture_config", os.path.join(_HERE, "config.py"))
CFG = _ilu.module_from_spec(_cfgspec); _cfgspec.loader.exec_module(CFG)
```
`store`/`media_db`/`_util` have **no** root-level counterpart, so only `config` needed fixing.

## Files changed (all under `campaign_extractor/media_capture/`)

1. `store.py` — collision-proof `CFG` load (the live path).
2. `pipeline.py` — same (offline batch tool).
3. `run_phase2a.py` — same (offline runner).
4. `tests/test_media_capture_photo_fix.py` — +3 collision tests.

Not changed this step: `live_adapter.py`, `media_db.py`. The **previous silent-drop fix is preserved**
(`MEDIA_HANDLING_ERROR` still in `STATUSES`; `record_failure` still resilient; `_err` still present) —
verified by direct import.

## Direct confirmation (exact live import order)

`import config` (root, no `PERMITTED_IMAGE_TYPES`) → then `from media_capture import store` →
`store.CFG.PERMITTED_IMAGE_TYPES == ('jpeg','png','webp','bmp')` and `store.CFG is not root config`.
**Collision defeated = True.**

## Tests added/updated + results

`test_media_capture_photo_fix.py` — **11/11 PASS** (8 prior + 3 new):
- `test_root_config_lacks_image_settings_and_media_config_has_them` — root config lacks the image settings;
  `store.CFG` has them and is a different module.
- `test_store_config_survives_reload_with_root_config_shadowing` — with `sys.modules['config']` = root,
  reloading `store` still resolves media_capture config.
- `test_photo_capture_works_even_with_root_config_shadowing` — end-to-end: with root config shadowing, a
  MessageMediaPhoto **captures** (`MEDIA_CAPTURED`) — would have been `MEDIA_HANDLING_ERROR` before.
- (retained) photo→disk w/ sha256+provenance; iter_download error recorded not dropped; failure records a
  row; `MEDIA_HANDLING_ERROR` allowed; resilient against old narrow CHECK; webpage still UNSUPPORTED;
  defensive descriptor; no forbidden broker/execution imports.

**Regression:** `test_phase2a.py` **17/17**, `test_phase2b.py` **5/5** still pass (incl. the guard forbidding
`download_media`/telethon/OCR in `live_adapter.py`). Text path untouched.

## Root project config safety

The media pipeline can **never** use the root `config.py` for image settings — it loads
`media_capture/config.py` explicitly by path under `media_capture_config`. The root `config` (MODE/gates) is
unaffected.

## Restart requirement

- **A listener RESTART IS STILL REQUIRED** to activate — PID 81428 holds the pre-fix `media_capture` bytecode;
  it was **not** restarted or modified. With this fix, on the next restart a photo post should write a
  `<sha256>.png` + `MEDIA_CAPTURED` row (the AttributeError is gone), and the msg-45629 backfill should
  succeed.

## Safety confirmations

- Changes confined to `media_capture/` (image pipeline); no broker/QST/cTrader/execution/order/permit/lease
  imports (asserted by test). Listener **PID 81428 running/untouched**; single instance.
- Gates `MODE=PAPER`/`LISTENER_MODE=PREVIEW`/`EXECUTION_ENABLED=False`/`CTRADER_EXECUTION_ENABLED=False`;
  broker/QST/execution absent; no permit/lease/order; no TradingView/Worker/R2/secret action; full backfill
  not run. `NOT_INTEGRATION_READY` unchanged.

## Next step

One **authorised** PREVIEW-listener restart to activate (stop PID 81428, relaunch `python -u
module_a_telegram.py`), then re-attempt the **one-message backfill of msg 45629** (XAU "100 pips") and confirm
`MEDIA_CAPTURED` + a `<sha256>.png` file; only then consider the fuller image-only backfill. Rollback = revert
these `media_capture` files + restart.
