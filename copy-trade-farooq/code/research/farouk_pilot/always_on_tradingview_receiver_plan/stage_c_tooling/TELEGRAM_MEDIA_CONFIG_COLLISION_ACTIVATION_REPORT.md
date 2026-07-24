# Telegram Media Config-Collision Fix — Activation Report

**Mode: CONTROLLED TELEGRAM PREVIEW LISTENER RESTART ONLY.** One deliberate restart to activate the
config-collision fix. No TradingView touch; no Worker deploy; no R2 check; no secret rotation; no
broker/cTrader/QST; no permit/lease/order; no gate change; **full backfill NOT run.** `NOT_INTEGRATION_READY`
unchanged. Date 2026-07-10.

## Restart

- **Old listener:** PID **81428** (`C:\Python314\python.exe -u module_a_telegram.py`) — confirmed as the
  Telegram PREVIEW listener, then **stopped** (`Stop-Process -Id 81428 -Force`). Verified gone; no
  `module_a_telegram` python left.
- **Relaunched:** same command/environment — `python -u module_a_telegram.py` (stdin `/dev/null`), single
  instance, from `C:\Users\Marty\signal-terminal`.
- **New listener:** PID **87988** (`C:\Python314\python.exe -u module_a_telegram.py`).
- **Exactly ONE** `module_a_telegram` listener running after restart. No duplicates.

## Startup banner (new process)

`PREVIEW MODE` · watching `-1001902136163` · `Listener mode : PREVIEW` · "Supported Telegram IMAGE bytes ARE
preserved … into prospective_media_v1" · "Execution disabled." · "Connected. Listening for new messages…".

## Config-collision fix — ACTIVE in the new process

Verified against the **exact live import order** (root `config` imported first, as the listener does):
- `store.CFG is not root config` → **True** (media_capture loads its own config).
- `store.CFG.PERMITTED_IMAGE_TYPES` → `('jpeg','png','webp','bmp')` (present — the AttributeError source is
  gone).
The silent-drop fix remains in place (`MEDIA_HANDLING_ERROR` allowed, resilient `record_failure`). Photo
capture should now succeed: the next photo post (or the msg-45629 backfill) should write a `<sha256>.png`
into `prospective_media_v1/` with a `MEDIA_CAPTURED` row.

## Safety confirmations

- Gates: `MODE=PAPER`, `LISTENER_MODE=PREVIEW`, `EXECUTION_ENABLED=False`, `CTRADER_EXECUTION_ENABLED=False`.
- Broker/cTrader/QST/execution **absent** (the only python process is the single PREVIEW listener). No
  permit/lease/order runtime files (data/ scanned — none).
- Only the Telegram PREVIEW listener was restarted; nothing else touched. No TradingView alert; Worker not
  deployed; R2 not checked; secret not rotated; **full backfill not run.**
- `NOT_INTEGRATION_READY` unchanged.

## Next step

Re-attempt the **one-message image backfill of msg 45629** (XAU "100 pips") via the copied-session method and
confirm `MEDIA_CAPTURED` + a `<sha256>.png` file, linked to `FP-LIVE-TRADE-OBS-003_XAUUSD`. If that captures
cleanly, the fuller image-only backfill of today's missed SOL/BTC/XAUUSD screenshots can be considered
(separately authorised). Note: the live listener PID is now **87988** (81428 retired). Observation-only.
