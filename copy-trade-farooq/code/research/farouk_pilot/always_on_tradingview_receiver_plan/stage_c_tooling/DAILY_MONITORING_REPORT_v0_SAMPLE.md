# Daily Monitoring Report — v0 SAMPLE

**Built offline from existing captured R2 evidence only** (the Gate G ANY_ALERT captures). Read-only;
no execution, no alert/Worker changes. This is a **sample** to show the format Martyn reads each morning.

---

## Capture window

- **UTC window:** 2026-07-08T22:15:04Z → 2026-07-09T09:51:02Z (~11.6 h)
- **Source:** Gate G ANY_ALERT mirror captures in R2 `farouk-tv-webhook-evidence-v1`
- **Payload type:** 100% raw text / `INVALID_JSON` (Farouk `alert()` messages)

## Total TradingView captures: **74**

## Event counts by type

| Event type | Count |
|---|---|
| Bearish Engulfing | 14 |
| Bullish Engulfing | 13 |
| A SHORT | 14 |
| A LONG | 10 |
| BPR tapped | 8 |
| Sweep high | 6 |
| Sweep low | 4 |
| CHoCH DOWN | 3 |
| CHoCH UP | 2 |
| **A+ / A+ or better** | **0** |
| **A+++** | **0** |
| BPR formed | 0 |
| Unknown / unclassified | 0 |
| **TOTAL** | **74** |

### Grouped

- A directional: LONG 10 / SHORT 14
- CHoCH: UP 2 / DOWN 3
- Sweep: high 6 / low 4
- Engulfing: bullish 13 / bearish 14
- BPR: tapped 8 / formed 0
- Grade: A+ 0 / A+++ 0

## Most recent 20 events (chronological, UTC)

| received_at_utc | family | dir | raw |
|---|---|---|---|
| 2026-07-09T05:57:01Z | A_LONG | LONG | Farouks Playbook: A LONG on XAUUSD 3 |
| 2026-07-09T05:57:01Z | ENGULFING | bullish | Farouks Playbook: Bullish Engulfing on XAUUSD 3 |
| 2026-07-09T06:12:02Z | A_SHORT | SHORT | Farouks Playbook: A SHORT on XAUUSD 3 |
| 2026-07-09T06:27:01Z | A_SHORT | SHORT | Farouks Playbook: A SHORT on XAUUSD 3 |
| 2026-07-09T06:39:01Z | ENGULFING | bearish | Farouks Playbook: Bearish Engulfing on XAUUSD 3 |
| 2026-07-09T06:39:02Z | A_SHORT | SHORT | Farouks Playbook: A SHORT on XAUUSD 3 |
| 2026-07-09T06:48:02Z | BPR_TAPPED | — | Farouks Playbook: BPR tapped on XAUUSD 3 |
| 2026-07-09T07:06:00Z | ENGULFING | bearish | Farouks Playbook: Bearish Engulfing on XAUUSD 3 |
| 2026-07-09T07:06:00Z | A_SHORT | SHORT | Farouks Playbook: A SHORT on XAUUSD 3 |
| 2026-07-09T07:15:01Z | BPR_TAPPED | — | Farouks Playbook: BPR tapped on XAUUSD 3 |
| 2026-07-09T07:45:05Z | A_SHORT | SHORT | Farouks Playbook: A SHORT on XAUUSD 3 |
| 2026-07-09T07:48:01Z | ENGULFING | bearish | Farouks Playbook: Bearish Engulfing on XAUUSD 3 |
| 2026-07-09T07:48:01Z | A_SHORT | SHORT | Farouks Playbook: A SHORT on XAUUSD 3 |
| 2026-07-09T08:21:01Z | A_LONG | LONG | Farouks Playbook: A LONG on XAUUSD 3 |
| 2026-07-09T09:03:00Z | A_LONG | LONG | Farouks Playbook: A LONG on XAUUSD 3 |
| 2026-07-09T09:09:01Z | A_SHORT | SHORT | Farouks Playbook: A SHORT on XAUUSD 3 |
| 2026-07-09T09:09:01Z | ENGULFING | bearish | Farouks Playbook: Bearish Engulfing on XAUUSD 3 |
| 2026-07-09T09:42:02Z | CHOCH_DOWN | bearish | Farouks Playbook: CHoCH DOWN on XAUUSD 3 |
| 2026-07-09T09:51:02Z | ENGULFING | bullish | Farouks Playbook: Bullish Engulfing on XAUUSD 3 |
| 2026-07-09T09:51:02Z | A_LONG | LONG | Farouks Playbook: A LONG on XAUUSD 3 |

## ⚠️ Noisy-event warning

- **Engulfing (27, 36%)** and **A LONG/SHORT (24, 32%)** dominate — ~68% of volume. High-frequency
  **context**, low standalone signal. Do **not** mirror these continuously; the ANY_ALERT composite that
  produced this data is too noisy for ongoing capture.

## 🎯 Low-volume signal watchlist (candidate trade-quality)

| Signal | This window | Read |
|---|---|---|
| A+ / "A+ or better" | **0** | Grade trigger — rare, highest signal (mirrored = H1) |
| CHoCH up/down | 5 | Structure shift (mirrored = H2, CHoCH DOWN) |
| BPR formed | 0 | Very rare, high value if it fires |
| Sweep high/low | 10 | Liquidity context (moderate) |

## Lane / safety status

- **H1** `LIVE004_APLUS_MIRROR_GATE_H1`: **armed, not fired** (A+ = 0 this window).
- **H2** `LIVE005_CHOCH_DOWN_MIRROR_GATE_H2`: **armed, not fired** (waiting for CHoCH DOWN).
- **Telegram PREVIEW listener:** RUNNING, PID 40416 (untouched).
- **Worker:** pure logging-only (`ef8d4a95`); `POST` capture only; `GET`/wrong-path reject.
- **Execution gates:** `MODE=PAPER`, `LISTENER_MODE=PREVIEW`, `EXECUTION_ENABLED=False`,
  `CTRADER_EXECUTION_ENABLED=False`.
- Broker/cTrader/QST: absent. Permits/leases/orders: none. 1.0% risk cap: unchanged.
- **`NOT_INTEGRATION_READY`: unchanged** (capture/observation only — this report enables no execution).

## Note

This v0 sample is built from the Gate G capture window. A real daily report would cover the prior 24 h
of R2 objects; see `DAILY_MONITORING_REPORT_GENERATOR_SPEC_v0_1.md` for the (future) auto-generator.
