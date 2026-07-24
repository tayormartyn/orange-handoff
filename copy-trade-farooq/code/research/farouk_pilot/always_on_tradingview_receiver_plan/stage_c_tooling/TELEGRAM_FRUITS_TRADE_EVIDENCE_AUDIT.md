# Telegram / Fruits (Farouk) Trade Evidence Audit — 2026-07-10

**Mode: READ-ONLY TELEGRAM EVIDENCE AUDIT ONLY.** Observation only. **These are discretionary Telegram trade
posts, NOT executable signals and NOT Farouk-Playbook-indicator alerts.** They are **NOT** fed into the
XAUUSD shadow pipeline (classifier/detector/scorer/state-machine) and **NOT** interpreted, sized, routed or
executed. No trade instruction / order intent / broker route / lot size / account id / risk sizing.
`NOT_INTEGRATION_READY` unchanged.

## Source

- Store: `campaign_extractor/prospective/data/prospective_evidence_v1.db` (table
  `prospective_message_evidence`, 269 rows; range 2026-06-29 → 2026-07-10).
- **Today (2026-07-10): 34 messages; 16 mention SOL/BTC/XAUUSD/Gold.** Read-only SQLite query; nothing
  modified.
- Media: message rows reference photos (`media:MessageMediaPhoto:<id>`), **but no media bytes are stored
  locally** — `prospective_media_v1/` is **empty (0 files)** and `prospective_media_v1.db` logged only 12
  `UNSUPPORTED_MEDIA_TYPE` records (none for today's trade photos). So screenshots are **referenced but not
  captured**; no local media paths exist to record.

## Trade-like posts today (16 instrument-mentioning; grouped by side record)

- **SOL:** 1 (setup). **BTC:** 4 (1 commentary + 1 long-update + 1 result + 1 short call). **XAUUSD/Gold:**
  11 (1 SELL setup + 10 management/rationale/result). Distinct trade setups ≈ **3** (SOL LONG, BTC, XAU SELL).

See the three separate side records:
- `side_trade_evidence/FP-LIVE-TRADE-OBS-001_SOL.md`
- `side_trade_evidence/FP-LIVE-TRADE-OBS-002_BTC.md`
- `side_trade_evidence/FP-LIVE-TRADE-OBS-003_XAUUSD.md`

### FP-LIVE-TRADE-OBS-001_SOL — SOLANA LONG
- msg **45641** @ **2026-07-10T15:16:51Z** · channel `sea-scalper-farouk` · poster `seascalperfarouk`
- instrument **SOLANA (SOL)** · direction **LONG** · **entry zone 78–74** · **SL 69** · TP: none stated
- media: photo **referenced, not stored locally** · follow-up/result: **none today** (entry only)

### FP-LIVE-TRADE-OBS-002_BTC — BTC (mixed)
- msg **45620** @ 06:30:53Z · `institutional-charts` · `kyledoops` — **commentary** (liquidation deltas, net
  long; sell wall ~$64,200). Not a trade. photo ref (not stored).
- msg **45624** @ 10:31:51Z · `sea-scalper-farouk` · `seascalperfarouk` — **BTC H4, ride bullish structure,
  "up 2,000+ pips"** (update on an existing LONG). No numeric entry/SL/TP. photo ref (not stored).
- msg **45636** @ 14:05:38Z · `sea-scalper-farouk` · `seascalperfarouk` — **"BTC Update — Full target hit!
  Take profits."** → **RESULT** of the BTC long. photo ref (not stored).
- msg **45638** @ 14:09:18Z · `quant-flow` · `wazwithazed` — **"BTC Short"** (new short call after a
  coinbase sweep; different poster). No numeric entry/SL/TP. photo ref (not stored).
- direction: **mixed** (existing LONG target-hit + a separate SHORT call) · follow-up/result: **YES**
  (45636 full-target-hit).

### FP-LIVE-TRADE-OBS-003_XAUUSD — XAU/USD SELL (full thread)
- msg **45625** @ **2026-07-10T12:43:32Z** · channel `gold-trades` · `seascalperfarouk` —
  **XAU/USD SELL · entry 4102–4115 · SL 4152 · "LOW LOT"**. No media.
- Management / rationale / result thread (all `gold-trades`, `seascalperfarouk`):
  - 45626 @ 13:08:24Z — "low risk, might push into 4125–4135"
  - 45627 @ 13:24:06Z — "take tp1, close worst entry, hold, SL to entry"
  - 45628 @ 13:24:33Z — photo (ref, not stored)
  - 45629 @ 13:25:16Z — **"100 pips"** (result; photo ref)
  - 45630 @ 13:28:45Z — photo (ref)
  - 45631 @ 13:28:54Z — "Let's go!!! take more off"
  - 45632 @ 13:30:11Z — **"200 pips"** (result; photo ref)
  - 45633 @ 13:31:35Z — rationale ("lost the Asia low; 5M/15M/H1 closed below; untested Asia high")
  - 45634 @ 13:37:10Z — "take 50% off, SL to entry"
  - 45635 @ 13:38:32Z — **TP2 4077.00 / TP3 4055.00**
- direction **SELL/SHORT** · entry **4102–4115** · SL **4152** · TP: TP1 hit (~100–200 pips), **TP2 4077**,
  **TP3 4055** · follow-up/result: **YES** (extensive management + results).

## Interpretation guardrails (explicit)

- **SOL and BTC are kept SEPARATE from the XAUUSD lane** — side observation records only; not classified,
  not detected, not scored, not run through the Farouk Campaign State Machine, not journalled into the
  shadow pipeline.
- The **XAU/USD SELL** here is Farouk's **discretionary Telegram call**, distinct from the mechanical
  TradingView Farouk-Playbook indicator alerts (CHoCH/Sweep/A). It is recorded as observation only —
  **not** treated as an executable signal and **not** fed to the state machine.
- **Nothing is trade-ready.** No sizing/entry/route/order derived. Descriptive record only.

## Safety confirmations

- Telegram PREVIEW listener **PID 16608 alive** (read-only check; not started/stopped/restarted).
- Read-only SQLite queries only; evidence DB **not modified**; no OCR performed (no local media to OCR).
- No TradingView alert touched; Worker not deployed; R2 not accessed; no broker/cTrader/QST; no
  permit/lease/order; gates `PAPER/PREVIEW/False/False`. `NOT_INTEGRATION_READY` unchanged.

## Next step

Observation only — these side records are retained for cross-reference (e.g., the XAU SELL @12:43Z sits in
the same ~4100–4135 Jul-10 price area as the captured structure events, but is **not** merged into the
shadow pipeline). If Martyn wants any of these tracked further, that is a **separate, explicit** decision;
by default they remain non-executable side evidence. No further action taken.
