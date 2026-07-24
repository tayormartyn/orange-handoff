# Gate G — Raw Event Inventory

**Offline analysis (2026-07-09), read-only.** Source: the Gate G ANY_ALERT captures in R2
(`farouk-tv-webhook-evidence-v1`). Analysed **74 of 75** Gate G objects (one straggler not fetched;
non-material). **Raw payload is the source of truth; all fields below are candidate/observational — no
execution meaning.**

- Payload type: **100% raw text / `INVALID_JSON`** (the ANY_ALERT alert is `alert()`-based → the webhook
  body is the Farouk indicator's own message string, e.g. `Farouks Playbook: A SHORT on XAUUSD 3`).
- Time span: **2026-07-08T22:15:04Z → 2026-07-09T09:51:02Z** (~11.6 h, UTC).
- All `symbol` XAUUSD, `timeframe` 3 (from the message text `on XAUUSD 3`).

## Event family inventory (candidate classification from raw text)

| Event family | Count | Direction (if inferable) |
|---|---|---|
| Bearish Engulfing | 14 | bearish |
| Bullish Engulfing | 13 | bullish |
| A SHORT | 14 | SHORT |
| A LONG | 10 | LONG |
| BPR tapped | 8 | — |
| Sweep high | 6 | bearish (liquidity) |
| Sweep low | 4 | bullish (liquidity) |
| CHoCH DOWN | 3 | bearish |
| CHoCH UP | 2 | bullish |
| **A+ / A+ or better** | **0** | — (none fired in this window) |
| **A+++** | **0** | — (never observed, consistent with all prior evidence) |
| BPR formed | 0 | — |
| Sweep (unspecified) | 0 | — |
| Unknown / unclassified | 0 | — |
| **TOTAL** | **74** | |

## Notes

- **No A+ grade event fired** in this ~11.6 h window → A+ is genuinely rare (validates H1's choice of the
  APLUS alert as low-volume, high-signal).
- **A+++ absent** — matches the FP-LIVE-OBSERVATION-001 / PHONE_ALERT_BATCH_001 findings (A+++ never
  observed).
- Engulfing (27) + A LONG/SHORT (24) dominate (~69%) → high-frequency **context**, not standalone
  trade-quality (see `GATE_G_EVENT_FREQUENCY_ANALYSIS.md`).

## Chronological sample (first 8, UTC)

| received_at_utc | family | dir | key(8) | parse_status | raw |
|---|---|---|---|---|---|
| 2026-07-08T22:15:04Z | ENGULFING | bearish | ac42a8cc | INVALID_JSON | Farouks Playbook: Bearish Engulfing on XAUUSD 3 |
| 2026-07-08T22:21:00Z | ENGULFING | bearish | 05abf146 | INVALID_JSON | Farouks Playbook: Bearish Engulfing on XAUUSD 3 |
| 2026-07-08T22:27:00Z | ENGULFING | bearish | 5fe6af26 | INVALID_JSON | Farouks Playbook: Bearish Engulfing on XAUUSD 3 |
| 2026-07-08T22:27:00Z | A_SHORT | SHORT | 15fc2db4 | INVALID_JSON | Farouks Playbook: A SHORT on XAUUSD 3 |
| 2026-07-08T22:48:01Z | ENGULFING | bullish | d65a312b | INVALID_JSON | Farouks Playbook: Bullish Engulfing on XAUUSD 3 |
| 2026-07-08T23:12:01Z | ENGULFING | bearish | babd139a | INVALID_JSON | Farouks Playbook: Bearish Engulfing on XAUUSD 3 |
| 2026-07-08T23:48:03Z | CHOCH_DOWN | bearish | (…) | INVALID_JSON | Farouks Playbook: CHoCH DOWN on XAUUSD 3 |
| 2026-07-08T23:57:02Z | BPR_TAPPED | — | (…) | INVALID_JSON | Farouks Playbook: BPR tapped on XAUUSD 3 |

_(Full 74-row chronology available from the captured objects; this is a representative head.)_

## Integrity

Raw preserved byte-exact; `received_at_utc` UTC; `path: /tv/<redacted>` (secret not stored). This is
measurement only — no execution interpretation, order intent, broker route, lot size, account ID, or
risk sizing anywhere.
