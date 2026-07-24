# Batch 002 EXTENDED A-only Time-Box CLOSE — Verification Report

**Mode: EXTENDED LIVE012 TIME-BOX CLOSED VERIFICATION ONLY.** Observation/verification only. No broker/
cTrader/QST/execution, no permit/lease/order, no gate change, no trade instruction, **no secret rotation**.
`NOT_INTEGRATION_READY` unchanged. Date 2026-07-10.

## Window + rotation status

- **`LIVE012_ANY_ALERT_TIMEBOX_A_ONLY_BATCH002` = CLOSED** (Martyn disabled/paused ONLY LIVE012).
- **Time-box was UNINTENTIONALLY EXTENDED** — LIVE012 had been running longer than intended (~10:27Z→18:03Z,
  ~7.5h) before being paused. Extra ANY_ALERT captures are accepted as **logging/evidence only** and are
  **not promoted**.
- **Webhook rotation DEFERRED by Martyn — exposure flag remains OPEN.** Verified on the existing logging-only
  path (no rotation, secret never printed/stored).

## R2 verification (read-only temp branch → reverted)

- Method: temporary **secret-free, token-gated read-only list branch** → enumerate keys → **revert to pure
  logging-only**. Object fetches via wrangler account auth. **No webhook secret used or printed.**
- **Object count: 93 → 103 = 10 new objects** during the extended window (2026-07-10 10:27Z–18:03Z).

## Counts by raw alert type (the 10 window objects)

| event_type | count | raw text |
|---|---|---|
| SWEEP_HIGH | 5 | `Liquidity Sweep high` |
| SWEEP_LOW | 3 | `Liquidity Sweep low` |
| CHOCH_UP | 2 | `CHoCH up (bullish)` |
| **A_LONG** | **0** | — |
| **A_SHORT** | **0** | — |
| Engulfing / BPR / A+ / A+++ / other | 0 | — |

- **A LONG captured: 0. A SHORT captured: 0.** No directional A fired during this (quiet) extended window.
- **Non-A noise ignored:** 0 of the classic-noise types (Engulfing/BPR/A+/A+++). The 10 non-A events are all
  **sequence-relevant** Sweep/CHoCH (kept for sequence detection, not promoted as standalone candidates).

## Preserved keys/times (task 8)

- **A LONG / A SHORT:** NONE this window (0 captured) — nothing to preserve.
- **Sequence-relevant CHoCH/Sweep** (received_at_utc · type · key8):
  `10:27:01Z SWEEP_HIGH 3a22593c` · `11:33:01Z SWEEP_LOW 69eaceeb` · `12:15:15Z CHOCH_UP 80a3a92c` ·
  `14:24:03Z SWEEP_HIGH b5ad9d50` · `14:27:02Z CHOCH_UP 3cadd156` · `14:30:13Z SWEEP_HIGH e7920d30` ·
  `14:36:03Z SWEEP_LOW 6fe116bb` · `16:03:01Z SWEEP_HIGH 49dbbef7` · `16:33:02Z SWEEP_HIGH 641093be` ·
  `18:03:00Z SWEEP_LOW 874f06d3`. (all `path=/tv/<redacted>`; secret not stored.)

## Sequence check (detector) — 0 candidates

`shadow_candidate_detector_v0_1`: **`candidates_total: 0`, `disqualified_total: 2`** (contradictory clusters
from opposite-bias Sweep/CHoCH within 15m, e.g. the 14:24–14:30 SWEEP_HIGH + CHOCH_UP mix).
- **No sequence can form: 0 directional A** (`A_LONG`/`A_SHORT`) → every pattern's terminal is missing.
- Also no `SWEEP_LOW→CHOCH_UP` within 30m (Sweep low 11:33 → CHoCH up 12:15 = 42m; other pairings wrong
  direction/order), and `SWEEP_HIGH` needs a `CHOCH_DOWN` (none captured).

**No valid Batch 002 sequence. No candidate fabricated. Batch 002 remains EMPTY (0).**

## OHLC matching

Not applicable — 0 candidates.

## Safety confirmations

- **Worker restored to pure logging-only** — src sha256 == baseline `30bdc54d…`; `__verify_list__` absent;
  temp version `78bba117…` → reverted `fe684cce…`. **Temp read/list branch ABSENT.** Backup + token removed.
- Post-revert negatives: `GET /__verify_list__?t=dummy`→405, `GET /__verify_list__`→405, `POST` wrong
  path→404, `GET /`→405 (all pass).
- LIVE008–LIVE011 remain armed/untouched from our side; original alerts untouched; no TradingView alert
  touched by Claude.
- Telegram PREVIEW listener **PID 16608 running/untouched**; no broker/cTrader/QST; no permit/lease/order;
  gates `MODE=PAPER`, `LISTENER_MODE=PREVIEW`, `EXECUTION_ENABLED=False`, `CTRADER_EXECUTION_ENABLED=False`.
- **No secret rotated; secret never printed/stored.** `NOT_INTEGRATION_READY` unchanged.

## Next step

Still no reviewable sequence: the extended window produced Sweep/CHoCH but **no directional A**, so nothing
terminates. A real candidate needs a window with a **CHoCH→aligned-A within 15m** (`CHOCH_UP→A_LONG` /
`CHOCH_DOWN→A_SHORT`) or a `SWEEP→CHOCH→A` chain — and the A must fire via a re-armed **short** time-boxed
LIVE012. Keep LIVE008–LIVE011 armed; re-arm LIVE012 briefly and deliberately next time (avoid over-runs).
Keep accumulating across sessions toward ≥30/≥5. **Deferred:** webhook-secret rotation (flag OPEN).
Observation-only.
