# Batch 002 A-only Time-Box CLOSE — Verification Report

**Mode: BATCH 002 A-ONLY TIME-BOX CLOSED VERIFICATION ONLY.** Observation/verification only. No broker/
cTrader/QST/execution, no permit/lease/order, no gate change, no trade instruction, **no secret rotation**.
`NOT_INTEGRATION_READY` unchanged. Date 2026-07-10.

## Window + rotation status

- **`LIVE012_ANY_ALERT_TIMEBOX_A_ONLY_BATCH002` = CLOSED** (Martyn disabled/paused only LIVE012; LIVE008–LIVE011
  and all originals untouched).
- **Webhook rotation DEFERRED by Martyn — the secret-exposure flag remains OPEN.** Verification proceeded on
  the existing logging-only path (no rotation). Blast radius stays bounded (logging-only → at most junk R2
  objects; no execution/broker).

## R2 verification (read-only temp branch → reverted)

- Method: temporary **secret-free, token-gated read-only list branch** deployed only to enumerate keys, then
  **reverted to pure logging-only**. Object fetches used wrangler account auth. **No webhook secret used or
  printed.**
- **Bucket count 90 → 93 = 3 new objects during the window** (2026-07-10 ~10:15–10:24Z).

### The 3 window captures (secrets redacted; `path=/tv/<redacted>` on all)

| received_at_utc | classified | raw text | object key | disposition |
|---|---|---|---|---|
| 2026-07-10T10:15:05Z | **A_SHORT** | `Farouks Playbook: A SHORT on XAUUSD 3` | `a989c821-71eb-46a3-895e-81dd5ae24127` | **whitelisted (directional A)** |
| 2026-07-10T10:21:02Z | **A_LONG** | `Farouks Playbook: A LONG on XAUUSD 3` | `0cc9cb88-8861-496c-b751-701309614664` | **whitelisted (directional A)** |
| 2026-07-10T10:24:02Z | CHOCH_UP | `CHoCH up (bullish)` | `4073b55d-ca37-4cac-9135-8f5a92932c88` | kept (discrete-mirror structure event) |

All `INVALID_JSON` (raw indicator text — expected). **Secret not stored** in any object.

## Local whitelist + noise handling

- **A LONG captured: YES** (10:21:02Z). **A SHORT captured: YES** (10:15:05Z). → the directional-A fallback
  **worked** — the previously-missing events are now capturable.
- **Non-A ANY_ALERT noise ignored: 0** — no Engulfing / BPR / A+ / other noise events landed in this
  (short, quiet) window. (The whitelist would have dropped any such; none present.)
- The single `CHOCH_UP` is a valid structure event (kept for sequence detection), not noise.

## Sequence check (detector) — 0 candidates

Ran `shadow_candidate_detector_v0_1` over the window's useful events:
- `candidates_total: 0`; **`disqualified_total: 1` — CONTRADICTORY_CLUSTER** (A_SHORT 10:15 + A_LONG 10:21,
  opposite direction hints within 15m).
- **No `CHOCH_UP→A_LONG`**: the `CHOCH_UP` (10:24) fired **after** the `A_LONG` (10:21), wrong order.
- **No `CHOCH_DOWN→A_SHORT`**: no `CHOCH_DOWN` before the `A_SHORT`.
- No sweeps in-window → no `SWEEP→CHOCH→A` chain.

**No valid Batch 002 sequence exists. No candidate fabricated.** The two A signals are an opposite-direction
cluster 6 min apart (indecisive chop), not a setup.

## OHLC matching

Not applicable — **0 sequence candidates**, so nothing to outcome-match (task 9). (Note: the imported Jul-10
OHLC ends 08:09Z anyway, before this 10:15–10:24Z window; a fresh export would be needed only once a real
sequence appears.)

## Journal / Batch 002

- **Journal unchanged** (no candidate). **Batch 002 remains 0 candidates.**
- Preserved for the record: the A_SHORT / A_LONG object keys, times, and raw texts above (secrets redacted).

## Safety confirmations

- **Worker restored to pure logging-only** — src sha256 == baseline `30bdc54d…`; `__verify_list__` absent;
  temp version `2a3fc3cf…` → reverted `5c89d2d3…`. **Temp read/list branch ABSENT.** Backup + token removed.
- Post-revert negative checks: `GET /__verify_list__?t=dummy`→405, `GET /__verify_list__`→405, `POST` wrong
  path→404, `GET /`→405 (all pass).
- LIVE008–LIVE011 remain armed/untouched from our side; original alerts untouched; no TradingView alert
  touched by Claude.
- Telegram PREVIEW listener **PID 16608 running/untouched**; no broker/cTrader/QST; no permit/lease/order;
  gates `MODE=PAPER`, `LISTENER_MODE=PREVIEW`, `EXECUTION_ENABLED=False`, `CTRADER_EXECUTION_ENABLED=False`.
- **No secret rotated; secret never printed/stored.** `NOT_INTEGRATION_READY` unchanged.

## Next step

The A-capture mechanism is **validated** (A LONG + A SHORT captured). To form a real sequence, a window is
needed where a **CHoCH precedes an aligned A within 15m** (`CHOCH_UP→A_LONG` / `CHOCH_DOWN→A_SHORT`) or a
`SWEEP→CHOCH→A` chain — the LIVE008–LIVE011 discrete mirrors + a re-armed time-boxed LIVE012 will capture the
pieces; keep accumulating across sessions toward the ≥30/≥5 bar. **Deferred:** webhook-secret rotation (flag
OPEN) whenever Martyn authorises it. Observation-only.
