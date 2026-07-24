# FP-LIVE-TRADE-OBS-003_XAUUSD

**Side observation record — NOT executable, NOT in the XAUUSD shadow pipeline.** This is Farouk's
**discretionary Telegram gold call**, distinct from the mechanical TradingView Farouk-Playbook indicator
alerts; it is **not** fed to the classifier/detector/scorer/state-machine, not sized, not routed, not
executed. No trade instruction / order intent / route / lot / account / risk sizing. `NOT_INTEGRATION_READY`
unchanged.

## The trade (setup)

| field | value |
|---|---|
| record_id | FP-LIVE-TRADE-OBS-003_XAUUSD |
| telegram_message_id | 45625 |
| timestamp (UTC) | 2026-07-10T12:43:32Z |
| channel | gold-trades |
| poster | seascalperfarouk |
| instrument | XAU/USD (Gold) |
| direction | SELL / SHORT |
| entry | 4102–4115 |
| SL | 4152 |
| TP | TP1 hit (~100–200 pips reported); TP2 4077.00; TP3 4055.00 |
| sizing note (verbatim, not acted on) | "LOW LOT" |
| media | none on the setup post |

## Management / rationale / result thread (all gold-trades · seascalperfarouk)

| msg | UTC | text summary | media |
|---|---|---|---|
| 45626 | 13:08:24Z | "low risk, might push into 4125–4135" | no |
| 45627 | 13:24:06Z | "take tp1, close worst entry, hold, SL to entry" | no |
| 45628 | 13:24:33Z | (photo only) | ref, not stored |
| 45629 | 13:25:16Z | **"100 pips"** (result) | ref, not stored |
| 45630 | 13:28:45Z | (photo only) | ref, not stored |
| 45631 | 13:28:54Z | "Let's go!!! take more off" | no |
| 45632 | 13:30:11Z | **"200 pips"** (result) | ref, not stored |
| 45633 | 13:31:35Z | rationale: "lost the Asia low; 5M/15M/H1 closed below; untested Asia high; unmitigated levels" | no |
| 45634 | 13:37:10Z | "take 50% off, SL to entry" | no |
| 45635 | 13:38:32Z | **TP2 4077.00 / TP3 4055.00** | no |

- direction **SELL/SHORT** · follow-up/result: **YES** (extensive — TP1 hit, 100/200 pips, SL-to-entry,
  TP2/TP3 targets).
- media: photos **referenced but NOT stored locally** (media folder empty).

## Media backfill (2026-07-10) — XAU "100 pips" screenshot RECOVERED ✅

After the config-collision fix was activated, the one-message image backfill of **msg 45629** ("100 pips"
gold-trades result screenshot; note msg 45625 the SELL setup has **no** photo) **succeeded**:

- **capture_status:** `MEDIA_CAPTURED`
- **image file:** `prospective_media_v1/92fe92b76960bb3f195519c58686e837af0ed5367643c8a3c3bedf9317c0ec5f.jpg`
- **sha256:** `92fe92b76960bb3f195519c58686e837af0ed5367643c8a3c3bedf9317c0ec5f` (matches filename; valid JPEG)
- **byte_count:** 18601 · **msg:** 45629 · **channel:** −1001902136163 · **media_ref:** `media:MessageMediaPhoto:45629`
- recorded as a **backfill re-capture (message_revision_number = 2)** because the earlier failed revision-1
  row is append-only and cannot be superseded in place.

**This image is linked to FP-LIVE-TRADE-OBS-003_XAUUSD** as the "100 pips" result screenshot of the XAU/USD
SELL. Image-only; not interpreted, not a signal. (History: the first attempt failed with the
`module 'config' has no attribute 'PERMITTED_IMAGE_TYPES'` collision, now fixed.) The other XAU result
screenshots were then recovered in the fuller backfill (below).

### Fuller backfill — remaining XAU result screenshots recovered (all `MEDIA_CAPTURED`)

| msg | sha256 | bytes | file |
|---|---|---|---|
| 45628 | `5643fb1050dabddfd71c9362f2afd51f7afdeb73924c6650aae9acda0a51b12b` | 37058 | `prospective_media_v1/5643fb10….jpg` |
| 45630 | `359caa892ba9dde8d5e0c4d3f0b59c738c9891bbd8085c99845584983579aa1c` | 20499 | `…/359caa89….jpg` |
| 45632 | `9c5c50f03b97bf3d438caa462cbe9225796cf29f3dc62de0381f1f83ee8a474e` | 20162 | `…/9c5c50f0….jpg` |

(45629 "100 pips" captured earlier as revision 2.) All file-hash == filename verified; image-only.

## Note (cross-reference only, not merged)

The entry band 4102–4115 sits in the same ~4100–4135 Jul-10 price area as the captured TradingView structure
events, but this discretionary call is **not** merged into the shadow pipeline and **not** treated as a
signal. Observation only.
