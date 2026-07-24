# Telegram Media Image-only Backfill — Today's Missed Trade Photos

**Mode: IMAGE-ONLY BACKFILL — TODAY'S MISSED TRADE PHOTOS ONLY.** Image/media only; no message reprocessed
as a signal; **not classified as trading candidates**; no outcome matching / scoring. Listener PID 87988 not
stopped/restarted; no second live listener (copied-session method); no TradingView/Worker/R2/secret/broker/QST
action; no permit/lease/order; no gate change. `NOT_INTEGRATION_READY` unchanged. Date 2026-07-10.

## Result — 8/8 recovered (plus msg 45629 earlier) = 9 total

- **Listener PID 87988:** running before and after (single instance; copied-session download did not disrupt
  it — no AUTH_KEY_DUPLICATED; live session file untouched).
- All 8 targets **resolved**, all had **MessageMediaPhoto**, all **downloaded → `MEDIA_CAPTURED`** (revision 1,
  clean — no prior rows), files content-addressed and **hash-verified on disk**.

| record | msg | status | sha256 | bytes |
|---|---|---|---|---|
| **FP-LIVE-TRADE-OBS-001_SOL** | 45641 | MEDIA_CAPTURED | `62ee913e21b1114590d25183a6c8d65a33de46290e76f12fdcd5e8eda89cd28b` | 158438 |
| **FP-LIVE-TRADE-OBS-002_BTC** | 45624 | MEDIA_CAPTURED | `70f3446e29ce0050660117afd5d2d11d1e6386166ae70b5ceec9be6187be2fc3` | 167370 |
| FP-LIVE-TRADE-OBS-002_BTC | 45636 | MEDIA_CAPTURED | `7f0900ab87a68aa017f944ec11e667ccda87d727f1eb968e940251ed7a9ba2e8` | 208763 |
| FP-LIVE-TRADE-OBS-002_BTC | 45638 | MEDIA_CAPTURED | `f59f3e1b4bd24bf697da6ef8d51f1e525b5417fbdf9ed59bfe92264b9b41b444` | 131423 |
| FP-LIVE-TRADE-OBS-002_BTC | 45620 | MEDIA_CAPTURED | `9731ae83d92cf99eb365c2bd82ba9ceae5dbcd87ec653d9652111482c397d97c` | 367056 |
| **FP-LIVE-TRADE-OBS-003_XAUUSD** | 45628 | MEDIA_CAPTURED | `5643fb1050dabddfd71c9362f2afd51f7afdeb73924c6650aae9acda0a51b12b` | 37058 |
| FP-LIVE-TRADE-OBS-003_XAUUSD | 45630 | MEDIA_CAPTURED | `359caa892ba9dde8d5e0c4d3f0b59c738c9891bbd8085c99845584983579aa1c` | 20499 |
| FP-LIVE-TRADE-OBS-003_XAUUSD | 45632 | MEDIA_CAPTURED | `9c5c50f03b97bf3d438caa462cbe9225796cf29f3dc62de0381f1f83ee8a474e` | 20162 |
| FP-LIVE-TRADE-OBS-003_XAUUSD | 45629 (earlier, rev 2) | MEDIA_CAPTURED | `92fe92b76960bb3f195519c58686e837af0ed5367643c8a3c3bedf9317c0ec5f` | 18601 |

- Files saved under `campaign_extractor/prospective/data/prospective_media_v1/<sha256>.jpg` (content-addressed,
  write-once). `media_records` `MEDIA_CAPTURED` rows written with `content_sha256`, `byte_count`,
  `storage_relative_path`, `telegram_media_reference`. **9 MEDIA_CAPTURED rows / 9 files total.**
- **Failures:** none. (The one earlier failure — msg 45629 revision 1 — remains recorded/untouched per
  append-only; its recovery is the revision-2 row.)

## Links to side evidence records

- SOL → `FP-LIVE-TRADE-OBS-001_SOL` (45641).
- BTC → `FP-LIVE-TRADE-OBS-002_BTC` (45624, 45636, 45638, 45620).
- XAUUSD → `FP-LIVE-TRADE-OBS-003_XAUUSD` (45628, 45630, 45632, and 45629 earlier).
- **SOL / BTC kept separate from XAUUSD** — three distinct records; **no** classification, detection, scoring,
  outcome matching, or state-machine run on any of them.

## Method (backfill-safe)

Copied `whale_room.session` → temp (live session untouched); one short-lived Telethon connection; per message:
`get_messages(id)` → image-only download via the media pipeline → disconnect; temp session removed. No OCR; no
text reprocessing.

## Safety confirmations

- Listener **PID 87988 running/untouched**; single instance; live session file untouched.
- Append-only history preserved (no UPDATE/DELETE of any prior row).
- No outcome matching / candidate scoring / state-machine run. Images are evidence only.
- Gates `MODE=PAPER`/`LISTENER_MODE=PREVIEW`/`EXECUTION_ENABLED=False`/`CTRADER_EXECUTION_ENABLED=False`;
  broker/cTrader/QST/execution absent; no permit/lease/order; no TradingView/Worker/R2/secret action.
  `NOT_INTEGRATION_READY` unchanged.

## Next step

All of today's known missed trade screenshots are recovered. Going forward the fixed live listener (PID 87988)
captures new photos automatically. If desired later, other channel photos from today (e.g. quant-flow/
institutional albums 45609–45623, 45640) could be backfilled the same way — but that is beyond the named trade
targets and out of scope here. Observation-only; no scoring.
